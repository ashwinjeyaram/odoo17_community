# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    warranty_type = fields.Selection([
        ('none', 'No Warranty'),
        ('limited', 'Limited Warranty'),
        ('full', 'Full Warranty')
    ], default='none', string='Warranty Type')

    warranty_duration = fields.Integer(string='Warranty Duration (Days)')

    motor_warranty_type = fields.Selection([
        ('none', 'No Motor Warranty'),
        ('limited', 'Limited Motor Warranty'),
        ('full', 'Full Motor Warranty')
    ], default='none', string='Motor Warranty Type')

    motor_warranty_duration = fields.Integer(string='Motor Warranty Duration (Days)')