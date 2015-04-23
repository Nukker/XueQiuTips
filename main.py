# -*- coding: utf-8 -*-
import urllib,urllib2
import os,time,sys
import cookielib
import json
import base64
import re
#发送邮件所需库
import email
import mimetypes
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.MIMEImage import MIMEImage
import smtplib

'''
<Introduction>
——————————————————————————————————————————
雪球网组合调仓提醒
a. 支持实时短信提醒（太贵了，尼玛买不起短信平台的服务）
b. 支持实时邮件提醒

'''
#常量
pre_url = r'http://www.xueqiu.com/cubes/rebalancing/history.json?cube_symbol='
login_url = r'http://xueqiu.com/user/login'
name_url = r'http://xueqiu.com/P/'
pre_id = 1000000	#设置一个较低的值，保证第一次对比的now_id比其大

#邮件相关常量
authInfo = {'server' : 'smtp.qq.com' , 'user' : 'xueqiutips@qq.com' , 'password' : 'XXX'}
fromAdd = 'xueqiutips@qq.com'


#获取cookie
cj = cookielib.CookieJar()
opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
urllib2.install_opener(opener)
#安装opener后，此后调用urlopen()都会使用安装过的opener(意思就是发的请求就是带cookie的了)

headers = {"User-Agent" : "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2062.102 Safari/537.36"}   #伪装成浏览器
data = {
	"areacode" : "86",
	"password" : "5124694000a",
	"remember_me" : "on",
	"telephone" : "18566699624"
	}
post_data = urllib.urlencode(data)
request = urllib2.Request(login_url,post_data,headers)
try:
	r = opener.open(request)
except urllib2.HTTPError, e:
	print u"该去输入验证码了啦"
	print e.code			#一般是400	


#获得组合的名字
def GetName(group):
	url = name_url + group
	request = urllib2.Request(url,headers = headers)
	try:
		result  = opener.open(request)
	except urllib2.HTTPError, e:
		print u"该去输入验证码了啦"
		print e.code
	
	content = result.read()
	name_patter = re.compile(r'<span class="name">(.*?)</span>')
	name = name_patter.findall(content)
	return name[0]

#把时间戳修改时间格式
def ChangeTime(timestamp):
	timestamp = timestamp/1000
	#timestamp += 28800
	#timeArray = time.gmtime(timestamp)
	timeArray = time.localtime(timestamp)
	timestr = time.strftime("%Y-%m-%d %H:%M:%S",timeArray)
	return timestr

#发送短信
def Sendmessage(phonenumber,message):
	url = 'https://sms-api.luosimao.com/v1/send.json'
	base64string = base64.encodestring('%s:%s' % ("api", "1674a71d8e1bf40d2777c007717bffc3"))[:-1]
	authheader = "Basic %s"%base64string
	values = {"mobile" : phonenumber ,
		"message" : message }
	data = urllib.urlencode(values)
	request = urllib2.Request(url,data)
	request.add_header("Authorization", authheader)

	try:
		result = urllib2.urlopen(request)
	except IOError,e:
		print "wrong api and key!"
		sys.exit(1)
	results = json.loads(result.read())
	print results

#发送邮件
def SendEmail(authInfo, fromAdd, toAdd, subject, htmlText):

	strFrom = fromAdd
	strTo = toAdd
	
	server = authInfo.get('server')
	user = authInfo.get('user')
	passwd = authInfo.get('password')

	if not (server and user and passwd) :
		print 'incomplete login info, exit now'
		return
	# 设定root信息
	msgRoot = MIMEMultipart('related')
	msgRoot['Subject'] = subject
	msgRoot['From'] = strFrom
	msgRoot['To'] = strTo
	msgRoot.preamble = 'This is a multi-part message in MIME format.'
	msgAlternative = MIMEMultipart('alternative')
	msgRoot.attach(msgAlternative)
	msgText = MIMEText(htmlText, 'html', 'utf-8')
	msgAlternative.attach(msgText)
	#发送邮件
	smtp = smtplib.SMTP()
	#设定调试级别，依情况而定
	# smtp.set_debuglevel(1)
	smtp.connect(server)
	smtp.login(user, passwd)
	smtp.sendmail(strFrom, strTo, msgRoot.as_string())
	smtp.quit()

#日志记录
def log(message,destination):
	fp = open('TIPSLOG.txt','a')
	nowtime = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(time.time()))
	fp.write(nowtime + "	" + message + "	" + destination + '\n')
	fp.close()

#监控
def Monitor(emailaddr,group):
	url = pre_url + group + '&count=1'
	request = urllib2.Request(url,headers = headers)
	result  = opener.open(request)
	try:
		s = json.loads(result.read())
	except Exception,e:
		print 'NOT FOUND JSON FILE'
	now_id = s["list"][0]["id"]
	status = s["list"][0]["status"]
	global pre_id
	# #初始化pre_id(只在第一次)
	# if isfirsttime:
	# 	pre_id = now_id
	# 	isfirsttime = False
	# 	#print pre_id
	# 	# stock_name = s["list"][0]["rebalancing_histories"][0]["stock_name"]
	# 	# prev_weight =  s["list"][0]["rebalancing_histories"][0]["prev_weight"]
	# 	# target_weight =  s["list"][0]["rebalancing_histories"][0]["target_weight"]
	# 	# print 'stock_name:',stock_name,' prev_weight:',prev_weight,' target_weight',target_weight		

	if now_id > pre_id and status == "success": 
		#当组合有调仓更新操作时,发送短信
		length = len(s["list"][0]["rebalancing_histories"])
		for i in range(length):
			name = GetName(group)
			time = ChangeTime(s["list"][0]["updated_at"])
			stock_name = s["list"][0]["rebalancing_histories"][i]["stock_name"]
			prev_weight =  s["list"][0]["rebalancing_histories"][i]["prev_weight"]
			target_weight = s["list"][0]["rebalancing_histories"][i]["target_weight"]
			if prev_weight == None : prev_weight = 0 
			if target_weight == None : target_weight =0
			message = '【雪球调仓提醒】您关注的组合' + name + group + ',于' + time + '调仓' + stock_name + ',仓位由' + str(prev_weight) + '%变为' + str(target_weight) + '%'
			log(message,emailaddr)
			print message
			htmlText = '<B>' + message + ' </B>'
			# Sendmessage(phonenumber,message)
			SendEmail(authInfo,fromAdd,emailaddr,message,htmlText)
		pre_id = now_id

if __name__ == '__main__' :
	data = {"j2211@qq.com" :"ZH191982",} 	#客户数据 group:phonenumber
	num = 0
	while True:
		for key in data.keys():
			Monitor(key,data[key])
		num += 1
		print num
