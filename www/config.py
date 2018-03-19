# !/usr/bin/env
# _*_ coding:utf-8 _*_

import config_default, config_override


class Dict(dict):

    def __init__(self,names=(),values=(),**kw):
        super(Dict,self).__init__(**kw)
        for k,v in zip(names,values):
            self[k]=v


    # 可以使用 .属性 的方式访问 dict
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Dict' object has no attribute '%s'" % key)


    def __setattr__(self, key, value):
        self[key]=value

#
# 将默认配置 和 标准配置合并
# 按照标准配置优先
def merge(defaults,override):
    r={}
    for k,v in defaults.items():
        if k in override:
            # 这里如果是 config
            if isinstance(v,dict):
                r[k]=merge(v,override[k])
            else:
                r[k]=override[k]
        else:
            r[k]=v
    return r

def toDict(d):
    D=Dict()
    for k,v in d.items():
        D[k]=toDict(v) if isinstance(v,dict) else v
    return D

configs= config_default.configs

try:
    configs=merge(configs, config_override.configs)
except ImportError:
    pass

configs=toDict(configs)