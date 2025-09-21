# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta

class FSMClaim(models.Model):
    _name = 'fsm.claim'
    _description = 'Service Partner Claim'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'create_date desc'
    
    name = fields.Char(string='Claim Number', readonly=True, copy=False, default='New')
    
    # Service Partner Information
    service_partner_id = fields.Many2one('fsm.service.partner', string='Service Partner', required=True, tracking=True)
    technician_ids = fields.Many2many('fsm.technician', string='Technicians', compute='_compute_technicians', store=True)
    
    # Claim Period
    period_start = fields.Date(string='Period Start', required=True)
    period_end = fields.Date(string='Period End', required=True)
    claim_date = fields.Date(string='Claim Date', default=fields.Date.today, required=True)
    
    # Service Calls
    call_ids = fields.Many2many('fsm.call', string='Service Calls', domain="[('service_partner_id', '=', service_partner_id)]")
    call_count = fields.Integer(string='Total Calls', compute='_compute_call_statistics', store=True)
    
    # TAT-based Claims
    claim_line_ids = fields.One2many('fsm.claim.line', 'claim_id', string='Claim Lines')
    
    # Amount Calculation
    total_calls_amount = fields.Monetary(string='Total Calls Amount', compute='_compute_amounts', store=True)
    spare_parts_amount = fields.Monetary(string='Spare Parts Amount', compute='_compute_amounts', store=True)
    expense_amount = fields.Monetary(string='Expense Amount', compute='_compute_amounts', store=True)
    incentive_amount = fields.Monetary(string='Incentive Amount', compute='_compute_amounts', store=True)
    penalty_amount = fields.Monetary(string='Penalty Amount', compute='_compute_amounts', store=True)
    
    subtotal_amount = fields.Monetary(string='Subtotal', compute='_compute_amounts', store=True)
    tax_amount = fields.Monetary(string='Tax Amount', compute='_compute_amounts', store=True)
    total_amount = fields.Monetary(string='Total Claim Amount', compute='_compute_amounts', store=True)
    
    # Payment Information
    payment_method = fields.Selection([
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
        ('cash', 'Cash'),
        ('online', 'Online Payment')
    ], string='Payment Method', default='bank_transfer')
    
    payment_reference = fields.Char(string='Payment Reference')
    payment_date = fields.Date(string='Payment Date')
    
    # Bank Details (from service partner)
    bank_account_number = fields.Char(string='Bank Account', related='service_partner_id.bank_account_number', readonly=True)
    bank_name = fields.Char(string='Bank Name', related='service_partner_id.bank_name', readonly=True)
    ifsc_code = fields.Char(string='IFSC Code', related='service_partner_id.ifsc_code', readonly=True)
    
    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('verified', 'Verified'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled')
    ], default='draft', string='Status', tracking=True)
    
    # Approval Process
    submitted_by = fields.Many2one('res.users', string='Submitted By')
    submitted_date = fields.Datetime(string='Submitted Date')
    
    verified_by = fields.Many2one('res.users', string='Verified By')
    verified_date = fields.Datetime(string='Verified Date')
    
    approved_by = fields.Many2one('res.users', string='Approved By')
    approved_date = fields.Datetime(string='Approved Date')
    
    rejected_by = fields.Many2one('res.users', string='Rejected By')
    rejected_date = fields.Datetime(string='Rejected Date')
    rejection_reason = fields.Text(string='Rejection Reason')
    
    # Notes
    notes = fields.Text(string='Notes')
    internal_notes = fields.Text(string='Internal Notes')
    
    # Attachments
    attachment_ids = fields.Many2many('ir.attachment', string='Supporting Documents')
    attachment_count = fields.Integer(string='Document Count', compute='_compute_attachment_count')
    
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('fsm.claim') or 'New'
        return super(FSMClaim, self).create(vals)
    
    @api.depends('service_partner_id')
    def _compute_technicians(self):
        for record in self:
            record.technician_ids = record.service_partner_id.technician_ids
    
    @api.depends('call_ids')
    def _compute_call_statistics(self):
        for record in self:
            record.call_count = len(record.call_ids)
    
    @api.depends('claim_line_ids.amount', 'call_ids', 'expense_amount', 'incentive_amount', 'penalty_amount')
    def _compute_amounts(self):
        for record in self:
            # TAT-based claim amounts
            record.total_calls_amount = sum(record.claim_line_ids.mapped('amount'))
            
            # Calculate spare parts amount from calls
            spare_requests = record.call_ids.mapped('spare_request_ids').filtered(lambda r: r.state == 'received')
            spare_amount = 0
            for request in spare_requests:
                spare_amount += sum(request.spare_line_ids.mapped('subtotal'))
            record.spare_parts_amount = spare_amount
            
            # Calculate expense amount from calls
            expenses = self.env['fsm.expense'].search([
                ('call_id', 'in', record.call_ids.ids),
                ('state', '=', 'approved'),
                ('is_reimbursable', '=', True)
            ])
            record.expense_amount = sum(expenses.mapped('final_amount'))
            
            # Calculate subtotal
            record.subtotal_amount = (
                record.total_calls_amount + 
                record.spare_parts_amount + 
                record.expense_amount + 
                record.incentive_amount - 
                record.penalty_amount
            )
            
            # Calculate tax (GST 18% for example)
            record.tax_amount = record.subtotal_amount * 0.18
            
            # Total amount
            record.total_amount = record.subtotal_amount + record.tax_amount
    
    @api.depends('attachment_ids')
    def _compute_attachment_count(self):
        for record in self:
            record.attachment_count = len(record.attachment_ids)
    
    @api.onchange('service_partner_id', 'period_start', 'period_end')
    def _onchange_period(self):
        """Load service calls for the period"""
        if self.service_partner_id and self.period_start and self.period_end:
            calls = self.env['fsm.call'].search([
                ('service_partner_id', '=', self.service_partner_id.id),
                ('call_date', '>=', self.period_start),
                ('call_date', '<=', self.period_end),
                ('state', 'in', ['closed', 'resolved'])
            ])
            self.call_ids = [(6, 0, calls.ids)]
    
    def action_calculate_claim(self):
        """Calculate claim based on TAT categories"""
        self.ensure_one()
        
        # Clear existing lines
        self.claim_line_ids.unlink()
        
        # Get TAT categories for service partner
        tat_categories = self.service_partner_id.tat_category_ids.sorted('days')
        
        if not tat_categories:
            raise ValidationError('No TAT categories defined for this service partner!')
        
        # Group calls by TAT achievement
        for category in tat_categories:
            eligible_calls = self.env['fsm.call']
            
            for call in self.call_ids:
                if call.closed_date and call.call_date:
                    days_taken = (call.closed_date.date() - call.call_date.date()).days
                    if days_taken <= category.days:
                        eligible_calls |= call
            
            if eligible_calls:
                # Remove calls already counted in lower TAT categories
                already_counted = self.claim_line_ids.mapped('call_ids')
                eligible_calls = eligible_calls - already_counted
                
                if eligible_calls:
                    line_vals = {
                        'claim_id': self.id,
                        'tat_category_id': category.id,
                        'call_ids': [(6, 0, eligible_calls.ids)],
                        'call_count': len(eligible_calls),
                        'rate': category.amount,
                        'amount': len(eligible_calls) * category.amount
                    }
                    self.env['fsm.claim.line'].create(line_vals)
        
        self.message_post(body='Claim calculated based on TAT categories.')
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Claim Calculated',
                'message': f'Total claim amount: {self.total_amount}',
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_submit(self):
        """Submit claim for verification"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError('Only draft claims can be submitted!')
        
        if not self.claim_line_ids:
            raise ValidationError('Please calculate the claim before submitting!')
        
        self.write({
            'state': 'submitted',
            'submitted_by': self.env.user.id,
            'submitted_date': fields.Datetime.now()
        })
        
        self.message_post(body='Claim submitted for verification.')
    
    def action_verify(self):
        """Verify claim details"""
        self.ensure_one()
        if self.state != 'submitted':
            raise UserError('Only submitted claims can be verified!')
        
        self.write({
            'state': 'verified',
            'verified_by': self.env.user.id,
            'verified_date': fields.Datetime.now()
        })
        
        self.message_post(body='Claim verified successfully.')
    
    def action_approve(self):
        """Approve claim for payment"""
        self.ensure_one()
        if self.state != 'verified':
            raise UserError('Only verified claims can be approved!')
        
        self.write({
            'state': 'approved',
            'approved_by': self.env.user.id,
            'approved_date': fields.Datetime.now()
        })
        
        self.message_post(body='Claim approved for payment.')
    
    def action_pay(self):
        """Mark claim as paid"""
        self.ensure_one()
        if self.state != 'approved':
            raise UserError('Only approved claims can be paid!')
        
        if not self.payment_reference:
            raise ValidationError('Please enter payment reference!')
        
        self.write({
            'state': 'paid',
            'payment_date': fields.Date.today()
        })
        
        self.message_post(body=f'Claim paid. Reference: {self.payment_reference}')
    
    def action_reject(self):
        """Reject claim"""
        self.ensure_one()
        if self.state in ['paid', 'cancelled']:
            raise UserError('Cannot reject paid or cancelled claims!')
        
        # Open rejection wizard
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reject Claim',
            'res_model': 'fsm.claim.reject',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_claim_id': self.id}
        }
    
    def action_cancel(self):
        """Cancel claim"""
        self.ensure_one()
        if self.state == 'paid':
            raise UserError('Paid claims cannot be cancelled!')
        
        self.state = 'cancelled'
        self.message_post(body='Claim cancelled.')
    
    def action_print_claim(self):
        """Print claim report"""
        self.ensure_one()
        # TODO: Implement report printing
        return {
            'type': 'ir.actions.report',
            'report_name': 'field_service_management.report_fsm_claim',
            'report_type': 'qweb-pdf',
            'data': None,
            'context': self.env.context,
            'res_ids': self.ids,
        }
    
    @api.constrains('period_start', 'period_end')
    def _check_period_dates(self):
        for record in self:
            if record.period_end < record.period_start:
                raise ValidationError('Period end date must be after start date!')


class FSMClaimLine(models.Model):
    _name = 'fsm.claim.line'
    _description = 'Claim Line'
    _rec_name = 'tat_category_id'
    
    claim_id = fields.Many2one('fsm.claim', string='Claim', required=True, ondelete='cascade')
    
    # TAT Category
    tat_category_id = fields.Many2one('fsm.tat.category', string='TAT Category', required=True)
    days_limit = fields.Integer(string='Days Limit', related='tat_category_id.days', readonly=True)
    
    # Service Calls
    call_ids = fields.Many2many('fsm.call', string='Service Calls')
    call_count = fields.Integer(string='Call Count', compute='_compute_call_count', store=True)
    
    # Amount Calculation
    rate = fields.Monetary(string='Rate per Call', currency_field='currency_id', required=True)
    amount = fields.Monetary(string='Amount', currency_field='currency_id', compute='_compute_amount', store=True)
    
    currency_id = fields.Many2one('res.currency', related='claim_id.currency_id', readonly=True)
    
    # Notes
    notes = fields.Text(string='Notes')
    
    @api.depends('call_ids')
    def _compute_call_count(self):
        for line in self:
            line.call_count = len(line.call_ids)
    
    @api.depends('call_count', 'rate')
    def _compute_amount(self):
        for line in self:
            line.amount = line.call_count * line.rate
    
    @api.onchange('tat_category_id')
    def _onchange_tat_category_id(self):
        if self.tat_category_id:
            self.rate = self.tat_category_id.amount


class FSMClaimReject(models.TransientModel):
    _name = 'fsm.claim.reject'
    _description = 'Reject Claim Wizard'
    
    claim_id = fields.Many2one('fsm.claim', string='Claim', required=True)
    rejection_reason = fields.Text(string='Rejection Reason', required=True)
    
    def action_reject(self):
        """Reject the claim with reason"""
        self.ensure_one()
        self.claim_id.write({
            'state': 'rejected',
            'rejected_by': self.env.user.id,
            'rejected_date': fields.Datetime.now(),
            'rejection_reason': self.rejection_reason
        })
        self.claim_id.message_post(body=f'Claim rejected. Reason: {self.rejection_reason}')