# -*- coding: utf-8 -*-
from odoo import models, fields, api


class FSMFault(models.Model):
    _name = 'fsm.fault'
    _description = 'Fault Master'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'create_date desc'
    
    name = fields.Char(string='Fault Name', required=True, tracking=True)
    code = fields.Char(string='Fault Code', readonly=True, copy=False, default='New')
    description = fields.Text(string='Description')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    
    @api.model
    def create(self, vals):
        if vals.get('code', 'New') == 'New':
            vals['code'] = self.env['ir.sequence'].next_by_code('fsm.fault') or 'New'
        return super(FSMFault, self).create(vals)