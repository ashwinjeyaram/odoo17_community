# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class FSMCallAttachmentWizard(models.TransientModel):
    _name = 'fsm.call.attachment.wizard'
    _description = 'FSM Call Attachment Wizard'
    
    call_id = fields.Many2one('fsm.call', string='Service Call', required=True)
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')
    
    @api.model
    def default_get(self, fields):
        res = super(FSMCallAttachmentWizard, self).default_get(fields)
        if self._context.get('active_id'):
            res['call_id'] = self._context['active_id']
        return res
    
    def action_add_attachments(self):
        """Add attachments to the service call"""
        self.ensure_one()
        if not self.attachment_ids:
            raise ValidationError("At least one attachment is required.")
        
        # Add attachments to the call
        attachments_to_link = []
        for attachment in self.attachment_ids:
            attachments_to_link.append((4, attachment.id))
        
        self.call_id.write({
            'attachment_ids': attachments_to_link
        })
        
        return {'type': 'ir.actions.act_window_close'}