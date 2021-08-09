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
class MobileAPI(http.Controller):

   @http.route('/api/user_auth', type='json', auth="none")
   def users_authenticate(self, db, login, password):
      try:
         rec_id = request.session.authenticate(db, login, password)
         data = request.env['res.users'].browse(rec_id)
         data_dict = {'odoo_id':data.id,'login':data.login,'name':data.name,'phone':data.phone,'email':data.email}
      except AccessError as aee:
         msg = "Error: %s" % aee.name
         return error_response(aee, msg,200)
      except AccessDenied as ade:
         msg = "Login or password invalid"
         return error_response(ade, msg,200)
      except Exception as e:
         error = "invalid_database"
         return error_response(e, error,403)
      return success_response(data_dict)
   
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
         return success_response('Registration Success')        
      except SignupError as aee:
         return error_response(aee, aee,200)
      except Exception as e:
         error = "invalid_database"
         return error_response(e, error,403)

   @http.route('/api/get_pdf/', type='json',auth="public",csrf=False,website=True,web_content_api=True)
   def send_pdf_file(self, **kw):
      try:
         if kw.get('file_name') in ['GENERAL_APPLICATION_GUIDELINES','AWARD_TERMS']:
            base_url = http.request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url_form = base_url+'/mobile_app_api/static/pdf/%s.pdf'%(kw.get('file_name'))
            result = {'url':url_form}
            return success_response(result)
         else:
            error = "Invalid File Name or Invalid Parameter"
            return error_response(error, error,403)
      except Exception as e:
         error = "Invalid File Name or Invalid Parameter"
         return error_response(e, error,403)

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

   @http.route('/api/contact_us/', type='json',auth="public",csrf=False,website=True,web_content_api=True)
   def create_contact_us(self, **kw):
      try:         
         if kw.get('name') and kw.get('phone') and kw.get('email_from'):
            sudo_lead = (http.request.env["crm.lead"].sudo())
            kw.update({'type':'lead'})
            sudo_lead.create(kw)
            return success_response('Lead created successfully')
         else:
            error = "Send the mandatory parameter"
            return error_response(error, error,403)
      except Exception as e:
         error = 'Invalid Parameter'
         return error_response(e, error,403)

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

   @http.route('/api/user_profile/', type='json',auth="public",csrf=False,website=True,web_content_api=True)
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
