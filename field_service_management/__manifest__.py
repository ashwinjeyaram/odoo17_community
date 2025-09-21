# -*- coding: utf-8 -*-
{
    'name': 'Field Service Management',
    'version': '17.0.1.0.1',
    'category': 'Services',
    'summary': 'Complete Field Service Management Module for Odoo 17',
    'description': """
        Field Service Management Module
        ===============================
        
        This module provides comprehensive field service management functionality including:
        - Service call management with multi-stage workflow
        - Technician assignment based on pincode/area
        - Inventory and spare parts management
        - Customer feedback with OTP verification
        - Expense management for technicians
        - Service partner claims processing
        - Real-time tracking and reporting
        - Integration with core Odoo modules
        
        Features:
        ---------
        * Service Calls: Create, assign, track, and close service calls
        * Technician Management: Manage technicians with area assignments
        * Inventory Tracking: Track spare parts requests and returns
        * Customer Portal: Allow customers to track service status
        * Analytics: Comprehensive dashboards and reports
        * Mobile Support: Optimized for field technician use
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'base',
        'mail',
        'contacts',
        'product',
        'stock',
        'sale',
        'purchase',
        'portal',
        'web',
    ],
    'data': [
        # Security
        'security/fsm_security.xml',
        'security/fsm_notification_security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/sequence_data.xml',
        # 'data/mail_template_data.xml',
        # 'data/default_data.xml',
        
        # Views
        'views/fsm_call_views.xml',
        'views/fsm_technician_views.xml',
        'views/fsm_service_partner_views.xml',
        'views/fsm_spare_views.xml',
        'views/fsm_inventory_views.xml',
        'views/fsm_feedback_views.xml',
        'views/fsm_expense_views.xml',
        'views/fsm_claim_views.xml',
        'views/fsm_dashboard_views.xml',
        'views/fsm_service_dashboard_views.xml',
        'views/fsm_inventory_dashboard_views.xml',
        'views/fsm_location_views.xml',
        'views/fsm_dealer_views.xml',
        'views/fsm_fault_views.xml',
        'views/fsm_notification_views.xml',
        'views/product_template_views.xml',
        'views/res_partner_views.xml',
        'views/menu.xml',
        
        # Wizards
        'wizard/fsm_assign_technician_views.xml',
        'wizard/fsm_spare_request_views.xml',
        'wizard/fsm_close_call_views.xml',
        'wizard/fsm_technician_assignment_views.xml',
        'wizard/fsm_call_attachment_views.xml',
        
        # Reports
        'report/fsm_service_report_views.xml',
        'report/fsm_service_report_template.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend': [
            'field_service_management/static/src/css/fsm_service_dashboard.css',
            'field_service_management/static/src/js/fsm_service_dashboard.js',
            'field_service_management/static/src/xml/fsm_service_dashboard_templates.xml',
            'field_service_management/static/src/css/fsm_inventory_dashboard.css',
            'field_service_management/static/src/js/fsm_inventory_dashboard.js',
            'field_service_management/static/src/xml/fsm_inventory_dashboard_templates.xml',
        ],
    },
    'external_dependencies': {
        'python': [],
    },
}