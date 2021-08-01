# -*- coding: utf-8 -*-

import logging
import subprocess
import json

from  datetime import datetime
from dateutil import relativedelta
import pprint

from odoo import api, fields, models, _
from odoo.modules.module import get_resource_path 
from odoo.addons.payment.models.payment_acquirer import ValidationError

_logger = logging.getLogger(__name__)


class PaymentAcquirerDubaiPay(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('dubaipay', 'DubaiPay')])
    suqia_spcode = fields.Char(
        string='SpCode',
        required_if_provider='dubaipay',
        groups='base.group_user'
    )
    suqia_servcode = fields.Char(
        string='ServCode',
        required_if_provider='dubaipay',
        groups='base.group_user'
    )


class TxDubaiPay(models.Model):
    _inherit = 'payment.transaction'

    dubaipay_status_code = fields.Char(string='Dupaipay Staus Code', readonly=True)
    dubaipay_txnTimestamp = fields.Char(string='Dupaipay txnTimestamp', readonly=True)
    dubaipay_payment_method = fields.Char(string='Dupaipay Payment Method', readonly=True)
    dubaipay_response_token = fields.Text(string='Dupaipay Response Token', readonly=True)
    payment_from = fields.Selection([('website','Website'),('mobile','Mobile')],string="Payment From")

    @api.model
    def _dubaipay_form_get_tx_from_data(self, data):
        reference, txn_id = data.get('sptrn'), data.get('degTrn')
        if not reference or not txn_id:
            error_msg = _('DubaiPay: received data with missing reference (%s) or txn_id (%s)') % (reference, txn_id)
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        # find tx -> @TDENOTE use txn_id ?
        txs = self.env['payment.transaction'].search([('reference', '=', reference)])
        if not txs or len(txs) > 1:
            error_msg = 'Dubai: received data for reference %s' % (reference)
            if not txs:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.info(error_msg)
            raise ValidationError(error_msg)
        return txs[0]  


    def _dubaipay_form_get_invalid_parameters(self, data):
        invalid_parameters = []
        # reference at acquirer: sptrn
        if data.get('sptrn') and data.get('sptrn') != self.reference:
            invalid_parameters.append(('Reference', data.get('sptrn'), self.reference))
        return invalid_parameters 
        
    def _dubaipay_form_validate(self, data):
        status = data['message']['code']
        if status == 0:
            self.write({
                'acquirer_reference': data.get('degTrn'),
                'dubaipay_payment_method': data.get('paymentMethod'),
                'dubaipay_status_code': status,
                'dubaipay_txnTimestamp': data.get('txnTimestamp'),
                'dubaipay_response_token': data.get('response_token')
            })
            self._set_transaction_done()
            return True
        else:
            error = data['message']['text']
            _logger.info(error)
            self.write({
                'state_message': error,
                'acquirer_reference': data.get('degTrn'),
                'dubaipay_payment_method': data.get('paymentMethod'),
                'dubaipay_status_code': status,
                'dubaipay_txnTimestamp': data.get('txnTimestamp'),
                'dubaipay_response_token': data.get('response_token')
            })
            self._set_transaction_cancel()
            return False

    # Cron Function  
    def _post_dubaipay_process_after_done(self):
        payment_id = self
        request_param = dict()
        acquirer_id = self.env['payment.acquirer'].sudo().search([('provider', '=', 'dubaipay')])
        if payment_id.dubaipay_response_token:
            request_param.update({
                "spCode" : acquirer_id.suqia_spcode,
                "servCode" : acquirer_id.suqia_servcode,
                "responseToken" : payment_id.dubaipay_response_token,
            })
            payment_status_path = get_resource_path('payment_dubaipay', 'php/epay_dubai/payment_status.php')
            proc = subprocess.Popen(["php", "-f", payment_status_path, json.dumps(request_param)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            script_response = proc.stdout.read()
            byte_to_str = script_response.decode("UTF-8")
            response = json.loads(byte_to_str)
            _logger.info('Beginning Dubaipay form_feedback with post data %s', pprint.pformat(response))
            if response:
                self.env['payment.transaction'].sudo().form_feedback(response, 'dubaipay')
            if response['message']['code'] == 0:
                request_param.update({
                    "spCode" : acquirer_id.suqia_spcode,
                    "servCode" : acquirer_id.suqia_servcode,
                    "sptrn" : response['sptrn'],
                    "code" : response['message']['code'],
                    "text" : response['message']['text'],
                })
                delivery_status_path = get_resource_path('payment_dubaipay', 'php/epay_dubai/confirm_del_status.php')
                delivery_status = subprocess.Popen(["php", "-f", delivery_status_path, json.dumps(request_param)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                delivery_response = delivery_status.stdout.read()
                del_byte_to_str = delivery_response.decode("UTF-8")
                del_response = json.loads(del_byte_to_str)
                _logger.info('Dubaipay Delivery status with post data %s', pprint.pformat(del_response))
        return True        

    # Cron Function  
    def _cron_dubaipay_post_process_after_done(self):          
        if not self:
            retry_limit_date = datetime.now() - relativedelta.relativedelta(days=1)
            self = self.search([
                    ('date', '>=', retry_limit_date), ('state', '=', 'draft')
                ])
        for tx in self:
            try:
                tx._post_dubaipay_process_after_done()
                self.env.cr.commit()
            except Exception as e:
                _logger.exception("Transaction post processing failed")
                self.env.cr.rollback()
