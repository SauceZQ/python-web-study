# !/usr/bin/env
# _*_ coding:utf-8 _*_
import time
import uuid

from orm import Model, StringField, BooleanField, FloatField, TextField


def next_id():
    return '%015d%s000' % (int(time.time()*1000),uuid.uuid4().hex)

class User(Model):
    __table__ ='users'

    # 这个地方 default 缺省值 可以传入函数 当调用 save()时会自动计算
    id=StringField(primary_key=True,default=next_id,column_type='varchar(50)')
    email=StringField(column_type='varchar(50)')
    passwd=StringField(column_type='varchar(50)')
    admin=BooleanField()
    name=StringField(column_type='varchar(50)')
    image=StringField(column_type='varchar(500)')
    created_at=FloatField(default=time.time)

    # def __init__(self,id,email,passwd,admin,name,image,created_at):
    #     self.id=id
    #     self.email=email
    #     self.passwd=passwd
    #     self.admin=admin
    #     self.name=name
    #     self.image=image
    #     self.created_at=created_at

class Blog(Model):
    __table__='blogs'

    id=StringField(primary_key=True,default=next_id,column_type='varchar(50)')
    user_id=StringField(column_type='varchar(50)')
    user_name=StringField(column_type='varchar(50)')
    user_image=StringField(column_type='varchar(500)')
    name=StringField(column_type='varchar(50)')
    summary=StringField(column_type='varchar(200)')
    content=TextField()
    created_at=FloatField(default=time.time)

class Comment(Model):
    __table__='comments'

    id=StringField(primary_key=True,default=next_id,column_type='varchar(50)')
    blog_id=StringField(column_type='varchar(50)')
    user_id=StringField(column_type='varchar(50)')
    user_name=StringField(column_type='varchar(50)')
    user_image=StringField(column_type='varchar(500)')
    content=TextField()
    created_at=FloatField(default=time.time)


