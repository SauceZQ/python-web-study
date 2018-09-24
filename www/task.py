# !/usr/bin/env
# _*_ coding:utf-8 _*_

#
# 定时任务
# 每天 6:00-12:00 推送小说更新
import asyncio
import datetime
import json

import requests
import time
from bqw_api.bqw_models import bqw_wx_formId
from bqw_api.newbqw_crawl import search_novel, get_chapter_list, get_chapter_detail, get_last_update_time

# 获取推送的openid formid 等信息 url
# wxInfoUrl = "http://127.0.0.1:9000/bqwapi/pushuser"
wxInfoUrl = "http://127.0.0.1:9000/bqwapi/push"

DEBUG = False


def my_request(url, method='GET', params=None):
    global data
    headers = {
        'content-type': "application/json;",
    }
    if method == "GET":
        data = requests.get(url)
    else:
        data = requests.post(url, headers=headers, data=params)
    if data.status_code == 200:
        return data.json()


def run():
    first_start_time = 180000
    first_end_time = 235959
    if DEBUG:
        first_start_time = -1
        first_end_time = 235959

    # 当前时间
    now_time = time.localtime()
    # 格式化
    now_time_format = int(time.strftime("%H%M%S", now_time))
    # 默认每次爬取停留的时间 5min
    default_sleep_time = 5 * 60
    # 默认在爬取时间之外的sleep时间 10min
    default_sleep_time_nocrawl = 10 * 60
    flag = True
    # 爬取的小说
    novels = ["元尊", "我是至尊", "超品巫师"]
    while flag:
        if first_start_time <= now_time_format <= first_end_time:
            # 在规定的时间內，可以执行爬虫任务
            for novel in novels:
                do_crawl(novel)
            # 5分钟查询一次
            time.sleep(default_sleep_time)
        else:
            print("在默认爬取时间范围之外")
            time.sleep(default_sleep_time_nocrawl)


#
# 爬取某一个小说
def do_crawl(novel_name):
    novels = search_novel(novel_name)
    if len(novels) > 0 and novels[0]['novelName'] == novel_name:
        novel = novels[0]
        # todo 这里先简单以时间判断一下
        last_update_time = get_last_update_time(novel["novelUrl"])
        last_update_time = datetime.datetime.strptime(last_update_time, "%Y-%m-%d %H:%M:%S")
        now = datetime.datetime.now()
        # 只要更新时间小于5个小时都算是未读推送
        diff_hour = (now - last_update_time).seconds / 3600
        if diff_hour < 5:
            # 推送 直接写一个推送接口，请求则推送吧
            # 然后还需要在数据库里面有一张表，或则有个状态值来存储今天是否已经推送了，如果推送完毕就不再请求了
            # 这里可以把每次推送的url保存起来，如果在表里面已经存在这个url，则表示已经推送了，不再推送这一条，
            data = {
                "novel": json.dumps(novel),
            }
            res = my_request(wxInfoUrl, method='POST', params=json.dumps(data))
            print(res)


if __name__ == "__main__":
    # do_crawl("元尊")
    run()
    pass
