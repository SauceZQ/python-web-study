# !/usr/bin/env
# _*_ coding:utf-8 _*_
import asyncio
import datetime
import hashlib
import json
import logging
import math

import requests
from aiohttp import web
from apis import APIValueError
from coroweb import get, post
#
# 获取小说章节
# 分页，默认20条,默认升序排列 1 降序排列为2
from handlers import isEmpty
from orm import DateEncoder

from bqw_api.bqw_models import bqw_read_history, bqw_wx_formId, kmj_page_record
from bqw_api.biquwang_crawl import parseDetail, getAllChapterByUrl, searchNovel
# 新笔趣阁
from bqw_api.newbqw_crawl import search_novel, get_chapter_list, get_chapter_detail

APP_ID = 'wx0e2b2d308df6ae01'
SECRET = '20766ba2433e83d9ad91d583f690c645'
accessToken = ''


#
# 格式化返回结果
def formatResponse(resData):
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Access-Control-Allow-Headers"
    }
    r = web.Response(headers=headers)
    r.content_type = 'application/json'
    r.body = json.dumps(resData, cls=DateEncoder, ensure_ascii=False).encode('utf-8')
    return r


#
# ------------------------api--------------

#
# 搜索小说，
# 返回搜索结果列表页
@get('/bqwapi/search/{searchKey}')
@asyncio.coroutine
def bqw_api_search(*, searchKey, page=1, limit=20):
    # 参数校验
    if (isEmpty(searchKey)):
        raise APIValueError('novelUrl', 'Invalid novelUrl.')

    # 强转
    try:
        page = int(page)
        limit = int(limit)
    except Exception as e:
        raise APIValueError('page or limit', 'Invalid page or limit.')

    # 参数校验 防止负数出现,如果为负数则默认为1
    page = page if page > 0 else 1
    limit = limit if limit > 0 else 20
    # 页码处理
    page = page - 1
    # searchResult = searchNovel(searchKey)
    searchResult = search_novel(searchKey)
    totalPage = len(searchResult)
    # 分页处理
    searchResult = searchResult[(page * limit):(page + 1) * limit]
    resData = {
        'error_code': 0,
        'msg': 'success',
        'data': {
            'searchResult': searchResult,
            'total_page': totalPage,
            'page': page + 1
        }
    }
    return formatResponse(resData)


#
# 获取小说章节列表
@get('/bqwapi/chapterlist')
@asyncio.coroutine
def bqw_api_get_chapterlist(*, novelUrl, page=1, limit=20, orderBy=1):
    # 参数校验
    if (isEmpty(novelUrl)):
        raise APIValueError('novelUrl', 'Invalid novelUrl.')

    # 强转
    try:
        page = int(page)
        limit = int(limit)
        orderBy = int(orderBy)
    except Exception as e:
        return 'params is error!'

    # 参数校验 防止负数出现,如果为负数则默认为1
    page = page if page > 0 else 1
    limit = limit if limit > 0 else 20
    orderBy = orderBy if orderBy in [1, 2] else 1
    # 页码处理
    page = page - 1

    # 这里不用存到数据库，每次查询直接去遍历爬取一遍即可嘿嘿
    # allChaptersData = getAllChapterByUrl(novelUrl)
    allChaptersData = get_chapter_list(novelUrl)
    # 如果第一次爬取失败，执行第二次爬取
    # 后期存自己数据库，防止爬取失败的情况，
    # 优先从数据库中存取，然后执行定时任务爬取更新数据库，
    if (allChaptersData is None):
        logging.info("搜索爬取失败,执行第二次爬取...")
        allChaptersData = getAllChapterByUrl(novelUrl)
    if (allChaptersData is None):
        logging.info("是的,第二次爬取也失败了...")

    # 如果两次爬取都是失败，说明是真的失败了
    resData = {
        'data': [],
        'total_page': 1,
        'page': page + 1
    }
    if (allChaptersData):
        # allChapters = allChaptersData['allChapters']
        allChapters = allChaptersData
        # 最大页码
        total = len(allChapters)
        totalPage = math.ceil(total / limit)

        # 排序处理
        if (orderBy == 2):
            allChapters = allChapters[::-1]

        # 分页处理
        allChapters = allChapters[(page * limit):(page + 1) * limit]

        resData = {
            'data': allChapters,
            'total_page': totalPage,
            'page': page + 1
        }

    return formatResponse(resData)


#
# 获取章节详情
@get('/bqwapi/getDetail')
@asyncio.coroutine
def bqw_api_getDetail(*, detailUrl=''):
    # chapterDetail = parseDetail(detailUrl)
    chapterDetail=get_chapter_detail(detailUrl)
    return formatResponse(chapterDetail)


#
# 存入阅读历史
@post('/bqwapi/readHistory')
@asyncio.coroutine
def bqw_api_save_readHistory(*, novelname, openid, chapter_url, chapter_name):
    # 参数校验
    if (isEmpty(novelname)):
        raise APIValueError('novelname', 'Invalid novelname.')
    if (isEmpty(openid)):
        raise APIValueError('openid', 'Invalid openid.')
    if (isEmpty(chapter_url)):
        raise APIValueError('chapter_url', 'Invalid chapter_url.')
    if (isEmpty(chapter_name)):
        raise APIValueError('chapter_name', 'Invalid chapter_name.')

    currentTime = datetime.datetime.now()

    # 存入
    bqwReadHistory = bqw_read_history(
        novelname=novelname,
        openid=openid,
        last_read_time=currentTime,
        chapter_url=chapter_url,
        chapter_name=chapter_name
    )
    readHistory = yield from bqwReadHistory.findAll('novelname=? and openid=?', [novelname, openid])
    readHistory = readHistory[0] if len(readHistory) > 0 else readHistory
    rows = 1
    if (len(readHistory) == 0):
        rows = yield from bqwReadHistory.save()
        print("保存=", rows)
    else:
        readHistory.last_read_time = currentTime
        readHistory.chapter_url = chapter_url
        readHistory.chapter_name = chapter_name
        rows = yield from readHistory.update()
        print("更新=", rows)

    # 成功时的返回结果
    responsData = {
        'msg': 'success',
        'error_code': 0,
    }
    # 失败的返回结果
    if (rows != 1):
        responsData['msg'] = 'fail'
        responsData['error_code'] = 1

    return formatResponse(responsData)


#
# 获取历史记录
@get('/bqwapi/readHistory')
@asyncio.coroutine
def bqw_api_get_readHistory(*, openid):
    if (isEmpty(openid)):
        raise APIValueError('openid', 'Invalid openid.')
    readHistory = bqw_read_history()
    allReadHistorys = yield from readHistory.findAll('openid=?', [openid], orderBy='last_read_time desc')
    # if(allReadHistorys is None):
    #     allReadHistorys=[]
    responseData = {
        'error_code': 0,
        'msg': 'success',
        'data': {
            'total_read_history': len(allReadHistorys),
            'openid': openid,
            'read_historys': allReadHistorys
        }
    }
    return formatResponse(responseData)


#
# ------------------- 微信接口 相关-------------------

#
# 消息推送校验
@get('/bqwapi/msgsend')
@asyncio.coroutine
def bqw_api_wx_checkSignature(*, signature, timestamp, nonce, echostr):
    # signature 微信加密签名，signature结合了开发者填写的token参数和请求中的timestamp参数、nonce参数。
    # EncodingAESKey(消息加密密钥): zDxyKUu0cyh2zDd6blDBP4Vfb7spczm96tog08Tuy2s
    token = 'z123456789q'
    temparr = [token, timestamp, nonce]
    temparr.sort()
    str = ''.join(temparr)
    trueSignature = hashlib.sha1(str.encode('utf-8')).hexdigest()
    logging.info("加密==", trueSignature)
    if (trueSignature == signature):
        return echostr
    else:
        return False


#
# 获取 微信openid
@post('/bqwapi/wxauthorization')
@asyncio.coroutine
def bqw_api_get_wxauthorization_code(*, js_code):
    if (isEmpty(js_code)):
        raise APIValueError('js_code', 'Invalid js_code.')
    params = {
        'appid': APP_ID,
        'secret': SECRET,
        'js_code': js_code,
        'grant_type': 'authorization_code'
    }
    url = 'https://api.weixin.qq.com/sns/jscode2session'
    response = requests.get(url, params=params).text
    response = json.loads(response)
    if 'openid' in response:
        resData = {
            'error_code': 0,
            'msg': 'success',
            'openid': response['openid']
        }
    else:
        resData = {
            'error_code': response['errcode'],
            'msg': response['errmsg'],
        }

    return formatResponse(resData)


#
# 手机 formId
@post('/bqwapi/formId')
@asyncio.coroutine
def bqw_api_save_formId(*, openId, formId):
    if isEmpty(openId):
        raise APIValueError('openId', 'Invalid openId.')
    if isEmpty(formId):
        raise APIValueError('formId', 'Invalid formId.')
    wxFormId = bqw_wx_formId()
    results = yield from wxFormId.findAll('openid=? and form_id=?', [openId, formId])
    resData = {
        'error_code': 1,
        'msg': 'save error',
    }
    # 检查是否已经保存了该 formid
    if len(results) > 0:
        return formatResponse(resData)
    # 保存
    wxFormId.openid = openId
    wxFormId.form_id = formId
    wxFormId.created_time = datetime.datetime.now()
    row = yield from wxFormId.save()
    if row != 1:
        return formatResponse(resData)
    # 保存成功
    resData['error_code'] = 0
    resData['msg'] = 'success'
    return formatResponse(resData)


@get('/getFormId')
@asyncio.coroutine
def getFormId(*, openId):
    # 获取openId 对应的 formid
    wxFormId = bqw_wx_formId()
    today = datetime.datetime.now()
    validty = today - datetime.timedelta(days=6)
    result = yield from wxFormId.findAll('openid=? and status=? and created_time>?', [openId, 0, validty],
                                         orderBy='created_time')
    if (len(result) == 0):
        print("formID 没有了，推送不了")
        return;
    formIdRes = result[0]
    # 更改状态
    formId = formIdRes['form_id']
    formIdRes['status'] = 1;
    yield from formIdRes.update()
    return formId


#
# 获取 access_token
def getAccessToken():
    url = "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=%s&secret=%s" % (APP_ID, SECRET)
    respText = requests.get(url).text
    resp = json.loads(respText)
    if 'access_token' in resp:
        # return resp['access_token']
        accessToken = resp['access_token']
    else:
        # return False
        accessToken = ''


#
# 模版消息 订阅小说更新通知
def mobanMsg(openId, templateId, data, page='index'):
    global accessToken
    if accessToken == '':
        getAccessToken()

    formId = getFormId()

    url = 'https://api.weixin.qq.com/cgi-bin/message/wxopen/template/send?access_token=%s' % accessToken
    params = {
        'touser': 'oDeII4zFCgWooci6aCbHOj9PB9uA',
        'data': data,
        'page': page,
        'form_id': formId
    }
    resp = requests.post(url, params=params)
    print(resp.text)


#
#
# kmj 测试接口
#

@post('/kmj/pagerecord')
@asyncio.coroutine
def api_kmj_page_record(*, in_time, route_path, user_id, user_type, next_path, serail_number):
    if isEmpty(in_time):
        raise APIValueError('in_time', 'Invalid in_time.')
    if isEmpty(route_path):
        raise APIValueError('route_path', 'Invalid route_path.')
    if isEmpty(user_id):
        raise APIValueError('user_id', 'Invalid user_id.')
    if isEmpty(user_type):
        raise APIValueError('user_type', 'Invalid user_type.')
    if isEmpty(next_path):
        raise APIValueError('next_path', 'Invalid next_path.')
    if isEmpty(serail_number):
        raise APIValueError('serail_number', 'Invalid serail_number.')

    resData = {
        'error_code': 0,
        'msg': 'success',
    }

    # 转换时间戳
    # try:
    #     in_time=datetime.datetime.fromtimestamp(int(in_time))
    # except Exception as e:
    #     msg='in_time is not timestamps'
    #     resData['error_code']=1,
    #     resData['msg']=msg
    #

    in_time = datetime.datetime.now()
    print("时间戳=", in_time)
    pageRecord = kmj_page_record(
        in_time=in_time,
        route_path=route_path,
        user_id=user_id,
        user_type=user_type,
        next_path=next_path,
        serail_number=serail_number,
        # token=token
    )

    rowIndex = yield from pageRecord.save()

    if rowIndex != 1:
        resData['error_code'] = 1
        resData['msg'] = 'error'

    return formatResponse(resData)
