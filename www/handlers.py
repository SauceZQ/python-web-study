# !/usr/bin/env
# _*_ coding:utf-8 _*_

import asyncio
import hashlib
import json
import logging
import re
import time

from aiohttp import web
from apis import APIValueError, APIError, APIPermissionError, Page, APIResourceNotFoundError
from config import configs
from coroweb import get, post
from models import User, Blog, next_id, Comment

import markdown2

# 邮箱验证 正则
_RE_EMAIL=re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
# sha1 校验正则1
_RE_SHA1=re.compile(r'^[0-9a-f]{40}$')

# cookie_name
COOKIE_NAME='awesession'
# cookie key
_COOKIE_KEY=configs.session.secret
# cookie 最大生命周期
COOKIE_MAX_AGE=86400


#
# 检查是否是admin
def check_admin(request):
    if request.__user__ is None or not request.__user__.admin:
        raise APIPermissionError()


#
# 字符串判空
def isEmpty(str):
    return not str or not str.strip()

#
# 加密cookie
# SHA1("用户id" + "用户口令" + "过期时间" + "SecretKey")
def user2cookie(user,max_age):
    expires=str(int(time.time()+max_age))
    s='%s-%s-%s-%s'%(user.id,user.passwd,expires,_COOKIE_KEY)
    L=[user.id,expires,hashlib.sha1(s.encode('utf-8')).hexdigest()]
    return '-'.join(L)

#
# 解密cookie
@asyncio.coroutine
def cookie2user(cookie_str):
    if isEmpty(cookie_str):
        return None
    try:
        L=cookie_str.split('-')
        if(len(L)!=3):
            return None
        uid,expires,sha1=L
        # 检测超时
        if int(expires)<time.time():
            return None
        # 查找用户是否存在
        user=yield from User.find(uid)
        if user is None:
            return None
        s='%s-%s-%s-%s'%(uid,user.passwd,expires,_COOKIE_KEY)
        # 对sha1 进行验证
        if sha1!=hashlib.sha1(s.encode('utf-8')).hexdigest():
            logging.info('invalid sha1')
            return None
        user.passwd='******'
        return user
    except Exception as e:
        logging.exception(e)
        return None

#
# 文本转html
def text2html(text):
    lines=map(lambda s:'<p>%s</p>' % s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;'),filter(lambda s:s.strip()!='',text.split('\n')))
    return ''.join(lines)



#
# 获取页码
def get_page_index(page_str):
    p=1
    try:
        p=int(page_str)
    except ValueError as e:
        pass
    if p<1:
        p=1
    return p


#
# 路由-------------------------

#
# 首页路由
# 路径占位符 {} 对应位置参数
@get('/')
@asyncio.coroutine
#
# 关于处理函数的参数定义，需要根据 coroweb 里面的 RequestHandler __call__ 对参数的限制
#
#
def index(*,page='1'):
    page_index=get_page_index(page)
    num=yield from Blog.findNumber('count(id)')
    page=Page(num)
    if num==0:
        blogs=[]
    else:
        blogs=yield from Blog.findAll(orderBy='created_at desc',limit=(page.offset,page.limit))
    return {
        '__template__':'blogs.html',
        'blogs':blogs,
        'page':page
    }

#
# 注册路由
@get('/register')
@asyncio.coroutine
def register():
    return {
        '__template__':'register.html'
    }

#
# 登陆路由
@get('/signin')
@asyncio.coroutine
def signnin():
    return {
        '__template__':'signin.html'
    }


#
# 退出登陆
@get('/signout')
@asyncio.coroutine
def signout(request):
    referer=request.headers.get('Referer')
    r=web.HTTPFound(referer or '/')
    r.set_cookie(COOKIE_NAME,'-deleted-',max_age=0,httponly=True)
    logging.info('user signed out.')
    return r


#
# 管理页
@get('/manage')
def manage():
    return 'redirect:/manage/comments'


#
# 评论
@get('/manage/comments')
def manage_comments(*,page='1'):
    return {
        '__template__':'manage_comments.html',
        'page_index':get_page_index(page)
    }


#
# 博客列表管理页
@get('/manage/blogs')
# @asyncio.coroutine
def manage_blogs(*,page='1'):
    return {
        '__template__':'manage_blogs.html',
        'page_index':get_page_index(page)
    }

#
# 创建blog路由
@get('/manage/blogs/create')
# @asyncio.coroutine
def manage_create_blog():
    return {
        '__template__':'manage_blog_edit.html',
        'id':'',
        'action':'/api/blogs'
    }

#
# 编辑blog路由
@get('/manage/blogs/edit')
def manage_edit_blog(*,id):
    return {
        '__template__':'manage_blog_edit.html',
        'id':id,
        'action':'/api/blogs/%s'%id
    }

#
# blog 页面路由
@get('/blog/{id}')
@asyncio.coroutine
def get_blog(id):
    blog=yield from Blog.find(id)
    comments=yield from Comment.findAll('blog_id=?',[id],orderBy='created_at desc')
    for c in comments:
        c.html_content=text2html(c.content)
    # 转换成 markdown 格式
    blog.html_content= markdown2.markdown(blog.content)
    return {
        '__template__':'blog.html',
        'blog':blog,
        'comments':comments
    }


#
# 用户管理
@get('/manage/users')
def manage_users(*,page='1'):
    return {
        '__template__':'manage_users.html',
        'page_index':get_page_index(page)
    }

#
# --------------api------------------


#
# 注册接口
@post('/api/users')
@asyncio.coroutine
def api_register_user(*,email,name,passwd):
    # 参数判空 及验证
    if isEmpty(name):
        raise APIValueError('name')
    if isEmpty(passwd) or not _RE_SHA1.match(passwd):
        raise APIValueError('passwd')
    if isEmpty(email) or not _RE_EMAIL.match(email):
        raise  APIValueError('email')
    # 判断是否注册过
    users=yield from User.findAll('email=?',[email])
    if len(users)>0:
        raise APIError('register:failed','email','Email is already in use')
    uid=next_id()
    # 对 密码 sha1加密 uid:密码明文 进行单向
    sha1_passwd='%s:%s'%(uid,passwd)
    user=User(id=uid,
              name=name.strip(),
              email=email,
              passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(),
              image='http://www.gravatar.com/avatar/%s?d=mm&s=120'%hashlib.md5(email.encode('utf-8')).hexdigest())
    # 注册信息存储到数据库
    yield from user.save()
    # 创建 session cookie
    r=web.Response()
    r.set_cookie(COOKIE_NAME,user2cookie(user,COOKIE_MAX_AGE),max_age=COOKIE_MAX_AGE,httponly=True)
    # 这里将user显示为 register.html*****
    user.passwd='******'
    r.content_type='application/json'
    r.body=json.dumps(user,ensure_ascii=False).encode('utf-8')
    return r


#
# 获取用户列表
@get('/api/users')
@asyncio.coroutine
def api_get_users(*,page='1'):
    page_index=get_page_index(page)
    num =yield from User.findNumber('count(id)')
    p=Page(num,page_index)
    if num == 0:
        return dict(page=p,users=())
    users=yield from User.findAll(orderBy='created_at desc',limit=(p.offset,p.limit))
    for u in users:
        u.passwd='******'
    return dict(page=p,users=users)



#
# 登陆接口
@post('/api/authenticate')
@asyncio.coroutine
def authenticate(*,email,passwd):
    # 参数判空
    if isEmpty(email):
        raise APIValueError('email','Invalid email.')
    if isEmpty(passwd):
        raise APIValueError('passwd','Invalid password.')
    users=yield  from  User.findAll('email=?',[email])
    if len(users)==0:
        raise APIValueError('email','Email not exist.')
    user=users[0]
    # 检查密码
    sha1=hashlib.sha1()
    sha1.update(user.id.encode('utf-8'))
    sha1.update(b':')
    sha1.update(passwd.encode('utf-8'))
    if user.passwd!=sha1.hexdigest():
        raise APIValueError('passwd','Invalid password.')
    #验证通过，设置 cookie
    r=web.Response()
    r.set_cookie(COOKIE_NAME,user2cookie(user,COOKIE_MAX_AGE),max_age=COOKIE_MAX_AGE,httponly=True)
    user.passwd='******'
    r.content_type='application/json'
    r.body=json.dumps(user,ensure_ascii=False).encode('utf-8')
    return r


#
# 创建blog接口
@post('/api/blogs')
@asyncio.coroutine
def api_create_blog(request,*,name,summary,content):
    # 只有 admin 权限才可以创建 blog
    check_admin(request)
    # 检测参数
    if isEmpty(name):
        raise APIValueError('name','name cannot be empty')
    if isEmpty(summary):
        raise APIValueError('summary','summary cannot be empty')
    if isEmpty(content):
        raise APIValueError('content','content cannot be empty')
    blog=Blog(user_id=request.__user__.id,
              user_name=request.__user__.name,
              user_image=request.__user__.image,
              name=name.strip(),
              summary=summary.strip(),
              content=content.strip())
    yield from blog.save()
    return blog


#
# 更新博客
@post('/api/blogs/{id}')
@asyncio.coroutine
def api_update_blog(id,request,*,name,summary,content):
    check_admin(request)
    blog=yield from Blog.find(id)
    if isEmpty(name):
        raise APIValueError('name','name cannot be empty')
    if isEmpty(summary):
        raise APIValueError('summary','summary cannot be empty')
    if isEmpty(content):
        raise APIValueError('content','content cannot be empty')
    blog.name=name
    blog.summary=summary.strip()
    blog.content=content.strip()
    yield from blog.update()
    return blog


#
# 删除博客
@post('/api/blogs/{id}/delete')
@asyncio.coroutine
def api_delete_blog(request,*,id):
    check_admin(request)
    blog=yield from Blog.find(id)
    yield from blog.remove()
    return dict(id=id)


#
# 获取博客列表
@get('/api/blogs')
@asyncio.coroutine
def api_blogs(*,page='1'):
    page_index=get_page_index(page)
    num=yield from Blog.findNumber('count(id)')
    p=Page(num,page_index)
    if num == 0:
        return dict(page=p,blogs=())
    blogs=yield from Blog.findAll(orderBy='created_at desc',limit=(p.offset,p.limit))
    return dict(page=p,blogs=blogs)

#
#获取blog详情 接口
@get('/api/blogs/{id}')
@asyncio.coroutine
def api_get_blog(*,id):
    blog=yield from Blog.find(id)
    return blog


#
# 获取评论列表
@get('/api/comments')
@asyncio.coroutine
def api_comments(*,page='1'):
    page_index=get_page_index(page)
    num=yield from Comment.findNumber('count(id)')
    p=Page(num,page_index)
    if num ==0:
        return dict(page=p,comments=())
    comments=yield from Comment.findAll(orderBy='created_at desc',limit=(p.offset,p.limit))
    return dict(page=p,comments=comments)


#
# 创建评论
@post('/api/blogs/{id}/comments')
@asyncio.coroutine
def api_create_comment(id,request,*,content):
    user=request.__user__
    if user is None:
        raise APIPermissionError('Please signin first')
    if isEmpty(content):
        raise APIValueError('content')
    blog=yield from Blog.find(id)
    if blog is None:
        raise APIResourceNotFoundError('Blog')
    comment=Comment(blog_id=blog.id,
                    user_id=user.id,
                    user_name=user.name,
                    user_image=user.image,
                    content=content.strip())
    yield from comment.save()
    return comment


#
# 删除评论
@post('/api/comments/{id}/delete')
@asyncio.coroutine
def api_delete_comments(id,request):
    check_admin(request)
    c=yield  from  Comment.find(id)
    if c is None:
        raise APIResourceNotFoundError('Comment')
    yield from c.remove()
    return dict(id=id)



