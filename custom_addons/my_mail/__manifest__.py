# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'My Mail',
    'version': '0.1',
    'category': 'Tools',
    'sequence': 15,
    'summary': 'Manage mail and communication with opt-in and opt-out features',
    'website': 'https://www.odoo.com/app/mail',
    'depends': [
        'base_setup',
        'mail',
        'calendar',
        'contacts',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/my_mail_menu.xml',
        'views/my_mail_message_views.xml',
        'views/mail_template_subscription_views.xml',
        'views/mail_template_bulk_actions.xml',
        'views/res_users_subscription_views.xml',
        'views/bulk_subscription_wizard_views.xml',
        'views/subscription_audit_log_views.xml',
    ],
    'demo': [
        
    ],
    'installable': True,
    'application': True,
    'assets': {
    },
    'author': 'Sascha Wernegger',
    'license': 'LGPL-3',
    'post_init_hook': 'hooks.post_init_hook',
}