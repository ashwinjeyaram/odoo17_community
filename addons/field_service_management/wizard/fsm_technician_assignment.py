# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class FSMTechnicianAssignmentWizard(models.TransientModel):
    _name = 'fsm.technician.assignment.wizard'
    _description = 'Technician Assignment Wizard'
    
    call_id = fields.Many2one('fsm.call', string='Service Call', required=True)
    dealer_id = fields.Many2one('fsm.dealer', string='Dealer', required=True)
    dealer_ids = fields.Many2many('fsm.dealer', string='Available Dealers')
    technician_id = fields.Many2one('fsm.technician', string='Technician')
    technician_ids = fields.Many2many('fsm.technician', string='Available Technicians')
    
    @api.model
    def default_get(self, fields):
        res = super(FSMTechnicianAssignmentWizard, self).default_get(fields)
        call_id = self._context.get('active_id') or self._context.get('default_call_id')
        if call_id:
            call = self.env['fsm.call'].browse(call_id)
            res['call_id'] = call.id

            # Get available dealers
            dealers = self.env['fsm.dealer'].search([('active', '=', True)])
            res['dealer_ids'] = [(6, 0, dealers.ids)]

        return res
    

    @api.onchange('dealer_id')
    def _onchange_dealer_id(self):
        if self.dealer_id:
            # Get all active technicians for selected dealer
            technicians = self.env['fsm.technician'].search([
                ('dealer_id', '=', self.dealer_id.id),
                ('active', '=', True),
                ('state', 'in', ['available', 'busy'])
            ])

            self.technician_ids = [(6, 0, technicians.ids)]

            # Auto-select technician with least active calls
            if technicians:
                technician_data = []
                for tech in technicians:
                    active_calls = tech.call_ids.filtered(
                        lambda c: c.state not in ['closed', 'cancelled']
                    )
                    technician_data.append({
                        'technician': tech,
                        'active_calls': len(active_calls)
                    })

                # Sort by active calls count (ascending) - least busy first
                technician_data.sort(key=lambda x: x['active_calls'])
                self.technician_id = technician_data[0]['technician'].id
            else:
                self.technician_id = False
        else:
            # Reset technician selection when dealer is cleared
            self.technician_ids = [(5, 0, 0)]
            self.technician_id = False
    
    def action_assign_technician(self):
        if not self.technician_id:
            raise UserError("Please select a technician to assign.")
            
        if self.technician_id and self.call_id:
            # Assign technician to the call
            self.call_id.write({
                'technician_id': self.technician_id.id,
                'state': 'assigned',
                'assigned_date': fields.Datetime.now()
            })
            
            # Send notification to technician
            self.call_id.message_post(
                body=f'Call assigned to {self.technician_id.name}',
                partner_ids=self.technician_id.user_id.partner_id.ids
            )
            
            # Create activity for technician
            self.call_id.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=f'Service Call {self.call_id.name}',
                user_id=self.technician_id.user_id.id
            )
            
            # Create notification transaction
            self.env['fsm.notification.transaction'].create({
                'call_id': self.call_id.id,
                'technician_id': self.technician_id.id,
                'service_partner_id': self.technician_id.service_partner_id.id if self.technician_id.service_partner_id else False,
                'notification_type': 'call_assigned',
                'old_status': 'confirmed' if self.call_id.state == 'assigned' else self.call_id.state,
                'new_status': 'assigned',
                'description': f'Service call {self.call_id.name} assigned to {self.technician_id.name}'
            })
            
        return {'type': 'ir.actions.act_window_close'}