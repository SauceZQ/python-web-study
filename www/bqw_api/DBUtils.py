#!/usr/bin/env 
#_*_ coding:utf-8 _*_
import mysql.connector

class DBUtils(object):
	OUTSTANDING=1001 					#等待状态。
	PROCESSING=1002						#正在爬取 ,默认不会出问题，可以爬取成功，但是未推送
	COMPLETE=1003						#已完成推送 
	TABLE_BQWNAME='bqw_name' 			#书名表名
	TABLE_BQWCHAPTER='bqw_chapter' 		#章节表名
	# 数据库参数
	username='root'
	password='z123456789q'
	database='awesome'
	
	DEBUG=False

	def __init__(self,timeout=300):
		# 初始化 mysql
		self.conn=mysql.connector.connect(user=self.username,password=self.password,database=self.database,buffered=True)
		self.cursor=self.conn.cursor()
		# 

	# 入队
	def saveNoContent(self,cid,section,chaptername,chapternum,contenturl):
		sql="INSERT INTO %s(cid,section,chaptername,chapternum,contenturl,status) VALUES('%s','%s','%s','%s','%s',%s)"%(self.TABLE_BQWCHAPTER,cid,section,chaptername,chapternum,contenturl,self.OUTSTANDING)
		if(self.DEBUG):
			print(sql)
		try:
			self.cursor.execute(sql)
			self.conn.commit()	
			result=self.cursor.rowcount
			if(result>0):
				if(self.DEBUG):
					print('入队成功')
		except Exception as e:
			if(self.DEBUG):
				print('push erro:',e)
			return []

	# 出队
	# 查询 状态为 OUTSTANDING 的记录
	# 出队成功，更改状态
	def pop(self):
		sql="SELECT * FROM %s WHERE status=%s"%(self.TABLE_BQWCHAPTER,self.OUTSTANDING)
		if(self.DEBUG):
			print(sql)
		try:
			self.cursor.execute(sql)
		except Exception as e:
			print('pop erro:',e)
			if(self.DEBUG):
				print('pop erro:',e)
		result=self.cursor.fetchone()
		if(result!=None):
			# 这里有一个自增的id
			bqwc=bqwChapter(result[1],result[2],result[3],result[4],result[5],result[6],result[7])
			# print('查询的对象',result)
			# print("转换的对象",bqwc.contenturl)
			# 出队成功，改变状态
			return bqwc if(self.changeStatusComplete(bqwc.contenturl)) else None
		else:
			print('所有等待状态已经出队')
			return None
	# 
	# 将数据库中，该小说状态为未爬取的小说拿出来
	# 
	def getAllOutstanding(self,chaptername):
		sql="SELECT * FROM %s WHERE status=%s and chaptername='%s'"%(self.TABLE_BQWCHAPTER,self.OUTSTANDING,chaptername)
		if(self.DEBUG):
			print(sql)
		try:
			self.cursor.execute(sql)
		except Exception as e:
			print('pop erro:',e)
			if(self.DEBUG):
				print('pop erro:',e)
		result=self.cursor.fetchall()
		return result

	# 
	# 更改状态为爬取完成 但未推送
	# 
	def changeStatusComplete(self,contenturl):
		sql="UPDATE %s SET status=%s WHERE contenturl='%s'"%(self.TABLE_BQWCHAPTER,self.PROCESSING,contenturl)
		if(DEBUG):
			print(sql)
		try:
			self.cursor.execute(sql)
			self.conn.commit()
			print('更新成功')
			return True
		except Exception as e:
			self.conn.rollback()
			# if(self.DEBUG):
			print('更改状态失败:',e)
			return False
	
	# 
	# 更改状态为已经推送
	def changeStatusHasSend(self,id):
		sql="UPDATE %s SET status=%s WHERE id=%s"%(self.TABLE_BQWCHAPTER,self.COMPLETE,id)
		if(self.DEBUG):
			print(sql)
		try:
			self.cursor.execute(sql)
			self.conn.commit()
			print('推送状态更改成功!')
			return True
		except Exception as e:
			self.conn.rollback()
			print('推送状态更改失败',e)
			return False



	# 保存到数据库
	def saveWithContent(self,contenturl,content,htmlContent):
		sql="UPDATE %s SET status=%s , content='%s' ,html_content='%s' WHERE contenturl='%s'"%(self.TABLE_BQWCHAPTER,self.PROCESSING,content,htmlContent,contenturl)
		if(self.DEBUG):
			print(sql)
		try:
			self.cursor.execute(sql)
			self.conn.commit()
			if(self.DEBUG):
				print('更新成功')
			return True
		except Exception as e:
			self.conn.rollback()
			if(self.DEBUG):
				print('更改状态失败:',e)
			return False

	# 
	# 获取最新的章节
	# 
	def searchNewChapter(self,title):
		sql="SELECT * FROM %s WHERE chaptername='%s' and status='%s' "%(self.TABLE_BQWCHAPTER,title,self.PROCESSING)
		if(self.DEBUG):
			print(sql)
		try:
			self.cursor.execute(sql)
			result=self.cursor.fetchall()
			if(self.DEBUG):
				print('查找的结果：',result)
			return result
		except Exception as e:
			if(self.DEBUG):
				print('searchChapter erro %s'%e)

	def close(self):
		self.cursor.close()
		self.conn.close()

class bqwChapter(object):
	def __init__(self, cid,section,chaptername,chapternum,content,htmlcontent,contenturl,status):
		self.cid= cid
		self.section=section
		self.chaptername=chaptername
		self.chapternum=chapternum
		self.content=content
		self.htmlcontent=htmlcontent
		self.contenturl=contenturl
		self.status=status
	
	def __str__(self):
		return "%s,%s,%s,%s,%s,%s,%s"%(self.cid,self.chaptername,self.chapternum,self.content,self.htmlcontent,self.contenturl,self.status)

if(__name__=='__main__'):
	dbUtils=DBUtils()
	result=dbUtils.searchChapter('我是至尊')
	print(result[0])
	if(result):
		lastchapter=result[len(result)-1]
		print(lastchapter[0],lastchapter[1],lastchapter[2],lastchapter[3])
	else:
		print('sss')



