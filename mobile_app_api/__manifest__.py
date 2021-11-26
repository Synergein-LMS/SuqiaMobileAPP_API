# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Mobile App API',
    'version': '1.0',
    'category': 'Mobile',
    'sequence': 5,
    'summary': '',
    'description': "",
    'website': '',
    'depends': [
        'base_setup',
        'base',
       
    ],
    'data': [
       'data/ir_config_param.xml',
       'data/user_data.xml',
       'views/res_users.xml',
       'security/ir.model.access.csv',
    ],
    'demo': [

    ],
    
    'installable': True,
    'application': True,
    'auto_install': False
}
