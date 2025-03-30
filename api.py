from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import sqlite3
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

# 创建FastAPI应用
app = FastAPI(
    title="小说榜单API",
    description="提供获取多平台小说榜单数据的API接口",
    version="1.0.0",
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],  # 允许所有头
)


# 数据模型
class BookItem(BaseModel):
    rank: int
    title: str
    author: Optional[str] = None
    book_id: Optional[str] = None
    book_url: Optional[str] = None
    category: Optional[str] = None
    indicator_value: Optional[str] = None
    indicator_unit: Optional[str] = None
    cover_url: Optional[str] = None
    latest_chapter: Optional[str] = None
    extra_data: Optional[dict] = None


class RankingData(BaseModel):
    site_name: str
    type_name: str
    fetch_date: str
    books: List[BookItem]


# 获取数据库连接
def get_db_connection():
    conn = sqlite3.connect("booklist.db")
    conn.row_factory = sqlite3.Row  # 使结果可以通过列名访问
    return conn


@app.get("/")
async def root():
    return {
        "message": "小说榜单API服务",
        "endpoints": [
            "/api/sites",
            "/api/rankings",
            "/api/rankings/{site_code}",
            "/api/rankings/{site_code}/{ranking_type}",
        ],
    }


@app.get("/api/sites", summary="获取所有站点信息")
async def get_sites():
    """
    获取所有已配置的站点信息
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sites WHERE active = 1")
        sites = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return {"sites": sites}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取站点信息失败: {str(e)}")


@app.get("/api/rankings", summary="获取当日所有榜单数据")
async def get_all_rankings(date: str = None):
    """
    获取当日所有平台的所有榜单数据

    - **date**: 可选参数，指定获取哪一天的榜单数据，格式为YYYY-MM-DD，默认为今天
    """
    try:
        # 如果没有提供日期，使用今天的日期
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        conn = get_db_connection()
        cursor = conn.cursor()

        # 查询当日所有榜单数据，只返回rank和book_id
        query = """
        SELECT s.site_name, s.site_code, rt.type_name, rt.type_code, 
               r.rank, r.book_id, r.fetch_date
        FROM rankings r
        JOIN sites s ON r.site_id = s.site_id
        JOIN ranking_types rt ON r.ranking_type_id = rt.ranking_type_id
        WHERE r.fetch_date = ?
        ORDER BY s.site_name, rt.type_name, r.rank
        """
        cursor.execute(query, (date,))
        results = cursor.fetchall()

        # 如果没有数据，尝试获取最近的数据
        if not results:
            # 查询最近的数据日期
            cursor.execute("SELECT MAX(fetch_date) FROM rankings")
            latest_date = cursor.fetchone()[0]
            if latest_date:
                cursor.execute(query, (latest_date,))
                results = cursor.fetchall()
                date = latest_date  # 更新日期为最近的数据日期

        # 组织数据结构
        rankings_by_site = {}
        for row in results:
            site_code = row["site_code"]
            type_code = row["type_code"]

            if site_code not in rankings_by_site:
                rankings_by_site[site_code] = {
                    "site_name": row["site_name"],
                    "site_code": site_code,
                    "rankings": {},
                }

            if type_code not in rankings_by_site[site_code]["rankings"]:
                rankings_by_site[site_code]["rankings"][type_code] = {
                    "type_name": row["type_name"],
                    "type_code": type_code,
                    "fetch_date": row["fetch_date"],
                    "books": [],
                }

            # 仅包含rank和book_id
            book = {
                "rank": row["rank"],
                "book_id": row["book_id"],
            }

            rankings_by_site[site_code]["rankings"][type_code]["books"].append(book)

        conn.close()

        return {"fetch_date": date, "sites": list(rankings_by_site.values())}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取榜单数据失败: {str(e)}")


@app.get("/api/rankings/{site_code}", summary="获取指定站点的榜单数据")
async def get_site_rankings(site_code: str, date: str = None):
    """
    获取指定站点的所有榜单数据

    - **site_code**: 站点代码，如ciweimao, qidian, fanqie
    - **date**: 可选参数，指定获取哪一天的榜单数据，格式为YYYY-MM-DD，默认为今天
    """
    try:
        # 如果没有提供日期，使用今天的日期
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        conn = get_db_connection()
        cursor = conn.cursor()

        # 首先检查站点是否存在
        cursor.execute(
            "SELECT site_id, site_name FROM sites WHERE site_code = ?", (site_code,)
        )
        site = cursor.fetchone()
        if not site:
            raise HTTPException(status_code=404, detail=f"站点 {site_code} 不存在")

        site_id = site["site_id"]
        site_name = site["site_name"]

        # 查询指定站点当日所有榜单数据
        query = """
        SELECT rt.type_name, rt.type_code, 
               r.rank, r.title, r.author, r.book_id, r.book_url, r.category,
               r.indicator_value, r.indicator_unit, r.cover_url, r.latest_chapter,
               r.extra_data, r.fetch_date
        FROM rankings r
        JOIN ranking_types rt ON r.ranking_type_id = rt.ranking_type_id
        WHERE r.site_id = ? AND r.fetch_date = ?
        ORDER BY rt.type_name, r.rank
        """
        cursor.execute(query, (site_id, date))
        results = cursor.fetchall()

        # 如果没有数据，尝试获取最近的数据
        if not results:
            cursor.execute(
                "SELECT MAX(fetch_date) FROM rankings WHERE site_id = ?", (site_id,)
            )
            latest_date = cursor.fetchone()[0]
            if latest_date:
                cursor.execute(query, (site_id, latest_date))
                results = cursor.fetchall()
                date = latest_date  # 更新日期为最近的数据日期

        # 组织数据结构
        rankings_by_type = {}
        for row in results:
            type_code = row["type_code"]

            if type_code not in rankings_by_type:
                rankings_by_type[type_code] = {
                    "type_name": row["type_name"],
                    "type_code": type_code,
                    "fetch_date": row["fetch_date"],
                    "books": [],
                }

            # 处理extra_data字段
            extra_data = None
            if row["extra_data"]:
                try:
                    extra_data = json.loads(row["extra_data"])
                except:
                    pass

            book = {
                "rank": row["rank"],
                "title": row["title"],
                "author": row["author"],
                "book_id": row["book_id"],
                "book_url": row["book_url"],
                "category": row["category"],
                "indicator_value": row["indicator_value"],
                "indicator_unit": row["indicator_unit"],
                "cover_url": row["cover_url"],
                "latest_chapter": row["latest_chapter"],
                "extra_data": extra_data,
            }

            rankings_by_type[type_code]["books"].append(book)

        conn.close()

        return {
            "site_name": site_name,
            "site_code": site_code,
            "fetch_date": date,
            "rankings": list(rankings_by_type.values()),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取榜单数据失败: {str(e)}")


@app.get(
    "/api/rankings/{site_code}/{ranking_type}", summary="获取指定站点的指定榜单数据"
)
async def get_specific_ranking(site_code: str, ranking_type: str, date: str = None):
    """
    获取指定站点的指定榜单数据

    - **site_code**: 站点代码，如ciweimao, qidian, fanqie
    - **ranking_type**: 榜单类型代码，如weekly_clicks, monthly_votes, hot_list
    - **date**: 可选参数，指定获取哪一天的榜单数据，格式为YYYY-MM-DD，默认为今天
    """
    try:
        # 如果没有提供日期，使用今天的日期
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        conn = get_db_connection()
        cursor = conn.cursor()

        # 首先检查站点是否存在
        cursor.execute(
            "SELECT site_id, site_name FROM sites WHERE site_code = ?", (site_code,)
        )
        site = cursor.fetchone()
        if not site:
            raise HTTPException(status_code=404, detail=f"站点 {site_code} 不存在")

        site_id = site["site_id"]
        site_name = site["site_name"]

        # 检查榜单类型是否存在
        cursor.execute(
            "SELECT ranking_type_id, type_name FROM ranking_types WHERE site_id = ? AND type_code = ?",
            (site_id, ranking_type),
        )
        ranking_type_info = cursor.fetchone()
        if not ranking_type_info:
            raise HTTPException(
                status_code=404,
                detail=f"榜单类型 {ranking_type} 不存在于站点 {site_code}",
            )

        ranking_type_id = ranking_type_info["ranking_type_id"]
        type_name = ranking_type_info["type_name"]

        # 查询指定站点指定榜单类型当日数据
        query = """
        SELECT r.rank, r.title, r.author, r.book_id, r.book_url, r.category,
               r.indicator_value, r.indicator_unit, r.cover_url, r.latest_chapter,
               r.extra_data, r.fetch_date
        FROM rankings r
        WHERE r.site_id = ? AND r.ranking_type_id = ? AND r.fetch_date = ?
        ORDER BY r.rank
        """
        cursor.execute(query, (site_id, ranking_type_id, date))
        results = cursor.fetchall()

        # 如果没有数据，尝试获取最近的数据
        if not results:
            cursor.execute(
                "SELECT MAX(fetch_date) FROM rankings WHERE site_id = ? AND ranking_type_id = ?",
                (site_id, ranking_type_id),
            )
            latest_date = cursor.fetchone()[0]
            if latest_date:
                cursor.execute(query, (site_id, ranking_type_id, latest_date))
                results = cursor.fetchall()
                date = latest_date  # 更新日期为最近的数据日期

        # 组织数据结构
        books = []
        for row in results:
            # 处理extra_data字段
            extra_data = None
            if row["extra_data"]:
                try:
                    extra_data = json.loads(row["extra_data"])
                except:
                    pass

            book = {
                "rank": row["rank"],
                "title": row["title"],
                "author": row["author"],
                "book_id": row["book_id"],
                "book_url": row["book_url"],
                "category": row["category"],
                "indicator_value": row["indicator_value"],
                "indicator_unit": row["indicator_unit"],
                "cover_url": row["cover_url"],
                "latest_chapter": row["latest_chapter"],
                "extra_data": extra_data,
            }

            books.append(book)

        conn.close()

        return {
            "site_name": site_name,
            "site_code": site_code,
            "type_name": type_name,
            "type_code": ranking_type,
            "fetch_date": date,
            "books": books,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取榜单数据失败: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
