# -*- coding: utf-8 -*-
from base import JDRestApi
class OverseasOrderSopDelivery(JDRestApi):
	def __init__(self,domain='api.jd.com',port=443, appkey='', secret=''):
		JDRestApi.__init__(self,domain, port, appkey, secret)
		self.fields = None

	def getapiname(self):
		return '360buy.overseas.order.sop.delivery'
