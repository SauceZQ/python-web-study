# !/usr/bin/env
# _*_ coding:utf-8 _*_
import datetime

from orm import Model, StringField, IntegerField, TextField, DateField


class bqw_chapter(Model):
    __table__='bqw_chapter'

    id=IntegerField(primary_key=True)
    cid=StringField(column_type='varchar(20)')
    section=IntegerField(column_type='int(10)')
    chaptername=StringField(column_type='varchar(30)')
    chapternum=StringField(column_type='varchar(30)')
    content=TextField()
    html_content=TextField()
    contenturl=TextField()
    status=IntegerField(column_type='int(20)')


class bqw_read_history(Model):
    __table__='history_read'
    id=IntegerField(column_type='int(20)',primary_key=True)
    novelname=StringField(column_type='varchar(50)')
    openid=StringField(column_type='varchar(200)')
    last_read_time=DateField()
    chapter_url=StringField(column_type='varchar(200)')
    chapter_name=StringField(column_type='varchar(200)')


class bqw_wx_formId(Model):
    __table__='wx_form_id'
    id=IntegerField(column_type='int(11)',primary_key=True)
    openid=StringField(column_type='varchar(100)')
    form_id=StringField(column_type='varchar(100)')
    status=IntegerField(column_type='int(2)',default=0)
    created_time=DateField(default=datetime.datetime.now())


class kmj_page_record(Model):
    __table__='kmj_page_record'
    id=IntegerField(column_type='int(100)',primary_key=True)
    in_time=DateField()
    route_path=TextField()
    user_id=StringField(column_type='varchar(255)')
    user_type=StringField(column_type='varchar(100)')
    next_path=TextField()
    serail_number=StringField(column_type='varchar(255)')
    token=StringField(column_type='varchar(255)',default="")
