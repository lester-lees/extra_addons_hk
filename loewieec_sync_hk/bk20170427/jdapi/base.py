# -*- coding: utf-8 -*-
try: import httplib
except ImportError:
    import http.client as httplib
import urllib
import time
from datetime import datetime
import hashlib
import json
import itertools
import mimetypes

'''
定义一些系统变量
'''

SYSTEM_GENERATE_VERSION = "jd-sdk-python-20160822"

P_APPKEY = "app_key"
P_API = "method"
#P_SESSION = "session"
P_ACCESS_TOKEN = "access_token"
P_VERSION = "v"
P_FORMAT = "format"
P_TIMESTAMP = "timestamp"
P_SIGN = "sign"
P_SIGN_METHOD = "sign_method"
P_PARTNER_ID = "partner_id"

P_CODE = 'code'
P_EN_DESC = 'en_desc'
P_ZH_DESC = 'zh_desc'


N_REST = '/routerjson'

def semble_app_parameter(param_jsons):
        param_list = []		
        for key in param_jsons.keys():
            param_list.append( '"%s":"%s"' % (key,param_jsons[key]) )
        return "{%s}" % ",".join(param_list)

def sign(secret, parameters):
    #===========================================================================
    # '''签名方法
    # @param secret: 签名需要的密钥
    # @param parameters: 支持字典和string两种
    # '''
    #===========================================================================
    # 如果parameters 是字典类的话
    if hasattr(parameters, "items"):
        keys = parameters.keys()
        keys.sort()	
		
        body =  str().join('%s%s' % (key, parameters[key]) for key in keys)       
        parameters = "%s%s%s" % (secret, body, secret)
    sign = hashlib.md5(parameters).hexdigest().upper()
    return sign

def mixStr(pstr):
    if(isinstance(pstr, str)):
        return pstr
    elif(isinstance(pstr, unicode)):
        return pstr.encode('utf-8')
    else:
        return str(pstr)
    
class FileItem(object):
    def __init__(self,filename=None,content=None):
        self.filename = filename
        self.content = content

class MultiPartForm(object):
    """Accumulate the data to be used when posting a form."""

    def __init__(self):
        self.form_fields = []
        self.files = []
        self.boundary = "PYTHON_SDK_BOUNDARY"
        return
    
    def get_content_type(self):
        return 'multipart/form-data; boundary=%s' % self.boundary

    def add_field(self, name, value):
        """Add a simple field to the form data."""
        self.form_fields.append((name, str(value)))
        return

    def add_file(self, fieldname, filename, fileHandle, mimetype=None):
        """Add a file to be uploaded."""
        body = fileHandle.read()
        if mimetype is None:
            mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        self.files.append((mixStr(fieldname), mixStr(filename), mixStr(mimetype), mixStr(body)))
        return
    
    def __str__(self):
        """Return a string representing the form data, including attached files."""
        # Build a list of lists, each containing "lines" of the
        # request.  Each part is separated by a boundary string.
        # Once the list is built, return a string where each
        # line is separated by '\r\n'.  
        parts = []
        part_boundary = '--' + self.boundary
        
        # Add the form fields
        parts.extend(
            [ part_boundary,
              'Content-Disposition: form-data; name="%s"' % name,
              'Content-Type: text/plain; charset=UTF-8',
              '',
              value,
            ]
            for name, value in self.form_fields
            )
        
        # Add the files to upload
        parts.extend(
            [ part_boundary,
              'Content-Disposition: file; name="%s"; filename="%s"' % \
                 (field_name, filename),
              'Content-Type: %s' % content_type,
              'Content-Transfer-Encoding: binary',
              '',
              body,
            ]
            for field_name, filename, content_type, body in self.files
            )
        
        # Flatten the list and add closing boundary marker,
        # then return CR+LF separated data
        flattened = list(itertools.chain(*parts))
        flattened.append('--' + self.boundary + '--')
        flattened.append('')
        return '\r\n'.join(flattened)

class JosException(Exception):
    #===========================================================================
    # 业务异常类
    #===========================================================================
    def __init__(self):
        self.errorcode = None
        self.en_desc = None
        self.zh_desc = None
        self.application_host = None
        self.service_host = None
    
    def __str__(self, *args, **kwargs):
        sb = "errorcode=" + mixStr(self.errorcode) +\
            " en_desc=" + mixStr(self.en_desc) +\
            " zh_desc=" + mixStr(self.zh_desc) +\
            " application_host=" + mixStr(self.application_host) +\
            " service_host=" + mixStr(self.service_host)
        return sb

class JDRestApi(object):
    def __init__(self, domain='api.jd.com', port = 443, appkey='', secret=''):
        self.__domain = domain
        self.__port = port
        self.__httpmethod = "POST"
        self.__app_key = appkey
        self.__secret = secret		
        
    def get_request_header(self):
        return {
                 'Content-type': 'application/x-www-form-urlencoded;charset=UTF-8',
                 "Cache-Control": "no-cache",
                 "Connection": "Keep-Alive",
        }
        
    def set_app_info(self, appinfo):
        self.__app_key = appinfo.appkey
        self.__secret = appinfo.secret
        
    def getapiname(self):
        return ""
    
    def getMultipartParas(self):
        return [];

    def getTranslateParas(self):
        return {};
    
    def _check_requst(self):
        pass
    
    def getResponse(self, access_token=None, timeout=30):
        if not access_token : return False
		
        connection = httplib.HTTPSConnection(self.__domain)
        sys_parameters = {
            P_ACCESS_TOKEN : access_token,
            P_APPKEY: self.__app_key,
            P_FORMAT: 'json',	
            P_API: self.getapiname(),			
            P_TIMESTAMP: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),	
            P_VERSION: '2.0',			
        }
  
        application_parameter = {'360buy_param_json':semble_app_parameter(self.getApplicationParameters())}
		
        sign_parameter = sys_parameters.copy()
        sign_parameter.update(application_parameter)
        sys_parameters[P_SIGN] = sign(self.__secret, sign_parameter)        
        header = self.get_request_header();
        if(self.getMultipartParas()):
            form = MultiPartForm()
            for key, value in application_parameter.items():
                form.add_field(key, value)
            for key in self.getMultipartParas():
                fileitem = getattr(self,key)
                if(fileitem and isinstance(fileitem,FileItem)):
                    form.add_file(key,fileitem.filename,fileitem.content)
            body = str(form)
            header['Content-type'] = form.get_content_type()
        else:
            body = urllib.urlencode(application_parameter)
            
        url = N_REST + "?" + urllib.urlencode(sys_parameters)
        connection.request(self.__httpmethod, url, body=body, headers=header)
        response = connection.getresponse();
        if response.status is not 200:
            raise Exception('invalid http status ' + str(response.status) + ',detail body:' + response.read())
        result = response.read()
        jsonobj = json.loads(result)
        if jsonobj.has_key("error_response"):
            error = JosException()
            if jsonobj["error_response"].has_key(P_CODE) :
                error.errorcode = jsonobj["error_response"][P_CODE]
            if jsonobj["error_response"].has_key(P_EN_DESC) :
                error.en_desc = jsonobj["error_response"][P_EN_DESC]
            if jsonobj["error_response"].has_key(P_ZH_DESC) :
                error.zh_desc = jsonobj["error_response"][P_ZH_DESC]
            error.application_host = response.getheader("Application-Host", "")
            error.service_host = response.getheader("Location-Host", "")
            raise error
        return jsonobj
       
    def getApplicationParameters(self):
        application_parameter = {}
        for key, value in self.__dict__.iteritems():
            if not key.startswith("__") and not key in self.getMultipartParas() and not key.startswith("_JDRestApi__") and value is not None :
                if(key.startswith("_")):
                    application_parameter[key[1:]] = value
                else:
                    application_parameter[key] = value
        #查询翻译字典来规避一些关键字属性
        translate_parameter = self.getTranslateParas()
        for key, value in application_parameter.iteritems():
            if key in translate_parameter:
                application_parameter[translate_parameter[key]] = application_parameter[key]
                del application_parameter[key]
        return application_parameter
