#!/usr/bin/env python3
# _*_ coding:utf-8 _*_

import multiprocessing
import os
import random
import threading
import time
from datetime import datetime
from multiprocessing import Queue

import requests
from bs4 import BeautifulSoup

from .bqw_handlers import *
from .DBUtils import DBUtils

# 域名
host = 'http://www.biquge.com.tw/'

# 搜索接口 
# get 请求 urlencode gb2312
# 参数 searchkey=%CE%D2%CA%C7%D6%C1%D7%F0
searchUrl = 'http://www.biquge.com.tw/modules/article/soshu.php'
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

# debug
DEBUG = False

# 线程数 
maxThreads = 10

# 用来处理 请求异常 bug ChunkedEncodingError    IncompleteRead
getDataErro = False

# 目标邮件地址
toAddr = '852919300@qq.com'


#
# 简单封装一下 get 请求
# 
def myRequest(url, params=None):
    UA = random.choice(UserAgents)
    # params={'searchkey':bookTitle}
    try:
        data = requests.get(url, headers={'User-Agent': UA,"Accept-Encoding":""}, params=params, timeout=30)
        return data
    except Exception as e:
        getDataErro = True
        print(e)
        return None


#
# 对获取到的小说章节列表数据格式化
def getAllNameAndUrl(allA, bookTitle):
    # 遍历所有章节，
    allChapters = []
    for index, a in enumerate(allA):
        # 获取 章节url
        href = a['href']
        # 获取 章节名称
        title = a.get_text()
        allChapters.append({'href': href,
                            'title': title,
                            'section': index,
                            'name': bookTitle
                            })
    return allChapters


#
# 爬取所有章节
# 初始化队列
# params 小说名字
#
# 返回章节列表 以及chapterId
def getAllChapterName(bookTitle):
    # 这里注意编码，笔趣网的编码是 gbk
    searchKey = bookTitle.encode('gbk')
    params = {'searchkey': searchKey}
    global getDataErro
    data = myRequest(searchUrl, params)
    if data == None:
        return None;
    data.encoding = 'gbk'
    responseHtml = data.text
    DEBUG = False
    if (DEBUG):
        print("搜索的网页结果:\r\n", responseHtml)
    # 使用 beautifulsoup 加载返回的网页
    soup = BeautifulSoup(responseHtml, 'lxml')
    # 判断搜索结果
    # 是否多个结果
    allSearchResults = soup.find_all('tr', id='nr')
    # 如果是直接精确搜索，就直接拿到了所有章节的div
    allChaptersDiv = soup.find('div', id='list')
    # 层层判断一波
    if (allSearchResults):
        realResultUrl = findRealSearch(allSearchResults, bookTitle)
        data = myRequest(realResultUrl)
        data.encoding = 'gbk'
        responseHtml = data.text
        allChaptersDiv = BeautifulSoup(responseHtml, 'lxml').find('div', id='list')
        # 章节存储在 <dd> 里面的 <a> 标签
        allA = allChaptersDiv.find_all('a')
        if (allChaptersDiv):
            # 获取id
            # http://www.biquge.com.tw/18_18821/
            chapterId = data.url.split('/')[-2]
            allChapters = getAllNameAndUrl(allA)
            return {'allChapters': allChapters, 'chapterId': chapterId}
        else:
            # print('暂无搜索结果')
            return None
    elif (allChaptersDiv):
        # 获取id
        chapterId = data.url.split('/')[-2]
        # 章节存储在 <dd> 里面的 <a> 标签
        allA = allChaptersDiv.find_all('a')
        allChapters = getAllNameAndUrl(allA, bookTitle)
        return {'allChapters': allChapters, 'chapterId': chapterId}
    else:
        # print('暂无搜索结果')
        return None


#
# 根据 小说url 获取章节
def getAllChapterByUrl(novelUrl):
    data = myRequest(novelUrl)
    if (data is None):
        return []
    data.encoding = 'gbk'
    responseHtml = data.text
    soup = BeautifulSoup(responseHtml, 'lxml')
    allChaptersDiv = soup.find('div', id='list')
    # 获取id
    chapterId = data.url.split('/')[-2]
    # 获取小说名
    bookTitle = soup.find('div', id='info').find('h1').get_text()
    # 章节存储在 <dd> 里面的 <a> 标签
    allA = allChaptersDiv.find_all('a')
    allChapters = getAllNameAndUrl(allA, bookTitle)
    return {'allChapters': allChapters, 'chapterId': chapterId}


#
# 模糊搜索，返回一个搜索结果列表
# 搜索关键词可以是 书名 可以是作者名
def searchNovel(searchKey):
    #
    # 搜索结果每页数据
    def parseResultListPage(pageurl):
        data = myRequest(pageurl)
        if (data is None):
            return []
        data.encoding = 'utf-8'
        pageSearchResults = soup.find_all('tr', id='nr')
        allResult = []
        for result in pageSearchResults:
            tds = result.find_all('td')
            novelNameTd = tds[0].find('a')
            novelName = novelNameTd.get_text()
            novelUrl = novelNameTd['href']
            newsChapterTd = tds[1].find('a')
            newsChapterTitle = newsChapterTd.get_text()
            newsChapterUrl = newsChapterTd['href']
            author = tds[2].get_text()
            updateTime = tds[4].get_text()
            novelStatus = tds[5].get_text()
            allResult.append({
                'novelName': novelName,
                'novelUrl': novelUrl,
                'newsChapterTitle': newsChapterTitle,
                'newsChapterUrl': newsChapterUrl,
                'author': author,
                'updateTime': updateTime,
                'novelStatus': novelStatus
            })
        return allResult

    searchKey = searchKey.encode('gbk')
    params = {'searchkey': searchKey}
    data = myRequest(searchUrl, params=params)
    if (data is None):
        return []
    data.encoding = 'gbk'
    searchPageUrl = data.url
    responseText = data.text
    soup = BeautifulSoup(responseText, 'lxml')
    # 判断是否是只有唯一值，或则多个结果 根据当前url可以判断
    hasOnlyOneResult = searchPageUrl.find('modules')
    allResult = []
    # 如果有多个结果，则返回结果列表
    if (hasOnlyOneResult != -1):
        maxPage = int(soup.find('a', class_='last').get_text())
        for page in range(1, maxPage + 1):
            allResult = allResult + parseResultListPage(searchPageUrl + '+' + str(page))
        return allResult
    # 如果只搜索到一个结果，
    elif (hasOnlyOneResult == -1):
        novelInfo = soup.find('div', id='info')
        novelName = novelInfo.find('h1').get_text()
        novelUrl = searchPageUrl
        allPs = novelInfo.find_all('p')
        author = allPs[0].get_text()
        author = author[author.find('：') + 1:]
        updateTime = allPs[2].get_text()
        updateTime = updateTime[updateTime.find('：') + 1:]
        newsChapter = allPs[3].find('a')
        newsChapterTitle = newsChapter.get_text()
        newsChapterUrl = '/%s/%s' % (novelUrl.split('/')[-2], newsChapter['href'])
        print("什么玩意儿=",updateTime)
        updateTimeType = datetime.datetime.strptime(updateTime, '%Y-%m-%d')
        timeDelta = datetime.datetime.now() - updateTimeType
        novelStatus = '完本' if int(timeDelta.days) > 10 else '连载中'
        return [{
            'novelName': novelName,
            'novelUrl': novelUrl,
            'newsChapterTitle': newsChapterTitle,
            'newsChapterUrl': newsChapterUrl,
            'author': author,
            'updateTime': updateTime,
            'novelStatus': novelStatus
        }]
    # 说明搜索不到
    else:
        return []


#
# 精确搜索后，开始获取所有章节
# 
def pushQueue(allChapters, chapterId, bookTitle, queue):
    if (DEBUG):
        # 创建目录 debug 时 下载下来
        mkdir(bookTitle)
    dbUtils = DBUtils()
    # 遍历所有章节，
    for index, item in enumerate(allChapters):
        # 获取 章节url
        href = item['href']
        # 获取 章节名称
        title = item['title']
        # 这里入队 存到数据库
        dbUtils.saveNoContent(chapterId, index, bookTitle, title, href)
    # 初始化队列
    waitChapter = dbUtils.getAllOutstanding(bookTitle)
    for item in waitChapter:
        queue.put(item)
    dbUtils.close()
    print("开始爬取中...")


#
# 从多个搜索结果中找出绝对匹配的小说名称
# 
def findRealSearch(allSearchResults, bookTitle):
    realResult = ''
    for result in allSearchResults:
        allSearch = result.find_all('a')
        for a in allSearch:
            if (a.get_text() == bookTitle):
                realResult = a['href']
                break
    return realResult


#
# 创建目录
# 
def mkdir(dirName):
    # 创建目录
    abspath = os.path.abspath('.')
    dir = os.path.join(abspath, dirName)
    if not os.path.exists(dir):
        os.makedirs(dir)
    os.chdir(dir)


#
# 解析小说章节详情
def parseDetail(chapterUrl):
    # 这里需要加上域名
    url = host + chapterUrl
    # 获取章节网页
    data = myRequest(url)
    data.encoding = 'gbk'
    contentHtml = data.text
    # 加载到 BeautifulSoup
    soup = BeautifulSoup(contentHtml, 'lxml')
    topAs = soup.find('div', class_='bottem1').findAll('a')
    lastPageUrl = ''
    nextPageUrl = ''
    for a in topAs:
        if a.get_text() == '上一章':
            lastPageUrl = a['href']
        if a.get_text() == '下一章':
            nextPageUrl = a['href']
    # 这里解析一波小说名，但是有可能会出错
    novelName = topAs[2].get_text()
    # 这里多了一个 ／ 但是无伤大雅
    novelUrl = host + topAs[2]['href']
    chapterTitle = soup.find('div', class_='bookname').find('h1').get_text()
    html_content = soup.find('div', id='content')
    contentStr = html_content.get_text()

    # 处理一波标签 但是这里拿出来的好像就没有 html 的标签
    contentStr = contentStr.replace('<br/>', '\r\n')

    detail = {
        'novelName': novelName,
        'novelUrl': novelUrl,
        'chapterTitle': chapterTitle,
        'content': contentStr,
        'html_content': str(html_content),
        'lastPageUrl': lastPageUrl,
        'currentPageUrl': chapterUrl,
        'nextPageUrl': nextPageUrl
    }
    # return contentStr,chapterTitle,html_content
    return detail


#
# 存储文章
# 
def saveContent(chapterUrl):
    # contentStr,chapterTitle,html_content=parseDetail(chapterUrl)
    detail = parseDetail(chapterUrl)
    # print(contentStr)
    # 更改数据库状态
    dbUtils = DBUtils()
    isUpdata = dbUtils.saveWithContent(chapterUrl, detail['content'], detail['html_content'])
    dbUtils.close()
    print("《%s》保存成功!" % detail['chapterTitle'])
    if (DEBUG):
        # 写到文件中
        fileName = '%s.txt' % (detail['chapterTitle'])
        print("正在保存%s..." % (fileName))
        with open(fileName, 'w') as f:
            f.write(detail['content'])
            # 更改数据库状态
            dbUtils = DBUtils()
            isUpdata = dbUtils.saveWithContent(chapterUrl, detail['content'], detail['html_content'])
            dbUtils.close()
            if (DEBUG):
                print('更改状态=', isUpdata)
            print("《%s》保存成功!" % fileName)


#
# 多进程爬取
def start(queue):
    process = []
    cpunum = multiprocessing.cpu_count()
    if (DEBUG):
        print('启动%s个进程...' % cpunum)
    for i in range(cpunum):
        p = multiprocessing.Process(target=multiprocessCawl, args=(queue,))
        p.start()
        process.append(p)
    for p in process:
        p.join()


#
# 每个进程需要做的事情
def multiprocessCawl(queue):
    # 每个进程再开一波线程
    threads = []
    # 存储
    while threads or queue.empty() != True:
        # 遍历线程池里面的线程 是否已经完成任务，处于非活跃状态，如果是非活跃状态，则从线程池中移除
        for thread in threads:
            if not thread.is_alive():
                threads.remove(thread)
        # 只要 线程池 没有满。或者 队列中还有 就可以创建线程
        while len(threads) < maxThreads and queue.empty() != True:
            try:
                # 这里用 非阻塞 方式 获取队列中元素
                # 如果是阻塞
                item = queue.get(False)
            except:
                break;
            # print(item[0])
            thread = threading.Thread(target=saveContent, args=(item[7],))
            thread.setDaemon(True)
            thread.start()
            threads.append(thread)
        # 这里休眠一秒吧 爬慢一点 慢一点不着急
        time.sleep(1)


#
# 执行爬虫
def doCrawl(name):
    # 创建一个队列
    dbUtils = DBUtils()
    # python 自带队列
    queue = Queue()
    startTime = datetime.datetime.now()
    print("搜索《%s》中..." % name)
    # 查找所有的章节名
    # allChapters,chapterId=getAllChapterName(name)
    allChapterList = getAllChapterName(name)
    # 初始化队列
    pushQueue(allChapterList['allChapters'], allChapterList['chapterId'], name, queue)

    global getDataErro
    # 处理一波请求bug
    if (getDataErro):
        getDataErro = False
        return False
    start(queue)
    endTime = datetime.datetime.now()
    print('已完成！时间差=', endTime - startTime)
    dbUtils.close()
    # 搜索完毕
    return True


#
# 生成 html 字符串
def createHtmlContent(title, content):
    str = '''
		<head>
		    <title>book</title>
		    <style>
		        body {
		            width: 100%;
		            height: 100%;
		        }

		        * {
		            box-sizing: border-box;
		            margin: 0;
		            padding: 0;
		        }

		        h3 {
		            text-align: center;
		            margin-top: 20px;
		            margin-bottom: 21px;
		        }

		        #content {
		            padding: 10px;
		        }
		    </style>
		</head>
		<body>
		<h3>''' + title + '</h3>' + content + '</body>'
    return str


#
# 获取当前时间，
# 返回时间格式 2018-01-12 17:16:54
def getNowTime():
    return str(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))


def run():
    # todo 每天爬取后定时推送
    # todo 这里应该把需要推送的用户放到一个表里面，比如订阅功能
    openIds = ['oDeII4zFCgWooci6aCbHOj9PB9uA']
    names = ['我是至尊', '元尊', '超品巫师']
    # 每天爬取的时间范围
    # 18:30～23:59
    firstStartTime = 183000
    firstEndTime = 235959
    # 00:00~00:30
    secondStartTime = 000000
    secondEndTime = 3000
    # 当前时间
    nowTime = time.localtime()
    # 格式化
    nowTimeFormat = int(time.strftime("%H%M%S", nowTime))
    # 默认每次爬取停留的时间 5min
    defaultSleepTime = 5 * 60
    # 非爬取时间段，间隔时间 30min
    defaultWaitTime = 30 * 60
    # 是否推送
    isSendMsg = False
    #
    while (1):
        db = DBUtils()
        # 在固定时间
        if ((nowTimeFormat >= firstStartTime and nowTimeFormat <= firstEndTime)
            or (nowTimeFormat >= secondEndTime and nowTimeFormat <= secondEndTime)):
            print("开始爬取...")
            for index, name in enumerate(names):
                hasCrawlFinished = doCrawl(name)
                if (hasCrawlFinished and isSendMsg):
                    result = db.searchNewChapter(name)
                    print("查找到 %s" % result[0][4] if len(result) > 0 else '没有查找到新的章节')
                    # 发送模版消息
                    data = {
                        "keyword1": {
                            "value": name,
                            'color': '#173177'
                        },
                        "keyword2": {
                            "value": result[0][4],
                            'color': '#173177'
                        },
                        "keyword3": {
                            "value": "暂无备注",
                            'color': '#173177'
                        },
                    }
                    templateId = 'LrNVtcHDMrws-kZQEYIXS-7vNoHS2prxAeFH54os30M'
                    mobanMsg(openIds[index], templateId, data)
            time.sleep(defaultSleepTime)
        else:
            time.sleep(defaultWaitTime)
        nowTimeFormat = int(time.strftime("%H%M%S", nowTime))
        db.close()

#
# 执行
# if(__name__=='__main__'):
# 	# todo 每天爬取后定时推送
# 	# todo 这里应该把需要推送的用户放到一个表里面，比如订阅功能
# 	openIds=['oDeII4zFCgWooci6aCbHOj9PB9uA']
# 	names = ['我是至尊', '元尊', '超品巫师']
# 	# 每天爬取的时间范围
# 	# 18:30～23:59
# 	firstStartTime = 183000
# 	firstEndTime = 235959
# 	# 00:00~00:30
# 	secondStartTime = 000000
# 	secondEndTime = 3000
# 	# 当前时间
# 	nowTime = time.localtime()
# 	# 格式化
# 	nowTimeFormat = int(time.strftime("%H%M%S", nowTime))
# 	# 默认每次爬取停留的时间 5min
# 	defaultSleepTime = 5 * 60
# 	# 非爬取时间段，间隔时间 30min
# 	defaultWaitTime = 30 * 60
# 	# 是否推送
# 	isSendMsg = False
# 	#
# 	while (1):
# 		db = DBUtils()
# 		# 在固定时间
# 		if ((nowTimeFormat >= firstStartTime and nowTimeFormat <= firstEndTime)
# 			or (nowTimeFormat >= secondEndTime and nowTimeFormat <= secondEndTime)):
# 			print("开始爬取...")
# 			for index,name in enumerate(names):
# 				hasCrawlFinished = doCrawl(name)
# 				if (isSendMsg):
# 					result = db.searchNewChapter(name)
# 					print("查找到 %s" % result[0][4] if len(result) > 0 else '没有查找到新的章节')
# 					# accessToken = bqw_handlers.getAccessToken()
# 					# if not accessToken:
# 					# 	print("获取 aceess_token 失败...")
# 					# 发送模版消息
# 					data={
# 						"keyword1":{
# 							"value":name,
# 							'color':'#173177'
# 						},
# 						"keyword2": {
# 							"value": result[0][4],
# 							'color': '#173177'
# 						},
# 						"keyword3": {
# 							"value": "暂无备注",
# 							'color': '#173177'
# 						},
#
# 					}
# 					templateId='LrNVtcHDMrws-kZQEYIXS-7vNoHS2prxAeFH54os30M'
# 					bqw_handlers.mobanMsg(openIds[index],templateId,data)
