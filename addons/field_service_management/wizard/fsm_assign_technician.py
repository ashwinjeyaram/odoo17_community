# -*- coding: utf-8 -*-
from odoo import models, fields, api

class FSMAssignTechnician(models.TransientModel):
    _name = 'fsm.assign.technician'
    _description = 'Assign Technician Wizard'
    
    call_ids = fields.Many2many('fsm.call', string='Service Calls')
    technician_id = fields.Many2one('fsm.technician', string='Technician', required=True)
    
    def action_assign(self):
        """Assign selected technician to calls"""
        for call in self.call_ids:
            call.technician_id = self.technician_id
            call.action_assign()
        return {'type': 'ir.actions.act_window_close'}