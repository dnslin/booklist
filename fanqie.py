import requests
import json
import re
from lxml import etree
from bs4 import BeautifulSoup
from datetime import datetime


# https://fanqienovel.com/api/author/misc/top_book_list/v1/?limit=200&offset=0
# {
#             "author": "流潋紫",
#             "book_id": "7296152639836785675",
#             "book_name": "后宫·甄嬛传",
#             "category": "宫斗宅斗",
#             "creation_status": 0,
#             "rank_score": "",
#             "thumb_url": "https://p3-reading-sign.fqnovelpic.com/novel-pic/p2o0a84ab572d09874cdaa2f6aeb5133216~tplv-snk2bdmkp8-superreso-double-rz:1200:0.image?lk3s=ae45642e&x-expires=1748493825&x-signature=QknCcEPX3v84n20iM9ORrEbi%2FW4%3D"
# }


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
