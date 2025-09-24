# -*- coding: utf-8 -*-
#################################################################################
# Author      : Terabits Technolab (<www.terabits.xyz>)
# Copyright(c): 2021-23
# All Rights Reserved.
#
# This module is copyright property of the author mentioned above.
# You can't redistribute/reshare/recreate it for any purpose.
#
#################################################################################

{
    'name': 'Simplify Access Management',
    'version': '17.0.4.3.1',
    'sequence': 5,
    'author': 'Terabits Technolab',
    'license': 'OPL-1',
    'category': 'Tools',
    'website': 'https://www.terabits.xyz/r/SNS',
    'summary': """
       
        Delight POS theme | Advance POS Theme | point of sale theme | Theme POS | Odoo POS theme
        Point of sale split bill | Point of sale split order | POS split bill | POS split invoices
	
    """,
    "images": ["static/description/banner.gif"],
    "price": "370.99",
    "currency": "USD",
    'data': [
        'security/ir.model.access.csv',
        'security/res_groups.xml',
        'data/view_data.xml',
        'views/access_management_view.xml',
        'views/res_users_view.xml',
        'views/store_model_nodes_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            '/simplify_access_management/static/src/js/action_menus.js',
            '/simplify_access_management/static/src/js/hide_chatter.js',
            '/simplify_access_management/static/src/js/cog_menu.js',
            '/simplify_access_management/static/src/js/form_controller.js',
            '/simplify_access_management/static/src/js/pivot_grp_menu.js',
            '/simplify_access_management/static/src/js/model_field_selector.js',
        ],

    },
    'depends': ['web', 'advanced_web_domain_widget'],
    'post_init_hook': 'post_install_action_dup_hook',
    'application': True,
    'installable': True,
    'auto_install': False,
    'live_test_url': 'https://www.terabits.xyz/request_demo?source=index&version=17&app=simplify_access_management',
}
