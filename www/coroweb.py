# !/usr/bin/env
# _*_ coding:utf-8 _*_
import asyncio
import functools
import inspect
import logging;
from urllib import parse

from aiohttp import web

from apis import APIError

logging.basicConfig(level=logging.INFO)
import os

def get(path):

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args,**kw):
            return func(*args,**kw)
        wrapper.__method__='GET'
        wrapper.__route__=path
        return wrapper
    return decorator

def post(path):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args,**kw):
            return func(*args,**kw)
        wrapper.__method__='POST'
        wrapper.__route__=path
        return wrapper
    return decorator

#
# 对 fn 这个函数 里面的参数进行解析
# POSITIONAL_ONLY          位置参数(高版本中已经不用了) 正常参数
# KEYWORD_ONLY             命名关键词参数  「限制 关键字参数的名字，就可以用命名关键字参数，例如，只接收city和job作为关键字参数。这种方式定义的函数如下 」
# VAR_POSITIONAL           可选参数 *args  可变参数
# VAR_KEYWORD              关键词参数 kw   允许你传入0个或任意个含参数名的参数  def fun(id,**kw) def fun(1,name='zq',age='11')
# POSITIONAL_OR_KEYWORD    位置或必选参数  位置参数或者关键字参数

#
# 获取 「命名关键字」参数名称 不带默认参数值的那种
#
def get_required_kw_args(fn):
    args=[]
    params=inspect.signature(fn).parameters
    # name 是参数名称  param 是 inspect 的对象参数
    for name,param in params.items():
        # 如果参数类型等于 命名关键字参数 并且 参数的默认值为空
        if param.kind==inspect.Parameter.KEYWORD_ONLY and param.default==inspect.Parameter.empty:
            args.append(name)
    return tuple(args)


#
# 获取 「命名关键字」参数名称，
def get_named_kw_args(fn):
    args=[]
    params=inspect.signature(fn).parameters
    for name,param in params.items():
        if param.kind==inspect.Parameter.KEYWORD_ONLY:
            args.append(name)
    return tuple(args)

#
# 是否存在命名关键字参数
def has_named_kw_args(fn):
    params=inspect.signature(fn).parameters
    for name,param in params.items():
        if param.kind==inspect.Parameter.KEYWORD_ONLY:
            return True
#
# 是否存在关键字参数
def has_var_kw_arg(fn):
    params=inspect.signature(fn).parameters
    for name,param in params.items():
        if param.kind==inspect.Parameter.VAR_KEYWORD:
            return True

#
# 查找函数是否含有 名称为 request 的参数
def has_request_arg(fn):
    sig=inspect.signature(fn)
    params=sig.parameters
    found=False
    for name,param in params.items():
        if name=='request':
            found=True
            continue
        # 这里限制 request 参数只能放在这三种类型参数 1.可变参数 *args 2.命名关键字参数 *,aa,bb   3.关键字参数 **kw
        if found and (param.kind != inspect.Parameter.VAR_POSITIONAL and param.kind !=inspect.Parameter.KEYWORD_ONLY and param.kink!=inspect.Parameter.VAR_KEYWORD):
            raise ValueError('request parameter must be the last named parameter in function : %s%s'%(fn.__name__,str(sig)))
    return found



def index(*,zq,l):
    print('ss')

if(__name__=='__main__'):
    print('get_required_kw_args:',get_required_kw_args(index))
    print('get_named_kw_args:',get_named_kw_args(index))
    print('has_named_kw_args:',has_named_kw_args(index))
    print('has_var_kw_arg:',has_var_kw_arg(index))
    print('has_request_arg:',has_request_arg(index))






#
# 从URL 函数中分析 需要接受的参数，
# 并且调用处理函数
# 然后封装成需要的对象然后返回
#
class RequestHandler(object):

    #
    # fn 是处理url函数，里面有处理该页面请求逻辑
    #
    def __init__(self,app,fn):
        self._app=app
        self._func=fn
        self._has_request_arg=has_request_arg(fn)
        self._has_var_kw_arg=has_var_kw_arg(fn)
        self._has_named_kw_args=has_named_kw_args(fn)
        self._named_kw_args=get_named_kw_args(fn)
        self._required_kw_args=get_required_kw_args(fn)

    #
    #
    # 协程创建的 __call__  ，
    # 这里找了 request 参数从哪儿传入，找了很久，
    # 后面发现 request 参数是 由于 aiohttp 的处理函数 都会被传入一个 request 参数的
    # RequestHandler(app,fn) 在 add_route 时就相当于创建了一个 url 处理函数，
    # 然后 当然会在被aiohttp底层框架调用时传入一个 request
    # 对照下面 add_route(app,fn) 方法的注释理解
    #
    @asyncio.coroutine
    def __call__(self,request):
        kw=None
        # 是否含有 关键字参数  命名关键字参数  命名关键字参数不带默认值
        if self._has_var_kw_arg or self._has_named_kw_args or self._required_kw_args:
            if request.method=='POST':
                if not request.content_type:
                    return web.HTTPBadRequest(text='Missing Content-Type.')
                ct=request.content_type.lower()
                if ct.startswith('application/json'):
                    # 将请求转换成 json 类型
                    params=yield from request.json()
                    # 如果转换成功，params 会是字典类型
                    if not isinstance(params,dict):
                        return web.HTTPBadRequest(text='JSON body must be object .')
                    kw=params
                elif ct.startswith('appliction/x-www-form-urlencoded') or ct.startswith('multipart/form-data'):
                    # 返回一个 post 格式的参数 Return POST parameters
                    params=yield from request.post()
                    kw=dict(**params)
                else:
                    return web.HTTPBadRequest(text='Unsupported Content-Type: %s'%request.content_type)
            if request.method=='GET':
                qs=request.query_string
                if qs:
                    kw=dict()
                    for k,v in parse.parse_qs(qs,True).items():
                        kw[k]=v[0]

        # 如果 kw 为空 说明 不符合上面的三种参数规则，或者 不是 get post 请求，则给直接给参数赋值 请求里面的参数
        if kw is None:
            kw=dict(**request.match_info)
        else:
            if not self._has_var_kw_arg and self._named_kw_args:
                # 这里复制这一波 没有看懂 防止不必要参数？
                # 廖大大 注释是 remove all unamed kw
                # kw 数组里面存储的参数，有可能会和 处理函数的参数不一样，
                # kw 的参数是从 request 里面拿出来的
                # _named_kw_args 是处理函数的参数
                # 我们以 kw 里面的key 为主，筛选一遍 值
                copy=dict()
                for name in self._named_kw_args:
                    if name in kw:
                        copy[name]=kw[name]
                kw=copy
            #
            # kw 里面只有 用户的参数 没有url路径
            # 保存url的路径
            for k,v in request.match_info.items():
                if k in kw:
                    logging.warning('Duplicate arg name in named arg and kw args: %s'%k)
                kw[k]=v

        if self._has_request_arg:
            kw['request']=request

        # 再检查一遍参数
        if self._required_kw_args:
            for name in self._required_kw_args:
                if not name in kw:
                    return web.HTTPBadRequest(text='Missing argument:%s'%name)

        logging.info('call with args:$%s'%str(kw))
        try:
            r=yield from self._func(**kw)
            return r
        except APIError as e:
            return dict(error=e.error,data=e.data,message=e.message)


#
# 加载静态资源
def add_static(app):
    path=os.path.join(os.path.dirname(os.path.abspath(__file__)),'static')
    app.router.add_static('/static/',path)
    logging.info('add static %s => %s'%('/static/',path))

#
#注册一个 URL 处理函数
def add_route(app,fn):
    method=getattr(fn,'__method__',None)
    path=getattr(fn,'__route__',None)
    # 如果没有 __method__ __route__ 这两个属性
    # 说明 就没有用装饰类处理
    if path is None or method is None:
        raise ValueError('@get or @post not defined in %s .'%str(fn))
    if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
        fn=asyncio.coroutine(fn)
    logging.info('add route %s %s => %s(%s)'%(method,path,fn.__name__,','.join(inspect.signature(fn).parameters.keys())))
    # 调用 app 注册路由
    # 这里解释 RequestHandler 的 __call__ 方法中的 request 参数
    # 类似 app.router..add_route("GET","/","index") 注册路由处理函数时
    # 这里因为 RequestHandler 有 call 函数 ，所以 本身也可以作为一个函数来使用，所以，call 里面肯定会带有一个 request 参数
    # request参数实际上是一个继承于class aiohttp.web.BaseRequest的实例，
    # 而aiohttp.web.BaseRequest类包含了一个请求所携带的所有HTTP信息
    app.router.add_route(method,path,RequestHandler(app,fn))


#
# 扫描并加载所有的处理函数
def add_routes(app,module_name):
    n=module_name.rfind('.')
    if n==(-1):# 说明加载的是一个模块
        #导入一波该模块
        mod=__import__(module_name,globals(),locals())
    else:# 说明加载是 形如 handler.index 这样的处理函数,
        # 获取该处理函数的方法名
        name=module_name[n+1:]
        #导入模块，并获取该处理函数，此时该处理函数是这个模块的属性,getattr 获取该属性
        # module_name[:n] 这是获取的 处理函数所在的模块 比如 handler.index 就是获取的 handler
        mod=getattr(__import__(module_name[:n],globals(),locals(),[name]),name)

    # 获取到 mod 后遍历一边里面的属性
    # dir() 函数不带参数时，返回当前范围内的变量、方法和定义的类型列表；
    #       带参数时，返回参数的属性、方法列表。
    #       如果参数包含方法__dir__()，该方法将被调用。
    #       如果参数不包含__dir__()，该方法将最大限度地收集参数信息
    # 如果上面导入的是 模块，mod 是 内部含有很多的 「处理方法（属性）」的集合，
    # 如果是 导入的 handler.index 这样的处理函数 ，mod 是一个方法对象,也是可以传入 dir 的，
    # 但是没有理解 handler.index 这种导入方式 后面的循环处理方式 todo
    for attr in dir(mod):
        # 下划线的是私有属性，不是我们需要的 url处理函数
        if attr.startswith('_'):
            continue
        # 获取当前属性
        fn=getattr(mod,attr)
        # 如果该属性可以调用，即是方法函数，则表示是url处理函数
        if callable(fn):
            method=getattr(fn,'__method__',None)
            path=getattr(fn,'__route__',None)
            if method and path:
                add_route(app,fn)


