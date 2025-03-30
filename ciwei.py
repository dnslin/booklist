# https://www.ciweimao.com/
import requests
import json
from lxml import etree
import re


def get_webpage_content(url):
    """
    获取网页内容
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = "utf-8"  # 确保中文正确显示
        if response.status_code == 200:
            return response.text
        else:
            print(f"请求失败，状态码: {response.status_code}")
            return None
    except Exception as e:
        print(f"请求异常: {e}")
        return None


def parse_weekly_clicks(html_tree):
    """
    解析周点击榜数据
    """
    weekly_clicks_list = []

    # 获取周点击榜的容器
    try:
        # 找到包含"周点击榜"的标题框
        title_box = html_tree.xpath(
            '//div[@class="title-box icon-book"]/h3[contains(text(), "周点击榜")]/parent::div'
        )[0]
        # 从title_box的父元素获取ul列表
        weekly_clicks_ul = title_box.xpath("../ul")[0]

        # 解析排名第一的数据
        top1_item = weekly_clicks_ul.xpath('./li[@class="top1"]')[0]
        top1_data = {
            "rank": 1,
            "title": top1_item.xpath(".//h3/a/text()")[0].strip(),
            "url": top1_item.xpath(".//h3/a/@href")[0],
            "author": top1_item.xpath('.//p[@class="author"]/a/text()')[0],
            "author_url": top1_item.xpath('.//p[@class="author"]/a/@href')[0],
            "clicks": top1_item.xpath('.//p[@class="num"]/span/text()')[0],
            "cover_img": top1_item.xpath('.//a[@class="img"]/img/@data-original')[0],
        }
        weekly_clicks_list.append(top1_data)

        # 解析排名2-10的数据
        other_items = weekly_clicks_ul.xpath('./li[not(@class="top1")]')
        for item in other_items:
            rank_text = item.xpath('./a/i[@class="icon-top"]/text()')[0]
            rank = int(rank_text)

            # 提取分类，位于 [分类] 中
            category_match = item.xpath("./a/b/text()")
            category = category_match[0].strip("[]") if category_match else ""

            # 提取标题
            full_text = item.xpath("./a/text()")
            title_parts = [t.strip() for t in full_text if t.strip()]
            title = title_parts[-1] if title_parts else ""

            # 提取点击数
            clicks = item.xpath('./a/span[@class="num"]/text()')[0]

            item_data = {
                "rank": rank,
                "title": title,
                "url": item.xpath("./a/@href")[0],
                "category": category,
                "clicks": clicks,
            }
            weekly_clicks_list.append(item_data)
    except Exception as e:
        print(f"解析周点击榜数据异常: {e}")
        import traceback

        print(traceback.format_exc())

    return weekly_clicks_list


def parse_monthly_votes(html_tree):
    """
    解析月票榜数据
    """
    monthly_votes_list = []

    # 获取月票榜的容器
    try:
        # 找到包含"月票榜"的标题框
        title_box = html_tree.xpath(
            '//div[@class="title-box icon-book"]/h3[contains(text(), "月票榜")]/parent::div'
        )[0]
        # 从title_box的父元素获取ul列表
        monthly_votes_ul = title_box.xpath("../ul")[0]

        # 解析排名第一的数据
        top1_item = monthly_votes_ul.xpath('./li[@class="top1"]')[0]
        top1_data = {
            "rank": 1,
            "title": top1_item.xpath(".//h3/a/text()")[0].strip(),
            "url": top1_item.xpath(".//h3/a/@href")[0],
            "author": top1_item.xpath('.//p[@class="author"]/a/text()')[0],
            "author_url": top1_item.xpath('.//p[@class="author"]/a/@href')[0],
            "votes": top1_item.xpath('.//p[@class="num"]/span/text()')[0],
            "cover_img": top1_item.xpath('.//a[@class="img"]/img/@data-original')[0],
        }
        monthly_votes_list.append(top1_data)

        # 解析排名2-10的数据
        other_items = monthly_votes_ul.xpath('./li[not(@class="top1")]')
        for item in other_items:
            rank_text = item.xpath('./a/i[@class="icon-top"]/text()')[0]
            rank = int(rank_text)

            # 提取分类，位于 [分类] 中
            category_match = item.xpath("./a/b/text()")
            category = category_match[0].strip("[]") if category_match else ""

            # 提取标题
            full_text = item.xpath("./a/text()")
            title_parts = [t.strip() for t in full_text if t.strip()]
            title = title_parts[-1] if title_parts else ""

            # 提取月票数
            votes = item.xpath('./a/span[@class="num"]/text()')[0]

            item_data = {
                "rank": rank,
                "title": title,
                "url": item.xpath("./a/@href")[0],
                "category": category,
                "votes": votes,
            }
            monthly_votes_list.append(item_data)
    except Exception as e:
        print(f"解析月票榜数据异常: {e}")
        import traceback

        print(traceback.format_exc())

    return monthly_votes_list


def parse_new_books(html_tree):
    """
    解析新书榜数据
    """
    new_books_list = []

    # 获取新书榜的容器
    try:
        # 找到包含"新书榜"的标题框
        title_box = html_tree.xpath(
            '//div[@class="title-box icon-cat"]/h3[contains(text(), "新书榜")]/parent::div'
        )[0]
        # 从title_box的父元素获取ul列表
        new_books_ul = title_box.xpath("../ul")[0]

        # 新书榜的li元素
        items = new_books_ul.xpath("./li")

        for i, item in enumerate(items, 1):
            book_data = {
                "rank": i,
                "title": item.xpath('.//h3[@class="tit"]/a/text()')[0].strip(),
                "url": item.xpath('.//h3[@class="tit"]/a/@href')[0],
                "author": item.xpath('.//p[@class="author"]/a/text()')[0],
                "author_url": item.xpath('.//p[@class="author"]/a/@href')[0],
                "latest_chapter": item.xpath('.//p[@class="desc"]/text()')[0],
                "cover_img": item.xpath('.//a[@class="img"]/img/@data-original')[0],
            }

            # 更新频率信息可能不存在于所有项目中
            update_rate = item.xpath('.//p[@class="tips"]/text()')
            if update_rate:
                book_data["update_rate"] = update_rate[0]

            new_books_list.append(book_data)
    except Exception as e:
        print(f"解析新书榜数据异常: {e}")
        import traceback

        print(traceback.format_exc())

    return new_books_list


def main():
    url = "https://www.ciweimao.com/"
    html_content = get_webpage_content(url)

    if not html_content:
        print("获取网页内容失败")
        return

    # 解析HTML
    html_tree = etree.HTML(html_content)

    # 检查是否有榜单元素
    weekly_clicks_elements = html_tree.xpath(
        '//div[@class="title-box icon-book"]/h3[contains(text(), "周点击榜")]/parent::div'
    )
    monthly_votes_elements = html_tree.xpath(
        '//div[@class="title-box icon-book"]/h3[contains(text(), "月票榜")]/parent::div'
    )
    new_books_elements = html_tree.xpath(
        '//div[@class="title-box icon-cat"]/h3[contains(text(), "新书榜")]/parent::div'
    )

    print(f"找到周点击榜元素: {len(weekly_clicks_elements)} 个")
    print(f"找到月票榜元素: {len(monthly_votes_elements)} 个")
    print(f"找到新书榜元素: {len(new_books_elements)} 个")

    # 解析三个榜单数据
    weekly_clicks = parse_weekly_clicks(html_tree)
    monthly_votes = parse_monthly_votes(html_tree)
    new_books = parse_new_books(html_tree)

    # 组装最终数据
    results = {"周点击榜": weekly_clicks, "月票榜": monthly_votes, "新书榜": new_books}

    # 保存为JSON文件
    with open("ciweimao_rankings.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"数据已保存到ciweimao_rankings.json文件")


if __name__ == "__main__":
    main()
