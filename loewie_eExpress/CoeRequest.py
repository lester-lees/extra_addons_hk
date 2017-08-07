# -*- coding: utf-8 -*-
try: import httplib
except ImportError:
    import http.client as httplib
import hashlib
import urllib
from urllib import quote,unquote
from xmltodict import parse
import chardet
	
class CoeRequest(object):
        
    def get_request_header(self):   
        return {
                 'Content-type': 'application/x-www-form-urlencoded;charset=UTF-8',
        } 

    def getCancelResponse(self, xml=None):
	
        connection = httplib.HTTPConnection('etk.coe.com.hk')	
        sign = hashlib.md5( xml + '91c4eff7651f5587' ).hexdigest().upper()	
	
        parameters = {
            "content":xml,
            "token":'024b03d60df918ae',
            "appType":'etk',
            "sign":sign,			
        }	
		
        url = "/coeimport/orderApi?" + urllib.urlencode(parameters)	
		
        header = self.get_request_header();            

        connection.request('POST', url, headers=header)
        response = connection.getresponse();
        if response.status is not 200:
            return {'success':False,'msg':'invalid http status ' + str(response.status) + ',detail body:' + response.read()}
        result = response.read()
        jsonobj = parse(result)
        responses = jsonobj.get("responses")
        item = responses and responses.get('responseItems') or ''
        res = item and item.get('response')	or ''
        success = res and res.get('success','') or 'false'
		
        if success == 'false' : 
            return {'success':False, 'msg': 'reason:%s, errorInfo:%s.' % (res.get('reason'), res.get('errorInfo')) }
        else:
            return {'success':True, 'trackingNo': res.get('trackingNo')}			
		
    def getResponse(self, xml=None):
	
        connection = httplib.HTTPConnection('etk.coe.com.hk')
        char_type2 = chardet.detect(xml)			
        sign = hashlib.md5( xml + '91c4eff7651f5587' ).hexdigest().upper()
	
        parameters = {
            "content":xml,
            "token":'024b03d60df918ae',
            "appType":'etk',
            "sign":sign,			
        }		
		
        url = "/coeimport/orderApi"	
        body = 	urllib.urlencode(parameters)	
        char_url1 = chardet.detect(url)		
        url = url.encode('utf-8')	
        char_url2 = chardet.detect(url)		
        header = self.get_request_header();            

        connection.request('POST', url, body=body, headers=header)
        response = connection.getresponse();
        if response.status is not 200:
            return {'success':False,'msg':'invalid http status ' + str(response.status) + ',detail body:' + response.read()}
        result = response.read()
        char_type3 = chardet.detect(result)			
        jsonobj = parse(result)
        responses = jsonobj.get("responses")
        item = responses and responses.get('responseItems') or ''
        res = item and item.get('response')	or ''
        success = res and res.get('success',False) or 'false'
		
        if success == 'false' : 
            return {'success':False, 'msg': 'reason:%s, errorInfo:%s.' % (res.get('reason'), res.get('errorInfo')) }
        else:
            return {'success':True, 'trackingNo': res.get('trackingNo')}	
		