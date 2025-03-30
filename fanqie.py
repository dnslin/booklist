import requests
import json
import re
from lxml import etree
from bs4 import BeautifulSoup
from datetime import datetime


# https://fanqienovel.com/api/author/misc/top_book_list/v1/?limit=200&offset=0


def getJson():
    result = requests.get(
        "https://fanqienovel.com/api/author/misc/top_book_list/v1/?limit=200&offset=0"
    ).json()
    return result


# 写入文件
def writeToFile(data):
    with open("fanqie.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print("数据已写入到 fanqie.json")


if __name__ == "__main__":
    # 获取数据
    data = getJson()
    # 写入文件
    writeToFile(data)
    # 打印数据
