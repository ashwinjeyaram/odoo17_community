# -*- coding: utf-8 -*-
from odoo import models, fields, api
import random
import string


class FSMNotificationTransaction(models.Model):
    _name = 'fsm.notification.transaction'
    _description = 'Field Service Notification Transaction'
    _order = 'create_date desc'
    _rec_name = 'display_name'

    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)
    
    # Related Records
    call_id = fields.Many2one('fsm.call', string='Service Call')
    spare_request_id = fields.Many2one('fsm.spare.request', string='Spare Request')
    technician_id = fields.Many2one('fsm.technician', string='Technician')
    service_partner_id = fields.Many2one('fsm.service.partner', string='Service Partner')
    
    # Notification Details
    notification_type = fields.Selection([
        ('call_created', 'Call Created'),
        ('call_assigned', 'Call Assigned'),
        ('call_started', 'Call Started'),
        ('call_resolved', 'Call Resolved'),
        ('call_closed', 'Call Closed'),
        ('call_cancelled', 'Call Cancelled'),
        ('spare_requested', 'Spare Requested'),
        ('spare_approved', 'Spare Approved'),
        ('spare_issued', 'Spare Issued'),
        ('spare_received', 'Spare Received'),
        ('status_changed', 'Status Changed'),
        ('technician_assigned', 'Technician Assigned'),
        ('otp_generated', 'OTP Generated'),
        ('otp_verified', 'OTP Verified'),
    ], string='Notification Type', required=True)
    
    old_status = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('pending_spares', 'Pending Spares'),
        ('pending_customer', 'Pending Customer'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
        ('requested', 'Requested'),
        ('approved', 'Approved'),
        ('issued', 'Issued'),
        ('received', 'Received')
    ], string='Old Status')
    
    new_status = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('pending_spares', 'Pending Spares'),
        ('pending_customer', 'Pending Customer'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
        ('requested', 'Requested'),
        ('approved', 'Approved'),
        ('issued', 'Issued'),
        ('received', 'Received')
    ], string='New Status')
    
    # OTP Fields
    otp_code = fields.Char(string='OTP Code', size=5)
    otp_verified = fields.Boolean(string='OTP Verified', default=False)
    otp_generated_date = fields.Datetime(string='OTP Generated Date')
    
    # Description
    description = fields.Text(string='Description')
    
    # User who triggered the notification
    user_id = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user)
    
    # Timestamp
    create_date = fields.Datetime(string='Created On', default=fields.Datetime.now)
    
    @api.depends('call_id', 'notification_type')
    def _compute_display_name(self):
        for record in self:
            if record.call_id:
                record.display_name = f"{record.call_id.name} - {dict(record._fields['notification_type'].selection).get(record.notification_type, 'Notification')}"
            else:
                record.display_name = dict(record._fields['notification_type'].selection).get(record.notification_type, 'Notification')

    def generate_otp(self):
        """Generate a 5-digit OTP code"""
        self.ensure_one()
        # Generate random 5-digit OTP
        otp = ''.join(random.choices(string.digits, k=5))
        self.write({
            'otp_code': otp,
            'otp_generated_date': fields.Datetime.now(),
            'otp_verified': False
        })
        return otp

    def verify_otp(self, entered_otp):
        """Verify the entered OTP"""
        self.ensure_one()
        if self.otp_code == entered_otp:
            self.otp_verified = True
            return True
        return False