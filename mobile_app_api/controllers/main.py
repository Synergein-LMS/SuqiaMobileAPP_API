from odoo import http, tools,_
from odoo.http import request
import json
import datetime
from operator import itemgetter
from odoo.exceptions import AccessError,AccessDenied
import logging
_logger = logging.getLogger(__name__)
import collections
from odoo.addons.auth_signup.models.res_users import SignupError
import os
from pathlib import Path
from odoo.tools import date_utils
import functools
from OpenSSL import crypto
import OpenSSL.crypto 
import base64

TOKEN = 'a7e74538828a5dcd6f50a9ea23d3604ec14678da89be7f7d33b993e49158bca7'
expires_in = "mobile_app_api.access_token_expires_in"

def error_response(error, msg,code):
   return {
      "error": {
         "code": code,
         "message": "error",
         "data": {
            "name": str(error),
            "debug": "",
            "message": msg,
            "arguments": [error],
            "exception_type": type(error).__name__
         }
      }
   }


def success_response(data):
   return {
      "status": 200,
      "message": "success",
      
         "data": data
      
   }


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

def validate_token(func):
   @functools.wraps(func)
   def wrap(self, *args, **kwargs):
      data_kw = json.loads(request.httprequest.data)
      try:
         access_token = request.httprequest.headers.get("access_token")
         if not access_token:
            return error_response("access_token_not_found", "missing access token in request header", 401)
         access_token_data = (
            request.env["api.access_token"].sudo().search([("token", "=", access_token),('user_id','=',int(data_kw.get('params')['uid']))], order="id DESC", limit=1)
         )
         if access_token_data.find_one_or_create_token(user_id=access_token_data.user_id.id) != access_token:
            return error_response("access_token", "token seems to have expired or invalid", 401)

         request.session.uid = access_token_data.user_id.id
         request.uid = access_token_data.user_id.id
         return func(self, *args, **kwargs)
      except Exception as e:
         return error_response(e,e, 401)
   return wrap
    
class MobileAPI(http.Controller):

   # @validate_token
   @http.route('/api/user_auth', type='json', auth="none")
   def users_authenticate(self, db, login, password):
      data_dict = {}
      try:
         users = request.env['res.users']
         user = users.sudo().search([('login', '=', login)], order=users._get_login_order(), limit=1)
         try:
            if not user:
               raise AccessDenied()
         except AccessDenied as ade:
               msg = "Invalid Login" 
               return error_response(ade, msg,200)
         user = user.with_user(user)
         try:
            user._check_credentials(password)
         except AccessDenied as ade:
            msg = "Invalid Password"
            return error_response(ade, msg,200)
         rec_id = request.session.authenticate(db, login, password)
         data = request.env['res.users'].browse(rec_id)
         print(data,request.session.sid)
         # data_dict = {'odoo_id':data.id,'login':data.login,'name':data.name,'phone':data.phone,'email':data.email}
      except AccessError as aee:
         msg = "Error: %s" % aee.name
         return error_response(aee, msg,200)
      except AccessDenied as ade:
         msg = "Login or password invalid"
         return error_response(ade, msg,200)
      except Exception as e:
         error = "Invalid Database"
         return error_response(e, error,403)
      data_dict = request.env['ir.http'].session_info()
      json_file_path = os.path.join(str(Path(__file__).parent.parent)+'/static/','selfsigned'+'.crt')
      open_internal_ssl_crt = open(json_file_path,'r').read()
      sample_string = open_internal_ssl_crt
      sample_string_bytes = sample_string.encode("ascii")
      base64_bytes = base64.b64encode(sample_string_bytes)
      base64_string = base64_bytes.decode("ascii")
      crtObj_internal_data = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM,open_internal_ssl_crt)

      if request.env.ref('mobile_app_api.user_suqia_mobile').sudo().id == data.id:
         data_dict.update({'ssl_crt':base64_string,'ssl_expired': True if crtObj_internal_data.has_expired() else False})
      else:
         _token = request.env["api.access_token"]
         access_token = _token.find_one_or_create_token(user_id=data.id, create=True)
         # print(access_token,'access_token.lll.............oooooooooooooo')
         data_dict.update({'access_token':access_token,'expires_in':request.env.ref(expires_in).sudo().value})
      return data_dict
   
   @validate_crt
   # @validate_token
   @http.route('/api/sign_up/', type='json',auth="public",csrf=False,website=True)
   def users_create_authenticate(self, **kw):
      values = collections.OrderedDict(kw)
      sudo_users = (http.request.env["res.users"].with_context(create_user=True).sudo())
      full_name = values.get('name') +' '+values.get('middlename') + ' '+values.get('lastname')
      values['name']=full_name
      values['phone']=values.get("phone")
      values['email']=values.get("login")
      values.pop('middlename')
      values.pop('lastname')
      values.pop('confirm_email')
      try:
         values.pop('confirm_password')
         sudo_users.activate_signup(values,None)
         sudo_users.account_active(values.get("login"))
         return success_response('Registration Success. Please check your email to activate')        
      except SignupError as aee:
         return error_response(aee, aee,403)
      except Exception as e:
         error = "invalid_database"
         return error_response(e, error,403)

   @validate_crt
   # @validate_token
   @http.route('/api/get_pdf/', type='json',auth='public',csrf=False,website=True,web_content_api=True)
   def send_pdf_file(self, **kw):
      try:
         if kw.get('file_name') in ['GENERAL_APPLICATION_GUIDELINES','AWARD_TERMS','AT_GAG'] and kw.get('lang'):
            base_url = http.request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url_form = base_url+'/mobile_app_api/static/pdf/%s_%s.pdf'%(kw.get('file_name'),kw.get('lang'))
            print(url_form)
            result = {'url':url_form}
            return success_response(result)
         else:
            error = "Invalid File Name or Invalid Parameter"
            return error_response(error, error,403)
      except Exception as e:
         error = "Invalid File Name or Invalid Parameter"
         return error_response(e, error,403)
   
   @validate_crt
   # @validate_token
   @http.route('/api/reset_password/', type='json',auth="public",csrf=False,website=True,web_content_api=True)
   def user_reset_password(self, **kw):
      try:
         if kw.get('login'):
            sudo_users = (http.request.env["res.users"].sudo())
            sudo_users.reset_password(kw.get('login'))
            return success_response('An email has been sent with credentials to reset your password') 
      except Exception as e:
         error = 'Reset password: invalid username or email'
         return error_response(e, error,403)

   @validate_crt
   # @validate_token
   @http.route('/api/contact_us/', type='json',auth="public",csrf=False,website=False,web_content_api=True)
   def create_contact_us(self, **kw):
      print('----------------------------')
      try:        
         if kw.get('name') and kw.get('phone') and kw.get('email_from'):
            sudo_lead = (http.request.env["crm.lead"].sudo())
            # uid = request.uid
            if kw.get('uid'):
               kw.update({'user_id':int(kw.get('uid'))})
            else:
               kw.update({'user_id':4})
            kw.update({'type':'lead'})
            del kw['uid']
            sudo_lead.create(kw)
            return success_response('Respected person will contact soon.') 
         else:
            error = "Send the mandatory parameter"
            print(error)
            return error_response(error, error,403)
      except Exception as e:
         error = 'Invalid Parameter'
         print(e,'========-----0000000')

         return error_response(e, error,403)
   
   # @validate_crt
   @validate_token
   @http.route('/api/update_profile/', type='json',auth="public",csrf=False,website=True,web_content_api=True)
   def create_update_profile(self, **kw):
      try:         
         sudo_users = http.request.env["res.users"].sudo().browse(int(kw.get('uid')))
         if sudo_users:
            sudo_users.partner_id.email = kw.get('email') or ""
            sudo_users.partner_id.phone = kw.get('phone') or ""
            sudo_users.partner_id.name = kw.get('name') or ""
            sudo_users.partner_id.street = kw.get('street') or ""
            sudo_users.partner_id.company_name = kw.get('company_name') or ""
            sudo_users.partner_id.city = kw.get('city') or ""
            sudo_users.partner_id.zip = kw.get('zip') or ""
            sudo_users.partner_id.vat = kw.get('vat_number') or ""
            sudo_country = False
            sudo_state = False
            if kw.get('country'):
               sudo_country = http.request.env["res.country"].sudo().search([('id','=',int(kw.get('country')))],limit=1)
            sudo_users.partner_id.country_id = sudo_country.id if sudo_country else False
            if kw.get('state'):
               sudo_state = http.request.env["res.country.state"].sudo().search([('id','=',int(kw.get('state')))],limit=1)
            sudo_users.partner_id.state_id = sudo_state.id if sudo_state else False
         else:
            error = 'Invalid User ID'
            return error_response(e, error,403)            
         return success_response('Profile successfully Updated') 
      except Exception as e:
         error = 'Invalid Parameter or Error'
         return error_response(e, error,403)

   # @validate_crt
   @validate_token
   @http.route('/api/user_profile/', type='json',auth="public",csrf=True,website=True,web_content_api=True)
   def user_profile(self, **kw):
      try:
         sudo_users = http.request.env["res.users"].sudo().browse(int(kw.get('uid')))
         sudo_country = http.request.env["res.country"].with_context(lang=kw.get('lang')).sudo().search_read([])
         sudo_state = http.request.env["res.country.state"].with_context(lang=kw.get('lang')).sudo().search_read([])
         countries = []
         states = []
         for cou in sudo_country:
            del cou['image']
            countries.append(cou)
         val = {}

         val['countries'] = countries
         val['states'] = sudo_state
         user_details = {
             "email":sudo_users.partner_id.email or "",
                "phone":sudo_users.partner_id.phone or "",
                "name":sudo_users.partner_id.name or "",
                "street":sudo_users.partner_id.street or "",
                "company_name":sudo_users.partner_id.company_name or "",
                "city":sudo_users.partner_id.city or "",
                "zip":sudo_users.partner_id.zip or "",
                "country":str(sudo_users.partner_id.country_id.id) if sudo_users.partner_id.country_id else "",
                "state":str(sudo_users.partner_id.state_id.id) if sudo_users.partner_id.state_id else "",
                "vat_number":sudo_users.partner_id.vat or ""

      }
         val['user_details'] = user_details
         return success_response(val) 
      except Exception as e:
         error = 'Invalid Parameter or Error'
         return error_response(e, error,403)

   # @http.route('/api/user_profile/', type='json',auth="public",csrf=False,website=True,web_content_api=True)
   # def user_profile(self, **kw):
   #    try:
   #       sudo_country = http.request.env["res.country"].sudo().search_read([])
   #       sudo_state = http.request.env["res.country.state"].sudo().search_read([])
   #       countries = []
   #       states = []
   #       for cou in sudo_country:
   #          del cou['image']
   #          countries.append(cou)
   #       val = {}
   #       val['countries'] = countries
   #       val['states'] = sudo_state
   #       return success_response(val) 
   #    except Exception as e:
   #       error = 'Invalid Parameter or Error'
   #       return error_response(e, error,403)