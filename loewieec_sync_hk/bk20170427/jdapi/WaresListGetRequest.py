# -*- coding: utf-8 -*-
from base import JDRestApi
class WaresListGetRequest(JDRestApi):
	def __init__(self,domain='api.jd.com',port=443, appkey='', secret=''):
		JDRestApi.__init__(self,domain, port, appkey, secret)
		#self.fields = None
		#self.itemNum = None

	def getapiname(self):
		return '360buy.wares.list.get'
