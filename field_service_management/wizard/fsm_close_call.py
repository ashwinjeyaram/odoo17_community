# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class FSMCloseCallWizard(models.TransientModel):
    _name = 'fsm.close.call.wizard'
    _description = 'Close Service Call with OTP Verification'

    call_id = fields.Many2one('fsm.call', string='Service Call', required=True)
    otp_code = fields.Char(string='Enter OTP', size=5, required=True)
    
    @api.model
    def default_get(self, fields):
        res = super(FSMCloseCallWizard, self).default_get(fields)
        if self._context.get('active_id'):
            res['call_id'] = self._context['active_id']
        return res
    
    def action_verify_and_close(self):
        """Verify OTP and close the service call"""
        self.ensure_one()
        
        # Find the latest OTP notification for this call
        notification = self.env['fsm.notification.transaction'].search([
            ('call_id', '=', self.call_id.id),
            ('notification_type', '=', 'otp_generated')
        ], order='create_date desc', limit=1)
        
        if not notification:
            raise ValidationError("No OTP found for this service call. Please resolve the call first to generate an OTP.")
        
        if not notification.otp_code:
            raise ValidationError("OTP has not been generated for this service call.")
        
        # Verify OTP
        if notification.verify_otp(self.otp_code):
            # Update notification to show it's been verified
            notification.write({
                'notification_type': 'otp_verified',
                'description': f'OTP verified for closing call {self.call_id.name}'
            })
            
            # Close the call
            self.call_id.action_close()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': 'Service call closed successfully!',
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            raise ValidationError("Invalid OTP. Please try again.")