# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
import random
import string
from datetime import datetime, timedelta

class FSMFeedback(models.Model):
    _name = 'fsm.feedback'
    _description = 'Customer Feedback'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _rec_name = 'display_name'
    _order = 'create_date desc'
    
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)
    
    # Related Records
    call_id = fields.Many2one('fsm.call', string='Service Call', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Customer', related='call_id.partner_id', store=True, readonly=True)
    technician_id = fields.Many2one('fsm.technician', string='Technician', related='call_id.technician_id', store=True, readonly=True)
    
    # Feedback Information
    rating = fields.Selection([
        ('1', '⭐'),
        ('2', '⭐⭐'),
        ('3', '⭐⭐⭐'),
        ('4', '⭐⭐⭐⭐'),
        ('5', '⭐⭐⭐⭐⭐')
    ], string='Rating', required=True, tracking=True)
    
    satisfaction = fields.Selection([
        ('highly_satisfied', 'Highly Satisfied'),
        ('satisfied', 'Satisfied'),
        ('neutral', 'Neutral'),
        ('dissatisfied', 'Dissatisfied'),
        ('highly_dissatisfied', 'Highly Dissatisfied')
    ], string='Satisfaction Level', required=True)
    
    # Service Quality Metrics
    punctuality = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('average', 'Average'),
        ('poor', 'Poor')
    ], string='Punctuality')
    
    professionalism = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('average', 'Average'),
        ('poor', 'Poor')
    ], string='Professionalism')
    
    problem_resolution = fields.Selection([
        ('resolved', 'Completely Resolved'),
        ('partially', 'Partially Resolved'),
        ('not_resolved', 'Not Resolved')
    ], string='Problem Resolution')
    
    # Recommendation
    would_recommend = fields.Boolean(string='Would Recommend', default=True)
    
    # Comments
    positive_feedback = fields.Text(string='What went well?')
    improvement_areas = fields.Text(string='Areas for Improvement')
    additional_comments = fields.Text(string='Additional Comments')
    
    # OTP Verification
    otp_code = fields.Char(string='OTP Code', size=6)
    otp_generated_at = fields.Datetime(string='OTP Generated At')
    otp_verified = fields.Boolean(string='OTP Verified', default=False, tracking=True)
    otp_attempts = fields.Integer(string='OTP Attempts', default=0)
    otp_sent_to = fields.Char(string='OTP Sent To')
    
    # Verification Method
    verification_method = fields.Selection([
        ('sms', 'SMS'),
        ('email', 'Email'),
        ('both', 'Both SMS and Email')
    ], string='Verification Method', default='sms')
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('otp_sent', 'OTP Sent'),
        ('verified', 'Verified'),
        ('submitted', 'Submitted'),
        ('reviewed', 'Reviewed')
    ], default='draft', string='Status', tracking=True)
    
    # Submission Details
    submitted_date = fields.Datetime(string='Submitted Date')
    submitted_by = fields.Many2one('res.users', string='Submitted By')
    
    # Review Details
    reviewed_by = fields.Many2one('res.users', string='Reviewed By')
    reviewed_date = fields.Datetime(string='Reviewed Date')
    review_notes = fields.Text(string='Review Notes')
    
    # Follow-up
    requires_followup = fields.Boolean(string='Requires Follow-up', default=False)
    followup_done = fields.Boolean(string='Follow-up Done', default=False)
    followup_notes = fields.Text(string='Follow-up Notes')
    
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    
    @api.depends('call_id', 'rating')
    def _compute_display_name(self):
        for record in self:
            if record.call_id and record.rating:
                record.display_name = f"Feedback for {record.call_id.name} - {record.rating} stars"
            else:
                record.display_name = "New Feedback"
    
    @api.model
    def create(self, vals):
        # Check if feedback already exists for this call
        if vals.get('call_id'):
            existing = self.search([
                ('call_id', '=', vals['call_id']),
                ('state', '=', 'submitted')
            ])
            if existing:
                raise ValidationError('Feedback has already been submitted for this service call!')
        
        return super(FSMFeedback, self).create(vals)
    
    def generate_otp(self):
        """Generate 6-digit OTP"""
        self.ensure_one()
        
        # Check if OTP was recently generated (prevent spam)
        if self.otp_generated_at:
            time_diff = fields.Datetime.now() - self.otp_generated_at
            if time_diff < timedelta(minutes=1):
                raise UserError('Please wait 1 minute before requesting a new OTP.')
        
        # Generate random 6-digit OTP
        otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        # Determine where to send OTP
        send_to = None
        if self.verification_method in ['sms', 'both'] and self.partner_id.mobile:
            send_to = self.partner_id.mobile
        elif self.verification_method in ['email', 'both'] and self.partner_id.email:
            send_to = self.partner_id.email
        
        if not send_to:
            raise ValidationError('Customer has no valid contact information for OTP delivery!')
        
        self.write({
            'otp_code': otp,
            'otp_generated_at': fields.Datetime.now(),
            'otp_sent_to': send_to,
            'otp_attempts': 0,
            'state': 'otp_sent'
        })
        
        # Send OTP notification
        self._send_otp_notification(otp, send_to)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'OTP Sent',
                'message': f'OTP has been sent to {send_to}',
                'type': 'success',
                'sticky': False,
            }
        }
    
    def _send_otp_notification(self, otp, recipient):
        """Send OTP via SMS/Email"""
        message = f"""
        Dear {self.partner_id.name},
        
        Your OTP for service feedback verification is: {otp}
        
        This OTP is valid for 10 minutes.
        Service Call: {self.call_id.name}
        
        Thank you for your feedback!
        """
        
        if self.verification_method in ['email', 'both']:
            # Send email
            mail_values = {
                'subject': f'OTP for Service Feedback - {self.call_id.name}',
                'body_html': f'<p>{message}</p>',
                'email_to': recipient if '@' in recipient else self.partner_id.email,
                'email_from': self.env.company.email or 'noreply@company.com',
            }
            self.env['mail.mail'].create(mail_values).send()
        
        if self.verification_method in ['sms', 'both']:
            # TODO: Integrate with SMS gateway
            # For now, just log the message
            self.message_post(body=f"SMS OTP would be sent to {recipient}: {otp}")
    
    def verify_otp(self, entered_otp):
        """Verify entered OTP"""
        self.ensure_one()
        
        if self.state != 'otp_sent':
            raise UserError('Please generate OTP first!')
        
        # Check OTP expiry (10 minutes)
        if self.otp_generated_at:
            time_diff = fields.Datetime.now() - self.otp_generated_at
            if time_diff > timedelta(minutes=10):
                raise ValidationError('OTP has expired. Please generate a new one.')
        
        # Check attempts
        if self.otp_attempts >= 3:
            raise ValidationError('Maximum OTP attempts exceeded. Please generate a new OTP.')
        
        # Verify OTP
        if self.otp_code == entered_otp:
            self.write({
                'otp_verified': True,
                'state': 'verified'
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': 'OTP verified successfully!',
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            self.otp_attempts += 1
            remaining = 3 - self.otp_attempts
            raise ValidationError(f'Invalid OTP. {remaining} attempts remaining.')
    
    def action_verify_otp_wizard(self):
        """Open OTP verification wizard"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Verify OTP',
            'res_model': 'fsm.feedback.verify.otp',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_feedback_id': self.id}
        }
    
    def action_submit(self):
        """Submit feedback after OTP verification"""
        self.ensure_one()
        
        if not self.otp_verified:
            raise ValidationError('Please verify OTP before submitting feedback!')
        
        self.write({
            'state': 'submitted',
            'submitted_date': fields.Datetime.now(),
            'submitted_by': self.env.user.id
        })
        
        # Update service call status if needed
        if self.call_id.state == 'resolved':
            self.call_id.action_close()
        
        # Check if follow-up is needed based on rating
        if int(self.rating) <= 2:
            self.requires_followup = True
            
            # Create activity for follow-up
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=f'Follow-up required for low rating feedback',
                user_id=self.call_id.technician_id.user_id.id if self.call_id.technician_id else self.env.user.id
            )
        
        self.message_post(body='Feedback submitted successfully.')
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Thank You',
                'message': 'Your feedback has been submitted successfully!',
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_review(self):
        """Mark feedback as reviewed"""
        self.ensure_one()
        self.write({
            'state': 'reviewed',
            'reviewed_by': self.env.user.id,
            'reviewed_date': fields.Datetime.now()
        })
    
    def action_mark_followup_done(self):
        """Mark follow-up as completed"""
        self.ensure_one()
        self.followup_done = True
        self.message_post(body='Follow-up completed.')
    
    @api.onchange('rating')
    def _onchange_rating(self):
        """Auto-set satisfaction based on rating"""
        if self.rating:
            rating_int = int(self.rating)
            if rating_int >= 5:
                self.satisfaction = 'highly_satisfied'
            elif rating_int == 4:
                self.satisfaction = 'satisfied'
            elif rating_int == 3:
                self.satisfaction = 'neutral'
            elif rating_int == 2:
                self.satisfaction = 'dissatisfied'
            else:
                self.satisfaction = 'highly_dissatisfied'
    
    def get_feedback_statistics(self):
        """Get feedback statistics for reporting"""
        domain = [('state', '=', 'submitted')]
        all_feedback = self.search(domain)
        
        if not all_feedback:
            return {}
        
        ratings = [int(f.rating) for f in all_feedback]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        
        return {
            'total_feedback': len(all_feedback),
            'average_rating': round(avg_rating, 2),
            'five_star': len([r for r in ratings if r == 5]),
            'four_star': len([r for r in ratings if r == 4]),
            'three_star': len([r for r in ratings if r == 3]),
            'two_star': len([r for r in ratings if r == 2]),
            'one_star': len([r for r in ratings if r == 1]),
            'would_recommend': len(all_feedback.filtered('would_recommend')),
            'requires_followup': len(all_feedback.filtered('requires_followup')),
        }


class FSMFeedbackVerifyOTP(models.TransientModel):
    _name = 'fsm.feedback.verify.otp'
    _description = 'Verify OTP Wizard'
    
    feedback_id = fields.Many2one('fsm.feedback', string='Feedback', required=True)
    entered_otp = fields.Char(string='Enter OTP', size=6, required=True)
    
    def action_verify(self):
        """Verify the entered OTP"""
        self.ensure_one()
        self.feedback_id.verify_otp(self.entered_otp)
        
        # Return to feedback form
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'fsm.feedback',
            'res_id': self.feedback_id.id,
            'view_mode': 'form',
            'target': 'current',
        }