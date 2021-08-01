# -*- coding: utf-8 -*-

{
    'name': 'DubaiPay Payment Acquirer',
    'category': 'Accounting/Payment',
    'summary': 'DSG’s ePayment Gateway',
    'version': '1.0',
    'description': """ DSG’s ePayment Gateway """,
    'website': "http://www.sandv.biz",
    'author': 'S&V',
    'depends': ['payment', 'website'],
    'data': [
        'views/payment_dubaipay_templates.xml',
        'data/payment_acquirer_data.xml',
        'data/payment_dubaipay_cron.xml',
        'security/payment_security.xml',
        'views/templates.xml',
        'views/payment_views.xml',
    ],
    'installable': True,
}
