from odoo import http, tools
from odoo.http import request,Response,JsonRequest
import json
import datetime
from operator import itemgetter
from odoo.exceptions import AccessError,AccessDenied
import os
from pathlib import Path
from odoo.tools import date_utils
# from mobile_app_api.controllers.main import validate_token

def _json_response(self, result=None, error=None):
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

   # @validate_token
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
      
