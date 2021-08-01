# -*- coding: utf-8 -*-

import subprocess
import uuid
import logging
import json
import werkzeug

import pprint
from urllib.parse import urljoin
from werkzeug import url_encode

from odoo.http import request
from odoo.exceptions import ValidationError
from odoo.addons.payment.controllers.portal import PaymentProcessing
from odoo.modules.module import get_resource_path   
from odoo import fields, http, SUPERUSER_ID, tools, _

_logger = logging.getLogger(__name__)

def error_response(error, msg,code):
   print(error, msg)
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

class WebsiteDonation(http.Controller):

    @http.route('/donation', type='http', auth="public", website=True)
    def donation(self, **kw):
        return request.render('payment_dubaipay.WebsiteDonation')

    @http.route('/payment/success', type='http', auth="public", website=True)
    def payment_success(self, **kw):
        return request.render('payment_dubaipay.PaymentSuccess')
    
    @http.route('/payment/failed', type='http', auth="public", website=True)
    def payment_failed(self, **kw):
        return request.render('payment_dubaipay.PaymentFailed')        

    @http.route(['/payment/dubaipay/return'], type='http', auth='public', csrf=False, website=True, secure=False, samesite=None)
    def dubaipay_return(self, **post):
        acquirer = request.env['payment.acquirer'].sudo().search([('provider', '=', 'dubaipay')])
        redirect_url = None
        request_param = dict()
        request_param.update({
            "spCode" : acquirer.suqia_spcode,
            "servCode" : acquirer.suqia_servcode,
            "responseToken" : post.get('TOKEN'),
        })
        payment_status_path = get_resource_path('payment_dubaipay', 'php/epay_dubai/payment_status.php')
        proc = subprocess.Popen(["php", "-f", payment_status_path, json.dumps(request_param)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        script_response = proc.stdout.read()
        byte_to_str = script_response.decode("UTF-8")
        try: 
            response = json.loads(byte_to_str)
            response.update({
                "response_token" : post.get('TOKEN'),
            })
            _logger.info('Beginning Dubaipay form_feedback with post data %s', pprint.pformat(response))
            request.env['payment.transaction'].sudo().form_feedback(response, 'dubaipay')
            if response['message']['code'] == 0:
                request_param.update({
                    "spCode" : acquirer.suqia_spcode,
                    "servCode" : acquirer.suqia_servcode,
                    "sptrn" : response['sptrn'],
                    "code" : response['message']['code'],
                    "text" : response['message']['text'],
                })
                delivery_status_path = get_resource_path('payment_dubaipay', 'php/epay_dubai/confirm_del_status.php')
                delivery_status = subprocess.Popen(["php", "-f", delivery_status_path, json.dumps(request_param)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                delivery_response = delivery_status.stdout.read()
                del_byte_to_str = delivery_response.decode("UTF-8")
                try: 
                    del_response = json.loads(del_byte_to_str)
                    _logger.info('Dubaipay Delivery status with post data %s', pprint.pformat(del_response))
                    if del_response.get("valid"):
                        redirect_url = '/payment/success'
                except json.decoder.JSONDecodeError:
                    redirect_url = '/payment/failed' 
                except Exception:
                    pass
            else:
                redirect_url = '/payment/failed' 
        except json.decoder.JSONDecodeError:
            redirect_url = '/payment/failed' 
        except Exception:
                pass
        return werkzeug.utils.redirect(redirect_url)       

    # def _get_dubaipay_urls(self, environment):
    #     """ Wsdl dubaipay_ URLS """
    #     if environment == 'prod':
    #         return 'https://epayment.dubai.ae/ePayHub/WSDL/PaymentAPIService.wsdl'
    #     return 'https://epayment.qa.dubai.ae/ePayHub/WSDL/PaymentAPIService.wsdl'


    @http.route(['/shop/donation/transaction'], type='json', auth="public")
    def payment_transaction(self, **post):
        """ Json method that creates a payment.transaction, used to create a
        transaction when the user clicks on 'pay now' button. After having
        created the transaction, the event continues and the user is redirected
        to the acquirer website.

        :param int acquirer_id: id of a payment.acquirer record. If not set the
                                user is redirected to the checkout page
        """
        # Ensure a payment acquirer is selected
        result = dict()
        url = None
        acquirer_id = request.env['payment.acquirer'].sudo().search([('provider', '=', 'dubaipay')])
        if acquirer_id.state == 'disabled': 
            result.update({
                'message': (_('Payment gateway is disabled!')),
            })
            return result
        amount = float(post.get('amount'))
        if post.get('uid'):
            user_id = int(post.get('uid'))
        else:
            user_id = request.env.user.id
        if user_id:
            user = request.env['res.users'].sudo().browse(user_id)
            partner_id = user.partner_id
        if request.session.uid or post.get('uid'):
            is_authenticated = 'true'        
        else:
            is_authenticated = 'false'
        currency_id = request.env.ref('base.AED').sudo()
        partner_type = 'Individual' if partner_id.company_type == 'person' else 'Corporate'
        partner_company = partner_id.name if partner_id.company_type == 'company' else ' '
        sptrn = str(uuid.uuid4())[0:18]
        dubaipay_tx_values = dict()
        dubaipay_tx_values.update({
            # 'transactionInfo':
                "spCode" : acquirer_id.suqia_spcode,
                "servCode" : acquirer_id.suqia_servcode,
                'sptrn': sptrn,
                'currency': currency_id.name,
                'amount': amount,
                'description': 'Suqia Donation',
                'type': 'sale',
                'versionCode': 2.1,
                'paymentChannel': 100,
            # 'userInfo':
                'isAuthenticated': is_authenticated,
                'userId': partner_id.id,
                'userName': partner_id.name or ' ',
                'fullNameEn': partner_id.name or ' ',
                'mobileNo': partner_id.phone or partner_id.mobile,
                'email': partner_id.email,
            # 'serviceInfo':
                'serviceNameEn': 'Suqia Donation',
                'serviceId': acquirer_id.id,
            # beneficiaryInfo
                'accountId': partner_id.id,
                'partner_type': partner_type,
            # companyInfo
                'companyNameEn': partner_company or ' ',
        })
        index_path = get_resource_path('payment_dubaipay', 'php/epay_dubai/index.php')
        proc = subprocess.Popen(["php", "-f", index_path, json.dumps(dubaipay_tx_values)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        script_response = proc.stdout.read()
        byte_to_str = script_response.decode("UTF-8")
        try: 
            response = json.loads(byte_to_str)
            if response.get("valid"):
                url = response.get("uri")
        except json.decoder.JSONDecodeError:
            result.update({
                'message': (_(byte_to_str)),
            })
            return result
        except Exception:
                pass

        # Check a journal is set on acquirer.
        if not acquirer_id.journal_id:
            raise ValidationError(_('A journal must be specified of the acquirer %s.' % acquirer_id.name))
        account_payment_vals = {
            'amount': amount,
            'payment_type': 'inbound' if amount > 0 else 'outbound',
            'currency_id': currency_id.id,
            'partner_id': partner_id.id,
            'partner_type': 'customer',
            'journal_id': acquirer_id.journal_id.id,
            'company_id': acquirer_id.company_id.id,
            'payment_method_id': request.env.ref('payment.account_payment_method_electronic_in').id,
            'communication': sptrn,
        }  
        payment = request.env['account.payment'].sudo().create(account_payment_vals)
        payment_from = ''
        if post.get('payment_from'):
            payment_from = post.get('payment_from')
        else:
            payment_from = 'website'

        vals = {
            'acquirer_id': acquirer_id.id,
            'currency_id': currency_id.id,
            'partner_id': partner_id.id,
            'reference': sptrn,
            'payment_id': payment.id,
            'amount': amount,
            'payment_from':payment_from
        }
        transaction = request.env['payment.transaction'].sudo().create(vals)
        payment.sudo().write({
            'payment_transaction_id': transaction.id,
        })
        # store the new transaction into the transaction list and if there's an old one, we remove it
        # until the day the ecommerce supports multiple orders at the same time
        last_tx_id = request.session.get('__website_donation_last_tx_id')
        last_tx = request.env['payment.transaction'].browse(last_tx_id).sudo().exists()
        if last_tx:
            PaymentProcessing.remove_payment_transaction(last_tx)
        PaymentProcessing.add_payment_transaction(transaction)
        request.session['__website_donation_last_tx_id'] = transaction.id
        return url
    
    @http.route(['/payment/dubaipay/api_return'], type='json', auth='public')
    def dubaipay_return_mobile(self, **post):
        acquirer = request.env['payment.acquirer'].sudo().search([('provider', '=', 'dubaipay')])
        redirect_url = None
        request_param = dict()
        request_param.update({
            "spCode" : acquirer.suqia_spcode,
            "servCode" : acquirer.suqia_servcode,
            "responseToken" : post.get('TOKEN'),
        })
        payment_status_path = get_resource_path('payment_dubaipay', 'php/epay_dubai/payment_status.php')
        proc = subprocess.Popen(["php", "-f", payment_status_path, json.dumps(request_param)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        script_response = proc.stdout.read()
        byte_to_str = script_response.decode("UTF-8")
        try: 
            response = json.loads(byte_to_str)
            response.update({
                "response_token" : post.get('TOKEN'),
            })
            _logger.info('Beginning Dubaipay form_feedback with post data %s', pprint.pformat(response))
            request.env['payment.transaction'].sudo().form_feedback(response, 'dubaipay')
            if response['message']['code'] == 0:
                request_param.update({
                    "spCode" : acquirer.suqia_spcode,
                    "servCode" : acquirer.suqia_servcode,
                    "sptrn" : response['sptrn'],
                    "code" : response['message']['code'],
                    "text" : response['message']['text'],
                })
                delivery_status_path = get_resource_path('payment_dubaipay', 'php/epay_dubai/confirm_del_status.php')
                delivery_status = subprocess.Popen(["php", "-f", delivery_status_path, json.dumps(request_param)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                delivery_response = delivery_status.stdout.read()
                del_byte_to_str = delivery_response.decode("UTF-8")
                try: 
                    del_response = json.loads(del_byte_to_str)
                    _logger.info('Dubaipay Delivery status with post data %s', pprint.pformat(del_response))
                    if del_response.get("valid"):
                        return success_response('Payment Successfully')
                except json.decoder.JSONDecodeError as e:
                    error = "Payment Failed"
                    return  error_response(e, error,406)
                except Exception as a:
                    error = "Error"
                    return error_response(a, error,403)
            else:
                error = "Payment Failed"
                return error_response(error, error,406)
        except json.decoder.JSONDecodeError as e:
            error = "Payment Failed"
            return error_response(e, error,406)
        except Exception as a:
            error = "Error"
            return error_response(a, error,403)