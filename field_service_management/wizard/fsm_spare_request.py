# -*- coding: utf-8 -*-
from odoo import models, fields, api

class FSMSpareRequestWizard(models.TransientModel):
    _name = 'fsm.spare.request.wizard'
    _description = 'Spare Request Wizard'
    
    call_id = fields.Many2one('fsm.call', string='Service Call', required=True)
    spare_line_ids = fields.One2many('fsm.spare.request.wizard.line', 'wizard_id', string='Spare Parts')
    
    def action_create_request(self):
        """Create spare request"""
        request = self.env['fsm.spare.request'].create({
            'call_id': self.call_id.id,
            'spare_line_ids': [(0, 0, {
                'spare_id': line.spare_id.id,
                'quantity': line.quantity,
            }) for line in self.spare_line_ids]
        })
        request.action_request()
        return {'type': 'ir.actions.act_window_close'}

class FSMSpareRequestWizardLine(models.TransientModel):
    _name = 'fsm.spare.request.wizard.line'
    _description = 'Spare Request Wizard Line'
    
    wizard_id = fields.Many2one('fsm.spare.request.wizard', required=True)
    spare_id = fields.Many2one('fsm.spare', string='Spare Part', required=True)
    quantity = fields.Float(string='Quantity', default=1.0)