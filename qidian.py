import json
import requests
from lxml import etree


def get_cookies():
    """从cookie.json读取cookie信息"""
    with open("cookie.json", "r", encoding="utf-8") as f:
        cookie_data = json.load(f)
    return cookie_data.get("cookie", "")


def fetch_qidian():
    """发送请求到起点网站获取数据"""
    cookies = get_cookies()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36",
        "Cookie": cookies,
    }
    response = requests.get("https://www.qidian.com/", headers=headers)
    response.encoding = "utf-8"
    return response.text


def parse_book_info(li_element):
    """解析单本书的信息"""
    book_info = {}

    # 获取排名
    rank = li_element.get("data-rid", "")
    book_info["rank"] = rank

    # 处理展开的第一本书
    if "unfold" in li_element.get("class", ""):
        book_div = li_element.find('.//div[@class="book-info fl"]')
        if book_div is not None:
            # 书名
            title_element = book_div.find(".//h2/a")
            if title_element is not None:
                book_info["title"] = title_element.text
                book_info["url"] = title_element.get("href", "").strip()
                book_info["book_id"] = title_element.get("data-bid", "")

            # 数据指标(月票/销量冠军/增长最快等)
            digital_element = book_div.find('.//p[@class="digital"]')
            if digital_element is not None:
                if digital_element.find("em") is not None:
                    value = digital_element.find("em").text
                    unit = "".join(digital_element.xpath("text()")).strip()
                    book_info["indicator_value"] = value
                    book_info["indicator_unit"] = unit
                elif "f16" in digital_element.get("class", ""):
                    # 特殊标记，如"销量冠军"、"增长最快"等
                    book_info["special_mark"] = digital_element.text.strip()

            # 作者和分类
            author_element = book_div.find('.//p[@class="author"]')
            if author_element is not None:
                category = author_element.find('.//a[@class="type"]')
                author = author_element.find('.//a[@class="writer"]')
                if category is not None:
                    book_info["category"] = category.text
                    book_info["category_url"] = category.get("href", "").strip()
                if author is not None:
                    book_info["author"] = author.text
                    book_info["author_url"] = author.get("href", "").strip()

            # 封面图片
            cover_element = li_element.find('.//div[@class="book-cover"]//img')
            if cover_element is not None:
                book_info["cover_url"] = cover_element.get("src", "")
                book_info["cover_alt"] = cover_element.get("alt", "")
    else:
        # 处理普通列表项
        num_box = li_element.find('.//div[@class="num-box"]//span')
        if num_box is not None:
            rank_class = num_box.get("class", "")
            book_info["rank_class"] = (
                rank_class  # 例如：num1, num2, num3 等，用于前端样式
            )

        name_box = li_element.find('.//div[@class="name-box"]')
        if name_box is not None:
            # 书名和链接
            name_element = name_box.find('.//a[@class="name"]')
            if name_element is not None:
                book_info["title"] = name_element.text
                book_info["url"] = name_element.get("href", "").strip()
                book_info["book_id"] = name_element.get("data-bid", "")

            # 票数/指标
            total_element = name_box.find('.//i[@class="total"]')
            if total_element is not None:
                book_info["indicator_value"] = total_element.text

            # 检查是否有iconfont图标（特殊标记）
            icon_element = name_box.find('.//span[@class="iconfont"]')
            if icon_element is not None and icon_element.text.strip():
                book_info["icon_mark"] = icon_element.text.strip()

    return book_info


def parse_ranking_list(html_content):
    """解析所有榜单数据"""
    tree = etree.HTML(html_content)
    rankings = {}

    # 使用不同的选择器，确保能捕获所有榜单
    # 这里使用//div[@id="rank-list-row"]//div[contains(@class,"rank-list")]
    rank_divs = tree.xpath(
        '//div[@id="rank-list-row"]//div[contains(@class,"rank-list")]'
    )

    print(f"找到 {len(rank_divs)} 个榜单")

    for rank_div in rank_divs:
        # 获取榜单ID
        rank_id = rank_div.get("data-l2", "")

        if not rank_id:
            continue  # 跳过没有data-l2属性的div

        # 获取榜单名称和链接
        title_element = rank_div.xpath('.//h3[@class="wrap-title lang"]/a[1]')
        if title_element and len(title_element) > 0:
            # 获取包括嵌套文本在内的所有文本
            text_parts = []
            for txt in title_element[0].xpath(".//text()"):
                text_parts.append(txt.strip())
            rank_name = "".join(text_parts).strip()
            rank_url = title_element[0].get("href", "").strip()
        else:
            continue  # 如果找不到榜单名称，跳过这个榜单

        # 获取"更多"链接
        more_element = rank_div.xpath('.//a[@class="more"]')
        more_url = (
            more_element[0].get("href", "").strip()
            if more_element and len(more_element) > 0
            else ""
        )

        # 解析书籍列表
        book_elements = rank_div.xpath('.//div[@class="book-list"]//li')
        books = []
        for book_element in book_elements:
            book_info = parse_book_info(book_element)
            if book_info:  # 只添加非空的书籍信息
                books.append(book_info)

        print(f"榜单: {rank_name}, ID: {rank_id}, 书籍数量: {len(books)}")

        # 添加榜单信息
        rankings[rank_name] = {
            "id": rank_id,
            "url": rank_url,
            "more_url": more_url,
            "books": books,
        }

    return rankings


def save_to_json(data, filename="qidian_rankings.json"):
    """将数据保存为JSON文件"""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"数据已成功保存到 {filename}")

    # 打印榜单统计信息
    if "rankings" in data:
        print(f"\n榜单统计:")
        for rank_name, rank_data in data["rankings"].items():
            print(f"- {rank_name}: {len(rank_data['books'])} 本书")


def main():
    """主程序"""
    use_local = False  # 设置为True使用本地temp.html，False从网站获取

    if use_local:
        # 读取本地HTML文件
        with open("temp.html", "r", encoding="utf-8") as f:
            html_content = f.read()
    else:
        # 从网站获取数据
        try:
            html_content = fetch_qidian()
        except Exception as e:
            print(f"获取网站数据失败: {e}")
            return

    # 解析榜单数据
    rankings = parse_ranking_list(html_content)

    # 添加元数据
    result = {
        "source": "起点中文网",
        "url": "https://www.qidian.com/",
        "timestamp": "2025-03-30",
        "rankings": rankings,
    }

    # 保存为JSON文件
    save_to_json(result)

    print("数据已成功保存到 qidian_rankings.json")


if __name__ == "__main__":
    main()
