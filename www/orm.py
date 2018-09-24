# !/usr/bin/env
# _*_ coding:utf-8 _*_


import asyncio
import datetime
import json
import logging
import aiomysql


#
# sql 日志
def log(sql, arg=()):
    logging.info("SQL:%s" % sql)


#
# 连接池
@asyncio.coroutine
def create_pool(loop, **kw):
    logging.info('create database connection pool...')
    global __pool
    __pool = yield from aiomysql.create_pool(
        host=kw.get('host', 'localhost'),
        port=kw.get('port', 3306),
        user=kw['user'],
        password=kw['password'],
        db=kw['database'],
        charset=kw.get('charset', 'utf8'),
        autocommit=kw.get('autocommit', True),
        maxsize=kw.get('maxsize', 10),
        minsize=kw.get('minsize', 1),
        loop=loop
    )


#
# 查询操作
#
@asyncio.coroutine
def select(sql, args, size=None):
    log(sql, args)
    global __pool
    with (yield from __pool)as conn:  # todo
        # 获取游标
        cur = yield from conn.cursor(aiomysql.DictCursor)
        # 执行查询 sql ,这里需要替换占位符， SQL 语句的占位符时 ？ mysql 的占位符是 %s
        yield from cur.execute(sql.replace('?', '%s'), args or ())
        # 如果有查询条数，则按查询条数返回，如果没有就返回所以
        if size:
            result = yield from cur.fetchmany(size)
        else:
            result = yield from cur.fetchall()
        logging.info('rows returned :%s' % len(result))
        # 关闭游标
        yield from cur.close()
        return result


#
# 插入、修改、删除操作
@asyncio.coroutine
def execute(sql, args):
    log(sql)
    with(yield from __pool) as conn:
        try:
            cur = yield from conn.cursor()
            yield from cur.execute(sql.replace('?', '%s'), args)
            affected = cur.rowcount
            yield from cur.close()
        except BaseException as e:
            raise
        return affected


#
# 创建一个 sql 参数占位符
def create_args_string(num):
    L = []
    for n in range(num):
        L.append('?')
    return ','.join(L)


#
# Field 基础类
class Field(object):
    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default

    def __str__(self):
        return '<%s,%s:%s>' % (self.__class__.__name__, self.column_type, self.name)


#
# varchar 映射的 StringField 类
class StringField(Field):
    def __init__(self, name=None, primary_key=False, default=None, column_type='varchar(100)'):
        super().__init__(name, column_type, primary_key, default)


#
# boolean
class BooleanField(Field):
    def __init__(self, name=None, primary_key=False, default=False, column_type='boolean'):
        super().__init__(name, column_type, primary_key, default)


#
# int 映射 IntegerField 类
class IntegerField(Field):
    def __init__(self, name=None, primary_key=False, default=0, column_type='bigint'):
        super().__init__(name, column_type, primary_key, default)


#
# float 映射 FloatField 类
class FloatField(Field):
    def __init__(self, name=None, primary_key=False, default=0.0, column_type='real'):
        super().__init__(name, column_type, primary_key, default)


#
# text 映射 TextField 类
class TextField(Field):
    def __init__(self, name=None, primary_key=False, default=None, column_type='text'):
        super().__init__(name, column_type, primary_key, default)


#
# timestamp 映射 DateField 类
class DateField(Field):
    def __init__(self, name=None, primary_key=False, default=None, column_type='timestamp'):
        super().__init__(name, column_type, primary_key, default)


#
# json 序列化的时候 datetime 需要重新处理
# 这里重写json，遇到datetime时按照格式处理，其他时候用内置的处理
class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, datetime.date):
            return obj.strftime("%Y-%m-%d")
        else:
            return json.JSONEncoder.default(self, obj)


#
# ModelMetaclass
class ModelMetaclass(type):
    def __new__(cls, name, bases, attrs):
        if name == 'Model':
            return type.__new__(cls, name, bases, attrs)

        # 获取 table 名称
        tableName = attrs.get('__table__', None) or name
        logging.info('found model:%s(table:%s)' % (name, tableName))
        # 获取 Field 和主键名
        mappings = dict()  # key 是属性 value 是表的字段对象 如 id=IntegerField
        fields = []
        primaryKey = None
        for k, v in attrs.items():
            # print('%s=%s'%(k,v))
            if isinstance(v, Field):
                logging.info('found mappings:%s ==> %s' % (k, v))
                mappings[k] = v
                if v.primary_key:
                    if primaryKey:
                        raise RuntimeError(
                            'There are have more than one primary key for field ? %s and %s' % (primaryKey, k))
                    primaryKey = k
                else:
                    fields.append(k)
        # print(mappings)

        if not primaryKey:
            raise RuntimeError('Primary key not found!')
        # 将实例属性剔除去，不能影响类属性
        for k in mappings.keys():
            attrs.pop(k)
        # 构造一个元素为 ['`属性名`',] 的 list，用于 查询时拼接 sql ，不过这里面没有主键
        escaped_fields = list(map(lambda f: '`%s`' % f, fields))

        # 保存属性与列的映射关系
        attrs['__mappings__'] = mappings
        # 保存表名
        attrs['__table__'] = tableName
        # 保存主键
        attrs['__primary_key__'] = primaryKey
        # 除了主键以外的字段
        attrs['__fields__'] = fields

        # 构造默认的 增删改查 的sql语句
        attrs['__select__'] = 'SELECT `%s` ,%s FROM `%s`' % (primaryKey, ','.join(escaped_fields), tableName)
        # 这里因为有一个主键 所以占位符需要 +1
        attrs['__insert__'] = 'INSERT INTO `%s`(%s,`%s`) VALUES(%s)' % (tableName, ','.join(escaped_fields),
                                                                        primaryKey,
                                                                        create_args_string(len(escaped_fields) + 1))
        attrs['__update__'] = 'UPDATE `%s` SET %s WHERE `%s`= ? ' % (tableName,
                                                                     ','.join(map(lambda f: '`%s`=?' % (
                                                                         mappings.get(f).name or f), fields)),
                                                                     primaryKey)
        attrs['__delete__'] = 'DELETE FROM `%s` WHERE `%s`=?' % (tableName, primaryKey)

        # 返回要实例的对象
        return type.__new__(cls, name, bases, attrs)


#
# Model 类
class Model(dict, metaclass=ModelMetaclass):
    def __init__(self, **kw):
        super(Model, self).__init__(**kw)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Model' object has no attribute '%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value

    def getValue(self, key):
        return getattr(self, key, None)

    def getValueOrDefault(self, key):
        value = getattr(self, key, None)
        if value is None:
            # 属性里面找不到 就去 映射关系里面找
            field = self.__mappings__[key]
            if field.default is not None:
                value = field.default() if callable(field.default) else field.default
                logging.debug('using default value for %s:%s' % (key, str(value)))
                setattr(self, key, value)
        return value

    #
    # 这里为了比较两个对象是否属性值一样，自己定义了一个方法
    # 没有找到应该重写那个内置方法，
    # 这里不想递归比较，各种判断类型，然后就转换成了json来比较
    def equals(self, other):
        originStr = json.dumps(self, cls=DateEncoder)
        otherStr = json.dumps(other, cls=DateEncoder)
        return originStr == otherStr

    # 添加 class 方法 所有子类都可以调用
    #
    # 按照主键查找
    # cls 是当前类对象，即子类
    @classmethod
    @asyncio.coroutine
    def find(cls, pkValue):
        sql = '%s WHERE `%s`=?' % (cls.__select__, cls.__primary_key__)
        result = yield from select(sql, [pkValue], 1)
        if len(result) == 0:
            return None
        # 这里 cls 指的是映射的类 比如 user ，然后根据查询的参数，构造返回了一个 user 实例
        return cls(**result[0])

    #
    # 按条件查找
    @classmethod
    @asyncio.coroutine
    def findAll(cls, where=None, args=None, **kw):
        sql = [cls.__select__]
        if where:
            sql.append('where')
            sql.append(where)
        if args is None:
            args = []

        groupBy = kw.get('groupBy', None)
        if groupBy:
            sql.append(" GROUP BY ")
            sql.append(groupBy)

        orderBy = kw.get('orderBy', None)
        if orderBy:
            sql.append(' ORDER BY ')
            sql.append(orderBy)
        limit = kw.get('limit', None)
        if limit is not None:
            sql.append('limit')
            if isinstance(limit, int):
                sql.append('?')
                args.append(limit)
            elif isinstance(limit, tuple) and len(limit) == 2:
                sql.append('?,?')
                # 在参数序列中追加 limit 中的多个元素
                args.extend(limit)
            else:
                raise ValueError('Invalid limit value:%s' % str(limit))
        result = yield from select(' '.join(sql), args)
        return [cls(**r) for r in result]

    #
    # 微信formid 特殊查询语句
    @classmethod
    @asyncio.coroutine
    def findWxFormId(cls):
        # form_id 7天有效
        now = datetime.datetime.now()
        offset = now + datetime.timedelta(days=-7)
        print(offset)
        sql = "select `id`,`openid`,`form_id`, `status`,`is_push`,min(`created_time`) as 'created_time' from (select *  from wx_form_id where `created_time` > '%s' and `status`=0 and `is_push`=1) as temp group by `openid`" % offset
        result=yield from select(sql,[])
        return [cls(**r) for r in result]




    #
    # 按照 Where 条件查找，返回的是整数
    @classmethod
    @asyncio.coroutine
    def findNumber(cls, selectField, where=None, args=None):
        sql = ['SELECT %s as _num_ FROM `%s`' % (selectField, cls.__table__)]
        if where:
            sql.append('WHERE')
            sql.append(where)
        result = yield from select(' '.join(sql), args, 1)
        if len(result) == 0:
            return None
        return result[0]['_num_']

    #
    # 插入
    @asyncio.coroutine
    def save(self):
        args = list(map(self.getValueOrDefault, self.__fields__))
        args.append(self.getValueOrDefault(self.__primary_key__))
        rows = yield from execute(self.__insert__, args)
        if rows != 1:
            logging.warning('failed to insert record :affected rows:%s' % rows)
        return rows

    #
    # 修改
    @asyncio.coroutine
    def update(self):
        args = list(map(self.getValueOrDefault, self.__fields__))
        args.append(self.getValueOrDefault(self.__primary_key__))
        rows = yield from execute(self.__update__, args)
        if rows != 1:
            logging.warning('failed to update record : affected rows:%s' % rows)
        return rows

    #
    # 删除
    @asyncio.coroutine
    def remove(self):
        args = [self.getValue(self.__primary_key__)]
        rows = yield from execute(self.__delete__, args)
        if rows != 1:
            logging.warning('failed to remove by primary key:affected rows:%s' % rows)
