import sqlite3
import os
import json
import time
import re
import logging
from datetime import datetime
import importlib
import traceback

# 设置日志记录
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename="booklist_fetch.log",
    filemode="a",
    # encoding="utf-8",
    encoding="utf-8",
)
logger = logging.getLogger("booklist")


class BooklistDatabase:
    """
    榜单数据库管理类
    负责创建、连接数据库和执行数据库操作
    """

    def __init__(self, db_path="booklist.db"):
        """初始化数据库连接"""
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.initialize()

    def initialize(self):
        """初始化数据库连接并创建表结构"""
        # 检查数据库文件是否存在
        db_exists = os.path.exists(self.db_path)

        # 连接数据库
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")  # 启用外键约束
        self.cursor = self.conn.cursor()

        # 如果数据库文件不存在，创建表结构
        if not db_exists:
            self.create_tables()

    def create_tables(self):
        """创建数据库表结构"""
        # 创建sites表
        self.cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS sites (
            site_id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_name TEXT NOT NULL,
            site_url TEXT NOT NULL,
            site_code TEXT NOT NULL UNIQUE,
            fetch_type TEXT NOT NULL,
            api_url TEXT,
            description TEXT,
            active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        )

        # 创建ranking_types表
        self.cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS ranking_types (
            ranking_type_id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id INTEGER NOT NULL,
            type_name TEXT NOT NULL,
            type_code TEXT NOT NULL,
            type_url TEXT,
            description TEXT,
            active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (site_id) REFERENCES sites (site_id),
            UNIQUE (site_id, type_code)
        )
        """
        )

        # 创建rankings表
        self.cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS rankings (
            ranking_id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id INTEGER NOT NULL,
            ranking_type_id INTEGER NOT NULL,
            fetch_date DATE NOT NULL,
            book_id TEXT,
            rank INTEGER NOT NULL,
            title TEXT NOT NULL,
            author TEXT,
            book_url TEXT,
            category TEXT,
            indicator_value TEXT,
            indicator_unit TEXT,
            cover_url TEXT,
            latest_chapter TEXT,
            creation_status INTEGER,
            extra_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (site_id) REFERENCES sites (site_id),
            FOREIGN KEY (ranking_type_id) REFERENCES ranking_types (ranking_type_id)
        )
        """
        )

        # 创建fetch_logs表
        self.cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS fetch_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id INTEGER NOT NULL,
            fetch_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL,
            message TEXT,
            items_fetched INTEGER DEFAULT 0,
            FOREIGN KEY (site_id) REFERENCES sites (site_id)
        )
        """
        )

        # 创建索引
        self.cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_rankings_site_date ON rankings (site_id, fetch_date)"
        )
        self.cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_rankings_type_date ON rankings (ranking_type_id, fetch_date)"
        )
        self.cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_rankings_book ON rankings (book_id)"
        )

        # 提交事务
        self.conn.commit()
        logger.info("数据库表结构创建完成")

        # 初始化预设站点数据
        self.init_preset_sites()

    def init_preset_sites(self):
        """初始化预设站点数据"""
        # 预设站点
        preset_sites = [
            {
                "site_name": "刺猬猫",
                "site_url": "https://www.ciweimao.com/",
                "site_code": "ciweimao",
                "fetch_type": "HTML",
                "api_url": "",
                "description": "刺猬猫小说榜单",
            },
            {
                "site_name": "起点中文网",
                "site_url": "https://www.qidian.com/",
                "site_code": "qidian",
                "fetch_type": "HTML",
                "api_url": "",
                "description": "起点中文网榜单",
            },
            {
                "site_name": "番茄小说",
                "site_url": "https://fanqienovel.com/",
                "site_code": "fanqie",
                "fetch_type": "API",
                "api_url": "https://fanqienovel.com/api/author/misc/top_book_list/v1/?limit=200&offset=0",
                "description": "番茄小说榜单",
            },
        ]

        # 预设榜单类型
        preset_ranking_types = [
            # 刺猬猫榜单
            {
                "site_code": "ciweimao",
                "type_name": "周点击榜",
                "type_code": "weekly_clicks",
                "type_url": "",
            },
            {
                "site_code": "ciweimao",
                "type_name": "月票榜",
                "type_code": "monthly_votes",
                "type_url": "",
            },
            {
                "site_code": "ciweimao",
                "type_name": "新书榜",
                "type_code": "new_books",
                "type_url": "",
            },
            # 番茄小说榜单
            {
                "site_code": "fanqie",
                "type_name": "热门榜",
                "type_code": "hot_list",
                "type_url": "",
            },
            # 起点中文网榜单 - 动态添加
        ]

        # 插入预设站点
        for site in preset_sites:
            try:
                self.cursor.execute(
                    """
                INSERT OR IGNORE INTO sites 
                (site_name, site_url, site_code, fetch_type, api_url, description)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        site["site_name"],
                        site["site_url"],
                        site["site_code"],
                        site["fetch_type"],
                        site["api_url"],
                        site["description"],
                    ),
                )
            except Exception as e:
                logger.error(f"插入预设站点失败: {str(e)}")

        # 提交事务
        self.conn.commit()

        # 获取插入的站点ID
        for ranking_type in preset_ranking_types:
            try:
                # 获取站点ID
                self.cursor.execute(
                    "SELECT site_id FROM sites WHERE site_code = ?",
                    (ranking_type["site_code"],),
                )
                site_id = self.cursor.fetchone()[0]

                # 插入榜单类型
                self.cursor.execute(
                    """
                INSERT OR IGNORE INTO ranking_types 
                (site_id, type_name, type_code, type_url, description)
                VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        site_id,
                        ranking_type["type_name"],
                        ranking_type["type_code"],
                        ranking_type["type_url"],
                        ranking_type.get("description", ""),
                    ),
                )
            except Exception as e:
                logger.error(f"插入预设榜单类型失败: {str(e)}")

        # 提交事务
        self.conn.commit()
        logger.info("预设站点和榜单类型初始化完成")

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()

    def get_active_sites(self):
        """获取所有启用的站点"""
        self.cursor.execute("SELECT * FROM sites WHERE active = 1")
        return self.cursor.fetchall()

    def get_ranking_types_by_site(self, site_id):
        """获取指定站点的榜单类型"""
        self.cursor.execute(
            "SELECT * FROM ranking_types WHERE site_id = ? AND active = 1", (site_id,)
        )
        return self.cursor.fetchall()

    def add_or_update_ranking_type(
        self, site_id, type_name, type_code, type_url="", description=""
    ):
        """添加或更新榜单类型"""
        try:
            self.cursor.execute(
                """
            INSERT OR REPLACE INTO ranking_types 
            (site_id, type_name, type_code, type_url, description, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
                (site_id, type_name, type_code, type_url, description),
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"添加或更新榜单类型失败: {str(e)}")
            return False

    def get_ranking_type_id(self, site_id, type_code):
        """获取榜单类型ID"""
        self.cursor.execute(
            "SELECT ranking_type_id FROM ranking_types WHERE site_id = ? AND type_code = ?",
            (site_id, type_code),
        )
        result = self.cursor.fetchone()
        return result[0] if result else None

    def save_ranking_data(self, site_id, ranking_type_id, fetch_date, book_data):
        """保存榜单数据"""
        # 提取书籍数据
        book_id = book_data.get("book_id", "")
        rank = book_data.get("rank", 0)
        title = book_data.get("title", "")
        author = book_data.get("author", "")
        book_url = book_data.get("url", book_data.get("book_url", ""))
        category = book_data.get("category", "")
        indicator_value = str(
            book_data.get(
                "indicator_value", book_data.get("clicks", book_data.get("votes", ""))
            )
        )
        indicator_unit = book_data.get("indicator_unit", "")
        cover_url = book_data.get("cover_url", book_data.get("cover_img", ""))
        latest_chapter = book_data.get("latest_chapter", "")
        creation_status = book_data.get("creation_status", None)

        # 额外数据转为JSON字符串
        extra_keys = set(book_data.keys()) - {
            "book_id",
            "rank",
            "title",
            "author",
            "url",
            "book_url",
            "category",
            "indicator_value",
            "clicks",
            "votes",
            "indicator_unit",
            "cover_url",
            "cover_img",
            "latest_chapter",
            "creation_status",
        }
        extra_data = {k: book_data[k] for k in extra_keys if k in book_data}
        extra_json = json.dumps(extra_data, ensure_ascii=False) if extra_data else None

        try:
            self.cursor.execute(
                """
            INSERT INTO rankings 
            (site_id, ranking_type_id, fetch_date, book_id, rank, title, author, 
            book_url, category, indicator_value, indicator_unit, cover_url, 
            latest_chapter, creation_status, extra_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    site_id,
                    ranking_type_id,
                    fetch_date,
                    book_id,
                    rank,
                    title,
                    author,
                    book_url,
                    category,
                    indicator_value,
                    indicator_unit,
                    cover_url,
                    latest_chapter,
                    creation_status,
                    extra_json,
                ),
            )
            return True
        except Exception as e:
            logger.error(f"保存榜单数据失败: {str(e)} - {book_data}")
            return False

    def log_fetch_activity(self, site_id, status, message="", items_fetched=0):
        """记录抓取活动日志"""
        try:
            self.cursor.execute(
                """
            INSERT INTO fetch_logs (site_id, status, message, items_fetched)
            VALUES (?, ?, ?, ?)
            """,
                (site_id, status, message, items_fetched),
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"记录抓取日志失败: {str(e)}")
            return False


class SiteAdapter:
    """站点适配器基类"""

    def __init__(
        self, site_id, site_code, site_name, site_url, fetch_type, api_url, db
    ):
        self.site_id = site_id
        self.site_code = site_code
        self.site_name = site_name
        self.site_url = site_url
        self.fetch_type = fetch_type
        self.api_url = api_url
        self.db = db
        self.today = datetime.now().strftime("%Y-%m-%d")

    def fetch_data(self):
        """抓取数据，由子类实现"""
        raise NotImplementedError("子类必须实现fetch_data方法")

    def process_data(self, data):
        """处理数据，由子类实现"""
        raise NotImplementedError("子类必须实现process_data方法")

    def fetch_and_save(self):
        """抓取和保存数据"""
        try:
            # 抓取数据
            data = self.fetch_data()
            if not data:
                self.db.log_fetch_activity(self.site_id, "失败", "抓取数据为空", 0)
                return False

            # 处理数据
            processed_data = self.process_data(data)
            if not processed_data:
                self.db.log_fetch_activity(self.site_id, "失败", "处理数据为空", 0)
                return False

            # 保存数据
            total_items = 0
            for ranking_type, books in processed_data.items():
                # 获取或创建榜单类型
                ranking_type_id = self.db.get_ranking_type_id(
                    self.site_id, ranking_type
                )
                if not ranking_type_id:
                    self.db.add_or_update_ranking_type(
                        self.site_id,
                        ranking_type,
                        ranking_type,
                        "",
                        f"{self.site_name} {ranking_type}",
                    )
                    ranking_type_id = self.db.get_ranking_type_id(
                        self.site_id, ranking_type
                    )

                # 保存书籍数据
                for book in books:
                    self.db.save_ranking_data(
                        self.site_id, ranking_type_id, self.today, book
                    )
                    total_items += 1

            # 记录抓取日志
            self.db.log_fetch_activity(
                self.site_id, "成功", f"已抓取 {total_items} 条数据", total_items
            )
            self.db.conn.commit()

            return True
        except Exception as e:
            logger.error(f"抓取和保存数据失败: {str(e)}")
            logger.error(traceback.format_exc())
            self.db.log_fetch_activity(self.site_id, "失败", f"异常: {str(e)}", 0)
            return False


class CiweimaoAdapter(SiteAdapter):
    """刺猬猫适配器"""

    def fetch_data(self):
        """抓取刺猬猫数据"""
        try:
            # 导入刺猬猫模块
            ciwei_module = importlib.import_module("ciwei")

            # 调用ciwei.py中的函数获取数据
            html_content = ciwei_module.get_webpage_content(self.site_url)
            if not html_content:
                logger.error("获取刺猬猫网页内容失败")
                return None

            # 解析HTML
            from lxml import etree

            html_tree = etree.HTML(html_content)

            # 解析三个榜单数据
            weekly_clicks = ciwei_module.parse_weekly_clicks(html_tree)
            monthly_votes = ciwei_module.parse_monthly_votes(html_tree)
            new_books = ciwei_module.parse_new_books(html_tree)

            # 组装最终数据
            results = {
                "weekly_clicks": weekly_clicks,
                "monthly_votes": monthly_votes,
                "new_books": new_books,
            }
            return results
        except Exception as e:
            logger.error(f"抓取刺猬猫数据失败: {str(e)}")
            logger.error(traceback.format_exc())
            return None

    def process_data(self, data):
        """处理刺猬猫数据"""
        if not data:
            return None

        # 处理数据，从URL中提取book_id
        processed_data = {}
        for ranking_type, books in data.items():
            processed_books = []
            for book in books:
                # 如果有book_url但没有book_id，尝试从URL中提取
                if "url" in book and not book.get("book_id", ""):
                    url = book["url"]
                    # 通常刺猬猫的URL格式为 https://www.ciweimao.com/book/{book_id}
                    match = re.search(r"/book/(\d+)", url)
                    if match:
                        book["book_id"] = match.group(1)
                processed_books.append(book)
            processed_data[ranking_type] = processed_books

        return processed_data


class QidianAdapter(SiteAdapter):
    """起点中文网适配器"""

    def fetch_data(self):
        """抓取起点中文网数据"""
        try:
            # 导入起点模块
            qidian_module = importlib.import_module("qidian")

            # 调用qidian.py中的函数获取数据
            html_content = qidian_module.fetch_qidian()
            if not html_content:
                logger.error("获取起点中文网网页内容失败")
                return None

            # 解析榜单数据
            rankings = qidian_module.parse_ranking_list(html_content)

            return rankings
        except Exception as e:
            logger.error(f"抓取起点中文网数据失败: {str(e)}")
            logger.error(traceback.format_exc())
            return None

    def process_data(self, data):
        """处理起点中文网数据"""
        if not data:
            return None

        processed_data = {}

        # 遍历所有榜单
        for rank_name, rank_data in data.items():
            # 创建榜单代码，去除空格和特殊字符
            rank_code = rank_name.strip().replace(" ", "_").lower()

            # 处理书籍数据
            processed_books = []
            for i, book in enumerate(rank_data.get("books", []), 1):
                # 确保有排名
                if not book.get("rank"):
                    book["rank"] = book.get("data-rid", i)

                processed_books.append(book)

            processed_data[rank_code] = processed_books

            # 添加或更新榜单类型
            self.db.add_or_update_ranking_type(
                self.site_id,
                rank_name,
                rank_code,
                rank_data.get("url", ""),
                f"起点中文网 {rank_name}",
            )

        return processed_data


class FanqieAdapter(SiteAdapter):
    """番茄小说适配器"""

    def fetch_data(self):
        """抓取番茄小说数据"""
        try:
            # 尝试直接使用requests获取数据，添加请求头
            import requests

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                "Referer": "https://fanqienovel.com/",
                "Accept": "application/json, text/plain, */*",
            }

            # 添加重试机制
            max_retries = 3
            retry_count = 0
            while retry_count < max_retries:
                try:
                    response = requests.get(self.api_url, headers=headers, timeout=10)
                    response.raise_for_status()  # 检查HTTP错误
                    return response.json()
                except (requests.RequestException, json.JSONDecodeError) as e:
                    logger.warning(
                        f"番茄小说API请求失败，正在重试 ({retry_count+1}/{max_retries}): {str(e)}"
                    )
                    retry_count += 1
                    time.sleep(2)  # 等待2秒后重试

            # 如果所有重试都失败，尝试使用fanqie模块
            logger.info("尝试使用fanqie模块获取数据")
            fanqie_module = importlib.import_module("fanqie")
            return fanqie_module.getJson()

        except Exception as e:
            logger.error(f"抓取番茄小说数据失败: {str(e)}")
            logger.error(traceback.format_exc())
            return None

    def process_data(self, data):
        """处理番茄小说数据"""
        if not data:
            logger.error("番茄小说数据为空")
            return None

        # 输出API返回的数据结构，以便调试
        logger.info(
            f"番茄小说API返回数据结构: {json.dumps(data, ensure_ascii=False)[:200]}..."
        )

        processed_data = {}

        try:
            # 尝试不同的数据格式处理方式
            if isinstance(data, dict):
                # 方式1: 标准API格式
                if "data" in data and "book_list" in data["data"]:
                    books = []
                    for i, book in enumerate(data["data"]["book_list"], 1):
                        book_data = {
                            "rank": i,
                            "book_id": book.get("book_id", ""),
                            "title": book.get("book_name", ""),
                            "author": book.get("author", ""),
                            "category": book.get("category", ""),
                            "creation_status": book.get("creation_status", 0),
                            "cover_url": book.get("thumb_url", ""),
                            "rank_score": book.get("rank_score", ""),
                        }
                        books.append(book_data)

                    processed_data["hot_list"] = books
                    logger.info(f"成功处理番茄小说热门榜数据: {len(books)} 条")
                    return processed_data
                # 方式2: 可能是直接返回书籍列表
                elif "book_list" in data:
                    books = []
                    for i, book in enumerate(data["book_list"], 1):
                        book_data = {
                            "rank": i,
                            "book_id": book.get("book_id", ""),
                            "title": book.get("book_name", ""),
                            "author": book.get("author", ""),
                            "category": book.get("category", ""),
                            "creation_status": book.get("creation_status", 0),
                            "cover_url": book.get("thumb_url", ""),
                            "rank_score": book.get("rank_score", ""),
                        }
                        books.append(book_data)

                    processed_data["hot_list"] = books
                    logger.info(f"成功处理番茄小说热门榜数据(方式2): {len(books)} 条")
                    return processed_data
                else:
                    # 记录数据结构，以便分析
                    logger.error(
                        f"番茄小说数据格式不符合预期: {json.dumps(data, ensure_ascii=False)[:500]}"
                    )
            elif isinstance(data, list):
                # 方式3: 直接是列表格式
                books = []
                for i, book in enumerate(data, 1):
                    book_data = {
                        "rank": i,
                        "book_id": book.get("book_id", ""),
                        "title": book.get("book_name", book.get("title", "")),
                        "author": book.get("author", ""),
                        "category": book.get("category", ""),
                        "creation_status": book.get("creation_status", 0),
                        "cover_url": book.get("thumb_url", book.get("cover_url", "")),
                        "rank_score": book.get("rank_score", ""),
                    }
                    books.append(book_data)

                processed_data["hot_list"] = books
                logger.info(f"成功处理番茄小说热门榜数据(列表格式): {len(books)} 条")
                return processed_data

            # 如果上面的所有方法都失败了，创建一个空榜单
            logger.warning("无法识别番茄小说数据格式，创建空榜单")
            processed_data["hot_list"] = []
            return processed_data

        except Exception as e:
            logger.error(f"处理番茄小说数据时出错: {str(e)}")
            logger.error(traceback.format_exc())

            # 出错时也创建一个空榜单，确保不会返回None
            processed_data["hot_list"] = []
            return processed_data


def get_adapter_for_site(site, db):
    """根据站点信息获取适配器实例"""
    (
        site_id,
        site_name,
        site_url,
        site_code,
        fetch_type,
        api_url,
        description,
        active,
    ) = site[:8]

    # 根据站点代码选择适配器类
    if site_code == "ciweimao":
        return CiweimaoAdapter(
            site_id, site_code, site_name, site_url, fetch_type, api_url, db
        )
    elif site_code == "qidian":
        return QidianAdapter(
            site_id, site_code, site_name, site_url, fetch_type, api_url, db
        )
    elif site_code == "fanqie":
        return FanqieAdapter(
            site_id, site_code, site_name, site_url, fetch_type, api_url, db
        )
    else:
        logger.error(f"未知的站点代码: {site_code}")
        return None


def main():
    """主函数，抓取所有站点的榜单数据"""
    logger.info("开始抓取榜单数据...")

    # 初始化数据库
    db = BooklistDatabase()

    try:
        # 获取所有启用的站点
        sites = db.get_active_sites()
        logger.info(f"找到 {len(sites)} 个启用的站点")

        # 遍历站点并抓取数据
        for site in sites:
            site_id, site_name, site_url, site_code = site[0], site[1], site[2], site[3]
            logger.info(f"开始抓取 {site_name} ({site_url}) 的榜单数据")

            # 获取站点适配器
            adapter = get_adapter_for_site(site, db)
            if not adapter:
                logger.error(f"无法为站点 {site_name} 创建适配器")
                continue

            # 抓取和保存数据
            success = adapter.fetch_and_save()
            if success:
                logger.info(f"成功抓取 {site_name} 榜单数据")
            else:
                logger.error(f"抓取 {site_name} 榜单数据失败")
    except Exception as e:
        logger.error(f"程序运行异常: {str(e)}")
        logger.error(traceback.format_exc())
    finally:
        # 关闭数据库连接
        db.close()

    logger.info("榜单数据抓取完成")


if __name__ == "__main__":
    main()
