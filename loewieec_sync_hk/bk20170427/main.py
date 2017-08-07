# -*- encoding: utf-8 -*-
from openerp import http
from openerp.http import request
import json

try: import httplib
except ImportError:
    import http.client as httplib

import logging
_logger = logging.getLogger(__name__)



class tmalljd_callback(http.Controller):

    @http.route(['/tmalljd_callback/jd'], type='http', auth="public", website=True)
    def tmalljd_callback(self,**arg):
        header = {
                 'Content-type': 'application/x-www-form-urlencoded;charset=UTF-8'
        }	
	
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry	
        shop_id = pool.get('loewieec.shop').search(cr,uid,[('appkey', '=', '0095ABD0C47C84AE9C393DF018A41A1F')], order="name asc")			
        if shop_id : 
            shop_obj = pool.get('loewieec.shop').browse(cr, uid, shop_id, context=context)	
        auth_code = ''            		
        if 'code' in request.params.keys():
            auth_code = request.params['code']		
            if shop_id : shop_obj.tokenurl = auth_code			
            url = '/oauth/token?grant_type=authorization_code&client_id=%s&redirect_uri=%s&scope=read&code=%s&client_secret=%s' % (shop_obj.appkey,shop_obj.authurl,auth_code,shop_obj.appsecret)		
            connection = httplib.HTTPSConnection('oauth.jd.com')
            connection.request("POST", url,headers=header)			
            response = connection.getresponse();
            if response.status is not 200:            			
                raise Exception('invalid http status ' + str(response.status) + ',detail body:' + response.read())	
            result = response.read()
            jsonobj = json.loads(result)
            shop_obj.last_log = jsonobj
            shop_obj.access_token = jsonobj.get('access_token')			
            shop_obj.access_token = jsonobj.get('access_token')				
        return 'OK, Thanks'
		
	
	