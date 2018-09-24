# !/usr/bin/env
# _*_ coding:utf-8 _*_
#
# 新笔趣网 www.xxbiquge.com/search.php
import datetime

import bs4
import requests
from bs4 import BeautifulSoup
import logging

# 地址主域名
import random

host = "http://www.xxbiquge.com/"

# 搜索接口
searchUrl = host + "search.php?keyword="

# UA 标识
UserAgents = [
    "Mozilla/5.0 (X11; CrOS i686 2268.111.0) AppleWebKit/536.11 (KHTML, like Gecko) Chrome/20.0.1132.57 Safari/536.11",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.6 (KHTML, like Gecko) Chrome/20.0.1092.0 Safari/536.6",
    "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.6 (KHTML, like Gecko) Chrome/20.0.1090.0 Safari/536.6",
    "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/19.77.34.5 Safari/537.1",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.9 Safari/536.5",
    "Mozilla/5.0 (Windows NT 6.0) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.36 Safari/536.5",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3",
    "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_0) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3",
    "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1062.0 Safari/536.3",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1062.0 Safari/536.3",
    "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3",
    "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3",
    "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.0 Safari/536.3",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/535.24 (KHTML, like Gecko) Chrome/19.0.1055.1 Safari/535.24",
    "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/535.24 (KHTML, like Gecko) Chrome/19.0.1055.1 Safari/535.24"]

# 请求成功状态码
STATUS_SUCCESS_CODE = 200

# debug 模式
DEBUG = True


# 获取小说搜索列表分页url
def get_page_url(search_key, page):
    return "%s%s&page=%d" % (searchUrl, search_key, page)


# 拼接章节详情的url
def get_chapter_detail_url(chapter_href):
    return "%s%s" % (host, chapter_href)


# 封装请求
def my_request(url, params=None):
    UA = random.choice(UserAgents)
    headers = {'User-Agent': UA, "Accept-Encoding": "UTF-8"}
    data = requests.get(url, headers=headers, params=params)
    if data.status_code != STATUS_SUCCESS_CODE:
        return None
    data.encoding = "utf-8"
    return data.text


# 封装 bs 解析
def parse4bs(html):
    soup = BeautifulSoup(html, "lxml")
    return soup


#
# 搜索小说，key 可以是书名 作者名 也可以模糊搜索
# @params novel_name 小说名／作者／模糊搜索key
# @return 返回搜索列表
# todo 这里也不想做分页了，模糊搜索就模糊，不过会先筛选完全匹配key的novel到第一个
def search_novel(novel_name, max_result=None):
    all_novel_list = []
    max_page = get_novel_max_page(novel_name)
    if max_page == 0:
        return all_novel_list
    # 遍历获取每一页的小说
    for page in range(1, max_page + 1):
        get_page_url(novel_name, page)
        novel_list = parse_search_novel_list(get_page_url(novel_name, page))
        if novel_list:
            all_novel_list = all_novel_list + novel_list
    # 这里手动处理一下把完全匹配的放到第一个
    filterList = list(filter(lambda novel: novel['novelName'] == novel_name, all_novel_list))
    if len(filterList) == 1:
        match_novel = filterList[0]
        index = all_novel_list.index(match_novel)
        if index != 0:
            all_novel_list.remove(match_novel)
            all_novel_list.insert(0, match_novel)
    return all_novel_list


#
# 获取小说章节列表
# @params novel_chapter_url 小说url
# todo 这里解析暂时不作分页处理了，一次性解析所有章节，反正本来就是简单的爬虫，也不追求速度，性能
def get_chapter_list(novel_chapter_url):
    all_chapters = []
    data = my_request(novel_chapter_url)
    if data is None:
        return all_chapters
    # 解析一波章节
    soup = parse4bs(data)
    # 小说名称
    novel_name = soup.find("div", id="info").find("h1").text.strip().strip("\r\n")
    chapter_list_dd = soup.find("div", id="list").findAll("dd")
    for index, chapter in enumerate(chapter_list_dd):
        chapter_info_a = chapter.find('a')
        chapter_title = chapter_info_a.text.strip().strip("\r\n")
        chapter_href = chapter_info_a["href"]
        chapter_section = index
        chapter_dict = get_chapter_dict(chapter_title, chapter_href, chapter_section, novel_name)
        if chapter_dict:
            all_chapters.append(chapter_dict)
    return all_chapters


#
# 获取最新更新时间
def get_last_update_time(novel_chapter_url):
    data = my_request(novel_chapter_url)
    # 默认昨天更新
    last_update_time = datetime.datetime.now() + datetime.timedelta(days=-1)
    if data is None:
        return last_update_time
    soup = parse4bs(data)
    last_update_time = soup.find("div", id="info").findAll('p')[2].text.replace("最后更新：", "")
    return last_update_time


#
# 获取章节详情
# @params chapter_url 章节href
def get_chapter_detail(chapter_url):
    detail = {}
    url = get_chapter_detail_url(chapter_url)
    data = my_request(url)
    if data is None:
        return detail
    soup = parse4bs(data)
    # 上一页 下一页
    top_page_a = soup.find("div", class_="bottem1").findAll("a")
    # 上一页 url
    last_page_url = ""
    # 下一页 url
    next_page_url = ""
    # 章节列表url 即小说url
    novel_url = ""
    for page_a in top_page_a:
        if page_a.text == '上一章':
            last_page_url = page_a['href']
        if page_a.text == '下一章':
            next_page_url = page_a['href']
        if page_a.text == "章节列表":
            novel_url = page_a["href"]
    # 这里解析一波小说名，但是有可能会出错
    novel_name = soup.find("div", class_="con_top").findAll("a")[2].text.strip().strip("\r\n")
    # 小说章节名称
    chapter_title = soup.find('div', class_='bookname').find('h1').text.strip().strip("\r\n")
    # 小说内容html 这个类型是 tag 类型，到时候需要str一下
    html_content = soup.find('div', id='content')
    # content_str = html_content.text
    # 处理一波标签 小程序 是不能直接加载 <br/> 换行的
    content_str = str(html_content).replace('<div id="content">', '').replace('</div>', "").replace("<br/>", "\r\n")
    return get_chapter_detail_dict(novel_name, novel_url,
                                   chapter_title, content_str,
                                   html_content, last_page_url,
                                   chapter_url, next_page_url)


#
# 获取章节详情dict
# 参数 小说名
#     小说章节列表url
#     章节title
#     章节内容 不带html标签
#     章节内容 带htnl标签的
#     上一页url
#     当前页url
#     下一页url
def get_chapter_detail_dict(novel_name="", novel_url="", chapter_title="", content="", html_content="",
                            last_page_url="", current_page_url="", next_page_url=""):
    return {
        'novelName': novel_name,
        'novelUrl': novel_url,
        'chapterTitle': chapter_title,
        'content': content,
        'html_content': str(html_content),
        'lastPageUrl': last_page_url,
        'currentPageUrl': current_page_url,
        'nextPageUrl': next_page_url
    }


# 获取一个章节信息对象
# 参数 章节名称
#     章节连接href
#     章节序号
#     小说名称
def get_chapter_dict(chapter_title="", chapter_href="", chapter_section="", novel_name=""):
    return {
        "title": chapter_title,
        "href": chapter_href,
        "section": chapter_section,
        "name": novel_name
    }


# 获取搜索小说列表最大页码
# @params novel_name 小说名
def get_novel_max_page(novel_name):
    max_page = 0
    url = searchUrl + novel_name
    data = my_request(url)
    # 如果搜索数据为空 则返回 0
    if data is None:
        return max_page
    soup = parse4bs(data)
    pages_a_size = len(soup.find("div", class_="search-result-page-main").findAll('a'))
    max_page = 1  # 默认只有一页
    if pages_a_size != 0:  # 如果查找到有多个页码 a 标签，则表示有多页
        max_page = pages_a_size - 4  # a标签减去 首页 上一页 下一页 末页 就是所有的页码a标签
    return max_page


# 解析搜索小说的每页数据
# @params novel_page_url 该页的url
# @return  返回该页小说信息列表
def parse_search_novel_list(novel_page_url):
    novel_list = []
    data = my_request(novel_page_url)
    if data is None:
        logging.error("获取%s页小说数据失败" % novel_page_url)
        return novel_list
    soup = parse4bs(data)
    result_list = soup.find("div", class_="result-list").findAll("div", class_=["result-item", "result-game-item"])
    # 获取搜索的每一个
    for result in result_list:
        novel_item = parse_novel_item(result)
        # 非空才加入列表
        if novel_item:
            novel_list.append(novel_item)
    return novel_list


# 解析每一个搜索的 item
# @params 该 item 的 div
def parse_novel_item(item_div):
    # 小说信息
    novel_item = {}
    if type(item_div) != bs4.element.Tag:
        return novel_item
    # 查找封面
    cover_img_url = \
        item_div.find("div", class_="result-game-item-pic").find("img", class_="result-game-item-pic-link-img")[
            'src'].strip().strip("\r\n")
    # 详细信息
    item_detail_div = item_div.find("div", class_="result-game-item-detail")
    title_a = item_detail_div.find('a', class_="result-game-item-title-link")
    novel_name = title_a['title'].strip().strip("\r\n")
    novel_url = title_a['href'].strip().strip("\r\n")
    novel_desc = item_detail_div.find("p", class_="result-game-item-desc").text.strip().strip("\r\n")
    item_infos = item_detail_div.find("div", class_="result-game-item-info").findAll("span")
    author = ""
    novel_type = ""
    update_time = ""
    for index, info in enumerate(item_infos):
        if info.text == "作者：":
            author = item_infos[index + 1].text.strip().strip("\r\n")
        if info.text == "类型：":
            novel_type = item_infos[index + 1].text.strip().strip("\r\n")
        if info.text == "更新时间：":
            update_time = item_infos[index + 1].text.strip().strip("\r\n")

    lasted_chapter_info = item_detail_div.find("div", class_="result-game-item-info").find("a")
    news_chapter_url = lasted_chapter_info["href"].strip("\r\n")
    news_chapter_title = lasted_chapter_info.text.strip("\r\n")
    return get_novel_dict(cover_img_url, novel_name, novel_type, author, novel_url, novel_desc, update_time,
                          news_chapter_title, news_chapter_url)


#
# 构造一个小说信息对象
# 参数 封面图片
#     小说名
#     小说类型
#     小说作者
#     小说url
#     小说描述
#     最近更新时间
#     最新章节名称
#     最新章节url
#
def get_novel_dict(cover_img_url="", novel_name="", novel_type="", author="", novel_url="", novel_desc="",
                   update_time="", news_chapter_title="", news_chapter_url=""):
    # 判断小说状态，如果最近一次更新时间大于15天，就是完本小说或则短更小说
    update_time_type = datetime.datetime.strptime(update_time, '%Y-%m-%d')
    time_delta = datetime.datetime.now() - update_time_type
    novel_status = '完本' if int(time_delta.days) > 15 else '连载中'
    return {
        'coverImgUrl': cover_img_url,
        'novelName': novel_name,
        'novelType': novel_type,
        'author': author,
        'novelUrl': novel_url,
        'novelDesc': novel_desc,
        'updateTime': update_time,
        'newsChapterTitle': news_chapter_title,
        'newsChapterUrl': news_chapter_url,
        'novelStatus': novel_status
    }


if __name__ == '__main__':
    novel_list = search_novel("斗破苍穹")
    # for novel in novel_list:
    #     for index, chapter in enumerate(get_chapter_list(novel["novelUrl"])):
    #         get_chapter_detail(chapter["href"])
    #         if index > 10:
    #             break
    #     break
    pass
