# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    # Field Service Fields
    is_fsm_customer = fields.Boolean(string='Is FSM Customer', default=False)
    is_service_partner = fields.Boolean(string='Is Service Partner', compute='_compute_is_service_partner', store=True)
    is_dealer = fields.Boolean(string='Is Dealer', default=False)
    
    # Related FSM Records
    fsm_call_ids = fields.One2many('fsm.call', 'partner_id', string='Service Calls')
    fsm_call_count = fields.Integer(string='Service Calls', compute='_compute_fsm_counts')
    
    fsm_service_partner_ids = fields.One2many('fsm.service.partner', 'partner_id', string='Service Partner Records')
    fsm_service_partner_count = fields.Integer(string='Service Partners', compute='_compute_fsm_counts')
    
    fsm_technician_ids = fields.One2many('fsm.technician', 'partner_id', string='Technician Records')
    fsm_feedback_ids = fields.One2many('fsm.feedback', 'partner_id', string='Feedback')
    
    # Customer Specific Fields
    preferred_technician_id = fields.Many2one('fsm.technician', string='Preferred Technician')
    service_contract_ids = fields.One2many('fsm.service.contract', 'partner_id', string='Service Contracts')
    
    # Statistics
    avg_service_rating = fields.Float(string='Avg Service Rating', compute='_compute_service_stats', store=True)
    total_service_calls = fields.Integer(string='Total Service Calls', compute='_compute_service_stats', store=True)
    pending_service_calls = fields.Integer(string='Pending Service Calls', compute='_compute_service_stats', store=True)
    
    # Service Preferences
    preferred_service_time = fields.Selection([
        ('morning', 'Morning (9 AM - 12 PM)'),
        ('afternoon', 'Afternoon (12 PM - 3 PM)'),
        ('evening', 'Evening (3 PM - 6 PM)'),
        ('anytime', 'Anytime')
    ], string='Preferred Service Time', default='anytime')
    
    service_notes = fields.Text(string='Service Notes')
    
    @api.depends('fsm_service_partner_ids')
    def _compute_is_service_partner(self):
        for partner in self:
            partner.is_service_partner = bool(partner.fsm_service_partner_ids)
    
    @api.depends('fsm_call_ids', 'fsm_service_partner_ids')
    def _compute_fsm_counts(self):
        for partner in self:
            partner.fsm_call_count = len(partner.fsm_call_ids)
            partner.fsm_service_partner_count = len(partner.fsm_service_partner_ids)
    
    @api.depends('fsm_call_ids', 'fsm_call_ids.state', 'fsm_feedback_ids', 'fsm_feedback_ids.rating')
    def _compute_service_stats(self):
        for partner in self:
            calls = partner.fsm_call_ids
            partner.total_service_calls = len(calls)
            partner.pending_service_calls = len(calls.filtered(lambda c: c.state not in ['closed', 'cancelled']))
            
            # Calculate average rating from feedback
            feedbacks = partner.fsm_feedback_ids.filtered(lambda f: f.rating and f.state == 'submitted')
            if feedbacks:
                ratings = [int(f.rating) for f in feedbacks]
                partner.avg_service_rating = sum(ratings) / len(ratings)
            else:
                partner.avg_service_rating = 0.0
    
    def action_view_service_calls(self):
        """View all service calls for this partner"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Service Calls',
            'res_model': 'fsm.call',
            'view_mode': 'tree,form,kanban',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id}
        }
    
    def action_create_service_call(self):
        """Create a new service call for this partner"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'New Service Call',
            'res_model': 'fsm.call',
            'view_mode': 'form',
            'context': {
                'default_partner_id': self.id,
                'default_phone': self.phone,
                'default_mobile': self.mobile,
                'default_email': self.email,
                'default_pincode': self.zip,
            }
        }
    
    def action_view_service_history(self):
        """View service history report for this partner"""
        self.ensure_one()
        # TODO: Implement service history report
        return {
            'type': 'ir.actions.act_window',
            'name': 'Service History',
            'res_model': 'fsm.call',
            'view_mode': 'tree,form,graph,pivot',
            'domain': [('partner_id', '=', self.id)],
            'context': {
                'search_default_group_by_state': 1,
                'search_default_closed': 1,
            }
        }


class FSMServiceContract(models.Model):
    _name = 'fsm.service.contract'
    _description = 'Service Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    
    name = fields.Char(string='Contract Number', readonly=True, copy=False, default='New')
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True)
    
    # Contract Details
    contract_type = fields.Selection([
        ('amc', 'Annual Maintenance Contract'),
        ('warranty', 'Extended Warranty'),
        ('service', 'Service Agreement'),
        ('support', 'Support Contract')
    ], string='Contract Type', required=True)
    
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    
    # Coverage
    product_ids = fields.Many2many('product.product', string='Covered Products')
    service_types = fields.Text(string='Covered Services')
    max_calls_per_year = fields.Integer(string='Max Calls/Year')
    free_spare_parts = fields.Boolean(string='Free Spare Parts', default=False)
    
    # Pricing
    contract_value = fields.Monetary(string='Contract Value', currency_field='currency_id')
    payment_terms = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
        ('onetime', 'One Time')
    ], string='Payment Terms', default='yearly')
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('terminated', 'Terminated')
    ], default='draft', string='Status', tracking=True)
    
    # Statistics
    calls_used = fields.Integer(string='Calls Used', compute='_compute_contract_stats')
    calls_remaining = fields.Integer(string='Calls Remaining', compute='_compute_contract_stats')
    
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('fsm.service.contract') or 'New'
        return super(FSMServiceContract, self).create(vals)
    
    @api.depends('partner_id', 'start_date', 'end_date', 'max_calls_per_year')
    def _compute_contract_stats(self):
        for contract in self:
            if contract.partner_id and contract.start_date and contract.end_date:
                calls = self.env['fsm.call'].search([
                    ('partner_id', '=', contract.partner_id.id),
                    ('call_date', '>=', contract.start_date),
                    ('call_date', '<=', contract.end_date)
                ])
                contract.calls_used = len(calls)
                
                if contract.max_calls_per_year:
                    contract.calls_remaining = max(0, contract.max_calls_per_year - contract.calls_used)
                else:
                    contract.calls_remaining = -1  # Unlimited
            else:
                contract.calls_used = 0
                contract.calls_remaining = contract.max_calls_per_year or -1
    
    def action_activate(self):
        """Activate the contract"""
        self.ensure_one()
        self.state = 'active'
        self.message_post(body='Contract activated.')
    
    def action_terminate(self):
        """Terminate the contract"""
        self.ensure_one()
        self.state = 'terminated'
        self.message_post(body='Contract terminated.')
    
    @api.model
    def check_expired_contracts(self):
        """Cron job to check and update expired contracts"""
        today = fields.Date.today()
        expired_contracts = self.search([
            ('state', '=', 'active'),
            ('end_date', '<', today)
        ])
        expired_contracts.write({'state': 'expired'})
        
        for contract in expired_contracts:
            contract.message_post(body='Contract has expired.')