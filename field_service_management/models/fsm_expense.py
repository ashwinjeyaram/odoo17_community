# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError

class FSMExpense(models.Model):
    _name = 'fsm.expense'
    _description = 'Field Service Expense'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'expense_date desc'
    
    name = fields.Char(string='Expense Reference', readonly=True, copy=False, default='New')
    
    # Related Records
    call_id = fields.Many2one('fsm.call', string='Service Call', required=True, tracking=True)
    technician_id = fields.Many2one('fsm.technician', string='Technician', related='call_id.technician_id', store=True, readonly=True)
    service_partner_id = fields.Many2one('fsm.service.partner', string='Service Partner', related='technician_id.service_partner_id', store=True, readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', related='call_id.partner_id', store=True, readonly=True)
    
    # Expense Details
    expense_date = fields.Date(string='Expense Date', default=fields.Date.today, required=True, tracking=True)
    expense_type = fields.Selection([
        ('travel', 'Travel'),
        ('fuel', 'Fuel'),
        ('food', 'Food & Accommodation'),
        ('tools', 'Tools & Equipment'),
        ('parts', 'Spare Parts'),
        ('other', 'Other')
    ], string='Expense Type', required=True, tracking=True)
    
    description = fields.Text(string='Description', required=True)
    
    # Travel Details (for travel expenses)
    from_location = fields.Char(string='From Location')
    to_location = fields.Char(string='To Location')
    distance_km = fields.Float(string='Distance (KM)')
    rate_per_km = fields.Monetary(string='Rate per KM', currency_field='currency_id')
    
    # Amount
    amount = fields.Monetary(string='Amount', currency_field='currency_id', required=True, tracking=True)
    calculated_amount = fields.Monetary(string='Calculated Amount', compute='_compute_calculated_amount', store=True)
    final_amount = fields.Monetary(string='Final Amount', compute='_compute_final_amount', store=True)
    
    # Reimbursement
    is_billable = fields.Boolean(string='Billable to Customer', default=False)
    is_reimbursable = fields.Boolean(string='Reimbursable', default=True)
    reimbursed = fields.Boolean(string='Reimbursed', default=False, tracking=True)
    reimbursement_date = fields.Date(string='Reimbursement Date')
    
    # Documents
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments', help='Attach receipts or supporting documents')
    attachment_count = fields.Integer(string='Attachment Count', compute='_compute_attachment_count')
    
    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled')
    ], default='draft', string='Status', tracking=True)
    
    # Approval
    submitted_date = fields.Datetime(string='Submitted Date')
    approved_by = fields.Many2one('res.users', string='Approved By')
    approved_date = fields.Datetime(string='Approved Date')
    rejected_by = fields.Many2one('res.users', string='Rejected By')
    rejected_date = fields.Datetime(string='Rejected Date')
    rejection_reason = fields.Text(string='Rejection Reason')
    
    # Payment
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
        ('online', 'Online Payment')
    ], string='Payment Method')
    payment_reference = fields.Char(string='Payment Reference')
    
    # Notes
    notes = fields.Text(string='Notes')
    
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('fsm.expense') or 'New'
        return super(FSMExpense, self).create(vals)
    
    @api.depends('distance_km', 'rate_per_km', 'expense_type')
    def _compute_calculated_amount(self):
        for record in self:
            if record.expense_type == 'travel' and record.distance_km and record.rate_per_km:
                record.calculated_amount = record.distance_km * record.rate_per_km
            else:
                record.calculated_amount = 0.0
    
    @api.depends('amount', 'calculated_amount', 'expense_type')
    def _compute_final_amount(self):
        for record in self:
            if record.expense_type == 'travel' and record.calculated_amount > 0:
                record.final_amount = record.calculated_amount
            else:
                record.final_amount = record.amount
    
    @api.depends('attachment_ids')
    def _compute_attachment_count(self):
        for record in self:
            record.attachment_count = len(record.attachment_ids)
    
    @api.onchange('expense_type')
    def _onchange_expense_type(self):
        """Set default values based on expense type"""
        if self.expense_type == 'travel':
            # Get default rate per km from configuration
            try:
                if self.currency_id and self.env.company.currency_id:
                    self.rate_per_km = self.env.company.currency_id.compute(10, self.currency_id)  # Default rate
                else:
                    self.rate_per_km = 10.0  # Fallback default rate
            except:
                self.rate_per_km = 10.0  # Fallback default rate
        else:
            self.distance_km = 0
            self.rate_per_km = 0
    
    @api.onchange('call_id')
    def _onchange_call_id(self):
        """Auto-fill locations from service call"""
        if self.call_id and self.expense_type == 'travel':
            self.to_location = f"{self.call_id.city}, {self.call_id.pincode}" if self.call_id.city else self.call_id.pincode
    
    def action_submit(self):
        """Submit expense for approval"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError('Only draft expenses can be submitted!')

        # Only require attachments for high-value expenses that are not travel-related
        if (not self.attachment_ids and self.final_amount > 500 and
            self.expense_type not in ['travel']):
            raise ValidationError('Please attach supporting documents for non-travel expenses above 500!')

        self.write({
            'state': 'submitted',
            'submitted_date': fields.Datetime.now()
        })

        # Create activity for manager approval
        self.activity_schedule(
            'mail.mail_activity_data_todo',
            summary=f'Expense approval required: {self.name}',
            user_id=self.env.user.id  # TODO: Assign to manager
        )

        self.message_post(body='Expense submitted for approval.')
    
    def action_approve(self):
        """Approve expense"""
        self.ensure_one()
        if self.state != 'submitted':
            raise UserError('Only submitted expenses can be approved!')
        
        self.write({
            'state': 'approved',
            'approved_by': self.env.user.id,
            'approved_date': fields.Datetime.now()
        })
        
        self.message_post(body='Expense approved.')
        
        # Update service call charges if billable
        if self.is_billable and self.call_id:
            self.call_id.service_charge += self.final_amount
    
    def action_reject(self):
        """Reject expense"""
        self.ensure_one()
        if self.state != 'submitted':
            raise UserError('Only submitted expenses can be rejected!')
        
        # Open rejection wizard
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reject Expense',
            'res_model': 'fsm.expense.reject',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_expense_id': self.id}
        }
    
    def action_pay(self):
        """Mark expense as paid"""
        self.ensure_one()
        if self.state != 'approved':
            raise UserError('Only approved expenses can be paid!')
        
        self.write({
            'state': 'paid',
            'reimbursed': True,
            'reimbursement_date': fields.Date.today()
        })
        
        self.message_post(body='Expense paid.')
    
    def action_cancel(self):
        """Cancel expense"""
        self.ensure_one()
        if self.state in ['paid']:
            raise UserError('Paid expenses cannot be cancelled!')
        
        self.state = 'cancelled'
        self.message_post(body='Expense cancelled.')
    
    def action_view_attachments(self):
        """View attached documents"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Attachments',
            'res_model': 'ir.attachment',
            'view_mode': 'kanban,form',
            'domain': [('id', 'in', self.attachment_ids.ids)],
            'context': {
                'default_res_model': self._name,
                'default_res_id': self.id,
            }
        }
    
    @api.constrains('distance_km', 'rate_per_km', 'amount')
    def _check_positive_values(self):
        for record in self:
            if record.distance_km < 0:
                raise ValidationError('Distance cannot be negative!')
            if record.rate_per_km < 0:
                raise ValidationError('Rate per KM cannot be negative!')
            if record.amount < 0:
                raise ValidationError('Amount cannot be negative!')


class FSMExpenseCategory(models.Model):
    _name = 'fsm.expense.category'
    _description = 'Expense Category'
    _order = 'sequence, name'
    
    name = fields.Char(string='Category Name', required=True)
    code = fields.Char(string='Category Code')
    sequence = fields.Integer(string='Sequence', default=10)
    
    # Limits
    daily_limit = fields.Monetary(string='Daily Limit', currency_field='currency_id')
    monthly_limit = fields.Monetary(string='Monthly Limit', currency_field='currency_id')
    requires_approval = fields.Boolean(string='Requires Approval', default=True)
    auto_approve_below = fields.Monetary(string='Auto-approve Below', currency_field='currency_id')
    
    # Documentation Requirements
    requires_receipt = fields.Boolean(string='Receipt Required', default=True)
    min_receipt_amount = fields.Monetary(string='Min Amount for Receipt', currency_field='currency_id')
    
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    
    _sql_constraints = [
        ('unique_code', 'UNIQUE(code, company_id)', 'Category code must be unique per company!')
    ]


class FSMExpenseReport(models.Model):
    _name = 'fsm.expense.report'
    _description = 'Expense Report'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'create_date desc'
    
    name = fields.Char(string='Report Number', readonly=True, copy=False, default='New')
    
    # Period
    period_start = fields.Date(string='Period Start', required=True)
    period_end = fields.Date(string='Period End', required=True)
    
    # Employee/Technician
    technician_id = fields.Many2one('fsm.technician', string='Technician')
    service_partner_id = fields.Many2one('fsm.service.partner', string='Service Partner')
    
    # Expenses
    expense_ids = fields.Many2many('fsm.expense', string='Expenses')
    expense_count = fields.Integer(string='Expense Count', compute='_compute_expense_stats')
    
    # Totals
    total_amount = fields.Monetary(string='Total Amount', compute='_compute_expense_stats', store=True)
    approved_amount = fields.Monetary(string='Approved Amount', compute='_compute_expense_stats', store=True)
    pending_amount = fields.Monetary(string='Pending Amount', compute='_compute_expense_stats', store=True)
    paid_amount = fields.Monetary(string='Paid Amount', compute='_compute_expense_stats', store=True)
    
    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('paid', 'Paid')
    ], default='draft', string='Status', tracking=True)
    
    notes = fields.Text(string='Notes')
    
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('fsm.expense.report') or 'New'
        return super(FSMExpenseReport, self).create(vals)
    
    @api.depends('expense_ids', 'expense_ids.final_amount', 'expense_ids.state')
    def _compute_expense_stats(self):
        for record in self:
            expenses = record.expense_ids
            record.expense_count = len(expenses)
            record.total_amount = sum(expenses.mapped('final_amount'))
            record.approved_amount = sum(expenses.filtered(lambda e: e.state == 'approved').mapped('final_amount'))
            record.pending_amount = sum(expenses.filtered(lambda e: e.state == 'submitted').mapped('final_amount'))
            record.paid_amount = sum(expenses.filtered(lambda e: e.state == 'paid').mapped('final_amount'))
    
    def action_generate_report(self):
        """Generate expense report for period"""
        self.ensure_one()
        
        domain = [
            ('expense_date', '>=', self.period_start),
            ('expense_date', '<=', self.period_end)
        ]
        
        if self.technician_id:
            domain.append(('technician_id', '=', self.technician_id.id))
        if self.service_partner_id:
            domain.append(('service_partner_id', '=', self.service_partner_id.id))
        
        expenses = self.env['fsm.expense'].search(domain)
        self.expense_ids = [(6, 0, expenses.ids)]
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Report Generated',
                'message': f'Found {len(expenses)} expenses for the period.',
                'type': 'success',
                'sticky': False,
            }
        }


class FSMExpenseReject(models.TransientModel):
    _name = 'fsm.expense.reject'
    _description = 'Reject Expense Wizard'
    
    expense_id = fields.Many2one('fsm.expense', string='Expense', required=True)
    rejection_reason = fields.Text(string='Rejection Reason', required=True)
    
    def action_reject(self):
        """Reject the expense with reason"""
        self.ensure_one()
        self.expense_id.write({
            'state': 'rejected',
            'rejected_by': self.env.user.id,
            'rejected_date': fields.Datetime.now(),
            'rejection_reason': self.rejection_reason
        })
        self.expense_id.message_post(body=f'Expense rejected. Reason: {self.rejection_reason}')