# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class FSMServicePartner(models.Model):
    _name = 'fsm.service.partner'
    _description = 'Service Partner'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'create_date desc'
    
    name = fields.Char(string='Partner Name', required=True, tracking=True)
    code = fields.Char(string='Partner Code', readonly=True, copy=False, default='New')
    partner_id = fields.Many2one('res.partner', string='Contact', required=True)
    
    # Contact Information
    street = fields.Char(string='Street', related='partner_id.street', readonly=False)
    street2 = fields.Char(string='Street2', related='partner_id.street2', readonly=False)
    city = fields.Char(string='City', related='partner_id.city', readonly=False)
    state_id = fields.Many2one('res.country.state', string='State', related='partner_id.state_id', readonly=False)
    zip = fields.Char(string='ZIP', related='partner_id.zip', readonly=False)
    country_id = fields.Many2one('res.country', string='Country', related='partner_id.country_id', readonly=False)
    
    phone = fields.Char(string='Phone', related='partner_id.phone', readonly=False)
    mobile = fields.Char(string='Mobile', related='partner_id.mobile', readonly=False)
    email = fields.Char(string='Email', related='partner_id.email', readonly=False)
    website = fields.Char(string='Website', related='partner_id.website', readonly=False)
    
    # Service Information
    service_area_ids = fields.One2many('fsm.service.partner.area', 'partner_id', string='Service Areas')
    technician_ids = fields.One2many('fsm.technician', 'service_partner_id', string='Technicians')
    technician_count = fields.Integer(string='Technician Count', compute='_compute_technician_count')
    
    # Contract Information
    contract_start_date = fields.Date(string='Contract Start Date')
    contract_end_date = fields.Date(string='Contract End Date')
    contract_status = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('terminated', 'Terminated')
    ], default='draft', string='Contract Status', tracking=True)
    
    # TAT Categories (Turn Around Time)
    tat_category_ids = fields.One2many('fsm.tat.category', 'partner_id', string='TAT Categories')
    
    # Performance Metrics
    total_calls = fields.Integer(string='Total Calls', compute='_compute_performance', store=True)
    completed_calls = fields.Integer(string='Completed Calls', compute='_compute_performance', store=True)
    pending_calls = fields.Integer(string='Pending Calls', compute='_compute_performance', store=True)
    avg_rating = fields.Float(string='Average Rating', compute='_compute_performance', store=True)
    
    # Financial Information
    bank_account_number = fields.Char(string='Bank Account Number')
    bank_name = fields.Char(string='Bank Name')
    ifsc_code = fields.Char(string='IFSC Code')
    pan_number = fields.Char(string='PAN Number')
    gst_number = fields.Char(string='GST Number')
    
    # Claims
    claim_ids = fields.One2many('fsm.claim', 'service_partner_id', string='Claims')
    total_claims_amount = fields.Monetary(string='Total Claims', compute='_compute_claims', store=True)
    pending_claims_amount = fields.Monetary(string='Pending Claims', compute='_compute_claims', store=True)
    
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    
    @api.model
    def create(self, vals):
        if vals.get('code', 'New') == 'New':
            vals['code'] = self.env['ir.sequence'].next_by_code('fsm.service.partner') or 'New'
        return super(FSMServicePartner, self).create(vals)
    
    @api.depends('technician_ids')
    def _compute_technician_count(self):
        for record in self:
            record.technician_count = len(record.technician_ids)
    
    @api.depends('technician_ids.call_ids', 'technician_ids.call_ids.state', 'technician_ids.call_ids.feedback_ids.rating')
    def _compute_performance(self):
        for record in self:
            all_calls = record.technician_ids.mapped('call_ids')
            record.total_calls = len(all_calls)
            record.completed_calls = len(all_calls.filtered(lambda c: c.state == 'closed'))
            record.pending_calls = len(all_calls.filtered(lambda c: c.state not in ['closed', 'cancelled']))
            
            feedbacks = all_calls.mapped('feedback_ids').filtered(lambda f: f.rating)
            if feedbacks:
                ratings = [int(f.rating) for f in feedbacks]
                record.avg_rating = sum(ratings) / len(ratings)
            else:
                record.avg_rating = 0.0
    
    @api.depends('claim_ids', 'claim_ids.total_amount', 'claim_ids.state')
    def _compute_claims(self):
        for record in self:
            all_claims = record.claim_ids
            record.total_claims_amount = sum(all_claims.mapped('total_amount'))
            pending_claims = all_claims.filtered(lambda c: c.state != 'paid')
            record.pending_claims_amount = sum(pending_claims.mapped('total_amount'))
    
    def action_activate_contract(self):
        self.contract_status = 'active'
    
    def action_terminate_contract(self):
        self.contract_status = 'terminated'
    
    def action_view_technicians(self):
        """View technicians for this service partner"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Technicians',
            'res_model': 'fsm.technician',
            'view_mode': 'tree,form',
            'domain': [('service_partner_id', '=', self.id)],
        }
    
    @api.constrains('contract_start_date', 'contract_end_date')
    def _check_contract_dates(self):
        for record in self:
            if record.contract_start_date and record.contract_end_date:
                if record.contract_end_date < record.contract_start_date:
                    raise ValidationError('Contract end date must be after start date!')
    
    @api.model
    def _check_contract_expiry(self):
        """Cron job to check and update expired contracts"""
        today = fields.Date.today()
        expired_partners = self.search([
            ('contract_status', '=', 'active'),
            ('contract_end_date', '<', today)
        ])
        expired_partners.write({'contract_status': 'expired'})


class FSMServicePartnerArea(models.Model):
    _name = 'fsm.service.partner.area'
    _description = 'Service Partner Area'
    _rec_name = 'area_name'
    
    partner_id = fields.Many2one('fsm.service.partner', string='Service Partner', required=True, ondelete='cascade')
    area_name = fields.Char(string='Area Name', required=True)
    pincode_from = fields.Char(string='Pincode From')
    pincode_to = fields.Char(string='Pincode To')
    city = fields.Char(string='City')
    state = fields.Char(string='State')
    active = fields.Boolean(default=True)
    
    @api.constrains('pincode_from', 'pincode_to')
    def _check_pincode_range(self):
        for record in self:
            if record.pincode_from and record.pincode_to:
                if record.pincode_from > record.pincode_to:
                    raise ValidationError('Pincode From must be less than or equal to Pincode To!')


class FSMTATCategory(models.Model):
    _name = 'fsm.tat.category'
    _description = 'TAT Category'
    _order = 'days'
    
    partner_id = fields.Many2one('fsm.service.partner', string='Service Partner', required=True, ondelete='cascade')
    name = fields.Char(string='Category Name', required=True)
    days = fields.Integer(string='Days', required=True)
    amount = fields.Monetary(string='Claim Amount', required=True)
    description = fields.Text(string='Description')
    currency_id = fields.Many2one('res.currency', related='partner_id.currency_id', readonly=True)
    active = fields.Boolean(default=True)
    
    _sql_constraints = [
        ('unique_partner_days', 'UNIQUE(partner_id, days)', 'TAT category with same days already exists for this partner!')
    ]
    
    @api.constrains('days', 'amount')
    def _check_positive_values(self):
        for record in self:
            if record.days <= 0:
                raise ValidationError('Days must be positive!')
            if record.amount <= 0:
                raise ValidationError('Amount must be positive!')