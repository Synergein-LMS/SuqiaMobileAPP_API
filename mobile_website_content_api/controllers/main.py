from odoo import http, tools
from odoo.http import request,Response,JsonRequest
import json
import datetime
from operator import itemgetter
from odoo.exceptions import AccessError,AccessDenied
import os
from pathlib import Path
from odoo.tools import date_utils
import functools
from OpenSSL import crypto
import OpenSSL.crypto 
import base64

def validate_crt(func):
   """."""
   @functools.wraps(func)
   def wrap(self, *args, **kwargs):
      """."""
      try:
         ssl_crt = request.httprequest.headers.get("ssl_crt")
         if not ssl_crt:
            return error_response("ssl_crt_not_found", "missing ssl_crt in request header", 401)
         json_file_path = os.path.join(str(Path(__file__).parent.parent)+'/static/','selfsigned'+'.crt')
         open_internal_ssl_crt = open(json_file_path,'r').read()
         base64_bytes = ssl_crt.encode('ascii')
         message_bytes = base64.b64decode(base64_bytes)
         message = message_bytes.decode('ascii')
         print(message)
         if message.replace('\n', '') != open_internal_ssl_crt.replace('\n', ''):
            return error_response("ssl_crt", "ssl crt to be not matched", 401)
         crtObj_header = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM,message)
         crtObj_internal_data = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM,open(json_file_path,'r').read())
         
         dict_crtObj_header = dict(crtObj_header.get_subject().get_components())
         rm_bytes_header = {y.decode('ascii'): dict_crtObj_header.get(y).decode('ascii') for y in dict_crtObj_header.keys()}
         dict_crtObj_internal_data = dict(crtObj_internal_data.get_subject().get_components())
         rm_bytes_internal_data_header = {y.decode('ascii'): dict_crtObj_internal_data.get(y).decode('ascii') for y in dict_crtObj_internal_data.keys()}
         if rm_bytes_header.get('C') != rm_bytes_internal_data_header.get('C') or rm_bytes_header.get('ST') != rm_bytes_internal_data_header.get('ST') or rm_bytes_header.get('L') != rm_bytes_internal_data_header.get('L')\
            or rm_bytes_header.get('O') != rm_bytes_internal_data_header.get('O') or rm_bytes_header.get('OU') != rm_bytes_internal_data_header.get('OU') or rm_bytes_header.get('CN') != rm_bytes_internal_data_header.get('CN')\
            or rm_bytes_header.get('emailAddress') != rm_bytes_internal_data_header.get('emailAddress') or crtObj_header.get_serial_number() != crtObj_internal_data.get_serial_number():
            return error_response("ssl_crt", "ssl crt to be not matched", 401)
         if crtObj_header.has_expired():
            return error_response("ssl_crt", "ssl crt has been expired", 401)
         return func(self, *args, **kwargs)
      except Exception as e:
         print(e)
         return error_response("ssl_crt", "ssl crt to be not matched", 401)
   return wrap

def _json_response(self, result=None, error=None):
   print(self.endpoint.routing)
   web_content_api = self.endpoint.routing.get('web_content_api')
   response = {}
   if web_content_api:
      response = {}
      if error is not None:
         response = error
      if result is not None:
         response = result
   else:
      response = {
         'jsonrpc': '2.0',
         'id': self.jsonrequest.get('id')
         }
      if error is not None:
         response['error'] = error
      if result is not None:
         response['result'] = result
   mime = 'application/json'
   body = json.dumps(response, default=date_utils.json_default)

   return Response(
      body, status=error and error.pop('http_status', 200) or 200,
      headers=[('Content-Type', mime), ('Content-Length', len(body))]
   )
     
setattr(JsonRequest,'_json_response',_json_response) #overwrite the method
        

def error_response(error, msg,code):
   return {
      "error": {
         "code": code,
         "message": "error",
         "data": {
            "name": str(error),
            "message": msg,
           
         }
      }
   }


# def success_response(data):
#    return {
#       "status": 200,
#       "message": "success",
#       "data": data
#    }
class MobileContantAPI(http.Controller):

   @validate_crt
   @http.route('/api/get-page-content/', type='json', auth="none",csrf=False,web_content_api=True)
   def GetPageContent(self,**kw):
      try:
         if not kw.get('page_id'):
            return error_response('Parameter Missing','Please give the page_id',200)
         elif not kw.get('lang'):
            return error_response('Parameter Missing','Please give the lang',200)
         cur_dir = Path.cwd()
         print(os.path.join(str(Path(__file__).parent.parent)))
         json_file_path = os.path.join(str(Path(__file__).parent.parent)+'/static/json',kw.get('page_id')+'-'+kw.get('lang')+'.json')
         with open(json_file_path,encoding="utf8") as f:
            data= f.read()
         file_name = kw.get('page_id')+'-'+kw.get('lang')
         datas = json.loads(data)
         print(len(['award-ar','award-en','engaging-youth-ar','engaging-youth-en','our-impacts-ar','our-impacts-en','our-solutions-en','our-solutions-ar','about-us-ar','about-us-en','award-categories-ar','award-categories-en','our-impacts-en','our-impacts-ar','innovation-and-water-en','innovation-and-water-ar','contact-us-en','contact-us-ar','donation-en','donation-ar','evaluation-criteria-en','evaluation-criteria-ar','hands-in-the-field-en','hands-in-the-field-ar','meet-the-winners-ar','meet-the-winners-en','our-programmes-en','our-programmes-ar','year-of-zayed-en','year-of-zayed-ar','why-water-en','why-water-ar','simple-immediate-solutions-ar','simple-immediate-solutions-en']),'+++++++++++++++++++++++++++++++++++++++++')
         if file_name in ['award-ar','award-en','engaging-youth-ar','engaging-youth-en','our-impacts-ar','our-impacts-en','our-solutions-en','our-solutions-ar','about-us-ar','about-us-en','award-categories-ar','award-categories-en','our-impacts-en','our-impacts-ar','innovation-and-water-en','innovation-and-water-ar','contact-us-en','contact-us-ar','donation-en','donation-ar','evaluation-criteria-en','evaluation-criteria-ar','hands-in-the-field-en','hands-in-the-field-ar','meet-the-winners-ar','meet-the-winners-en','our-programmes-en','our-programmes-ar','year-of-zayed-en','year-of-zayed-ar','why-water-en','why-water-ar','simple-immediate-solutions-ar','simple-immediate-solutions-en','faqs-en','faqs-ar','our-partner-en','our-partner-ar']:
            base_url = http.request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            datas['data'].update({'img_base_url':base_url})
         print(datas)
         return datas
      except Exception as a:
         print(a,';;;;;;;;;;;;')
         # msg = "Error: %s" % aee.name
         return error_response('Access error', 'No API defined in this ID',200)
      
