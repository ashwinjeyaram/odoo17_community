# -*- coding: utf-8 -*-
from odoo import models, fields, api


class FSMDealer(models.Model):
    _name = 'fsm.dealer'
    _description = 'Dealer Master'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'create_date desc'
    
    name = fields.Char(string='Dealer Name', required=True, tracking=True, default='New')
    city = fields.Char(string='City', required=True)
    phone_number = fields.Char(string='Phone Number')
    technician_ids = fields.One2many('fsm.technician', 'dealer_id', string='Technicians')
    
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('fsm.dealer') or 'New'
        return super(FSMDealer, self).create(vals)