# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class FSMTechnician(models.Model):
    _name = 'fsm.technician'
    _description = 'Field Service Technician'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'create_date desc'
    
    name = fields.Char(string='Name', required=True, tracking=True)
    code = fields.Char(string='Code', readonly=True, copy=False, default='New')
    user_id = fields.Many2one('res.users', string='User', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Contact')
    service_partner_id = fields.Many2one('fsm.service.partner', string='Service Partner')
    dealer_id = fields.Many2one('fsm.dealer', string='Dealer')
    image_1920 = fields.Image(string='Image', max_width=1920, max_height=1920)
    
    # Contact Information
    email = fields.Char(string='Email', related='user_id.email', readonly=True, store=True)
    phone = fields.Char(string='Phone')
    mobile = fields.Char(string='Mobile')
    
    # Service Areas
    pincode_ids = fields.One2many('fsm.technician.pincode', 'technician_id', string='Service Areas')
    
    # Related Calls
    call_ids = fields.One2many('fsm.call', 'technician_id', string='Assigned Calls')
    call_count = fields.Integer(string='Call Count', compute='_compute_call_count')
    active_call_count = fields.Integer(string='Active Calls', compute='_compute_call_count')
    
    # Status
    state = fields.Selection([
        ('available', 'Available'),
        ('busy', 'Busy'),
        ('offline', 'Offline')
    ], default='available', string='Status', tracking=True)
    
    # Skills and Specialization
    skill_ids = fields.Many2many('fsm.skill', string='Skills')
    specialization = fields.Text(string='Specialization')
    
    # Performance Metrics
    rating = fields.Float(string='Average Rating', compute='_compute_rating', store=True)
    total_calls_completed = fields.Integer(string='Total Calls Completed', compute='_compute_performance', store=True)
    avg_resolution_time = fields.Float(string='Avg Resolution Time (Days)', compute='_compute_performance', store=True)
    
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    
    @api.model
    def create(self, vals):
        if vals.get('code', 'New') == 'New':
            vals['code'] = self.env['ir.sequence'].next_by_code('fsm.technician') or 'New'
        return super(FSMTechnician, self).create(vals)
    
    @api.depends('call_ids', 'call_ids.state')
    def _compute_call_count(self):
        for record in self:
            record.call_count = len(record.call_ids)
            record.active_call_count = len(record.call_ids.filtered(
                lambda c: c.state not in ['closed', 'cancelled']
            ))
    
    @api.depends('call_ids.feedback_ids.rating')
    def _compute_rating(self):
        for record in self:
            feedbacks = record.call_ids.mapped('feedback_ids').filtered(lambda f: f.rating)
            if feedbacks:
                ratings = [int(f.rating) for f in feedbacks]
                record.rating = sum(ratings) / len(ratings)
            else:
                record.rating = 0.0
    
    @api.depends('call_ids', 'call_ids.state', 'call_ids.closed_date', 'call_ids.call_date')
    def _compute_performance(self):
        for record in self:
            completed_calls = record.call_ids.filtered(lambda c: c.state == 'closed')
            record.total_calls_completed = len(completed_calls)
            
            if completed_calls:
                total_days = 0
                valid_calls = 0
                for call in completed_calls:
                    if call.closed_date and call.call_date:
                        days = (call.closed_date - call.call_date).days
                        total_days += days
                        valid_calls += 1
                
                record.avg_resolution_time = total_days / valid_calls if valid_calls > 0 else 0
            else:
                record.avg_resolution_time = 0
    
    def action_set_available(self):
        self.state = 'available'
    
    def action_set_busy(self):
        self.state = 'busy'
    
    def action_set_offline(self):
        self.state = 'offline'
    
    @api.constrains('user_id')
    def _check_unique_user(self):
        for record in self:
            existing = self.search([
                ('user_id', '=', record.user_id.id),
                ('id', '!=', record.id)
            ])
            if existing:
                raise ValidationError('This user is already assigned as a technician!')


class FSMTechnicianPincode(models.Model):
    _name = 'fsm.technician.pincode'
    _description = 'Technician Service Area (Pincode)'
    _rec_name = 'pincode'
    
    technician_id = fields.Many2one('fsm.technician', string='Technician', required=True, ondelete='cascade')
    pincode = fields.Char(string='Pincode', required=True)
    area_name = fields.Char(string='Area Name')
    city = fields.Char(string='City')
    state = fields.Char(string='State')
    priority = fields.Integer(string='Priority', default=10, help='Lower value means higher priority')
    active = fields.Boolean(default=True)
    
    # Master data mapping
    fsm_pincode_id = fields.Many2one('fsm.pincode', string='Master Pincode')
    fsm_area_id = fields.Many2one('fsm.area', string='Master Area')
    fsm_district_id = fields.Many2one('fsm.district', string='Master District')
    fsm_state_id = fields.Many2one('fsm.state', string='Master State')
    
    @api.onchange('fsm_pincode_id')
    def _onchange_fsm_pincode_id(self):
        if self.fsm_pincode_id:
            self.pincode = self.fsm_pincode_id.pincode
            self.fsm_district_id = self.fsm_pincode_id.district_id
            self.fsm_state_id = self.fsm_pincode_id.state_id
            if self.fsm_pincode_id.district_id:
                self.city = self.fsm_pincode_id.district_id.name
            if self.fsm_pincode_id.state_id:
                self.state = self.fsm_pincode_id.state_id.name
    
    @api.onchange('fsm_area_id')
    def _onchange_fsm_area_id(self):
        if self.fsm_area_id:
            self.area_name = self.fsm_area_id.name
            self.fsm_pincode_id = self.fsm_area_id.pincode_id
            self.fsm_district_id = self.fsm_area_id.district_id
            self.fsm_state_id = self.fsm_area_id.state_id
            self.pincode = self.fsm_area_id.pincode_id.pincode if self.fsm_area_id.pincode_id else ''
            if self.fsm_area_id.district_id:
                self.city = self.fsm_area_id.district_id.name
            if self.fsm_area_id.state_id:
                self.state = self.fsm_area_id.state_id.name
    
    _sql_constraints = [
        ('unique_technician_pincode', 'UNIQUE(technician_id, pincode)', 'Pincode already assigned to this technician!')
    ]
    
    @api.model
    def get_available_technician(self, pincode):
        """Find available technician for given pincode"""
        domain = [
            ('pincode', '=', pincode),
            ('active', '=', True),
            ('technician_id.state', '=', 'available'),
            ('technician_id.active', '=', True)
        ]
        technician_pincodes = self.search(domain, order='priority')
        
        if technician_pincodes:
            # Find technician with least active calls
            technicians_data = []
            for tp in technician_pincodes:
                active_calls = tp.technician_id.call_ids.filtered(
                    lambda c: c.state not in ['closed', 'cancelled']
                )
                technicians_data.append({
                    'technician': tp.technician_id,
                    'active_calls': len(active_calls),
                    'priority': tp.priority
                })
            
            # Sort by priority first, then by active calls
            technicians_data.sort(key=lambda x: (x['priority'], x['active_calls']))
            
            if technicians_data:
                return technicians_data[0]['technician']
        
        return False
    
    @api.model
    def get_technicians_for_pincode(self, pincode):
        """Get all technicians serving a pincode"""
        domain = [
            ('pincode', '=', pincode),
            ('active', '=', True),
            ('technician_id.active', '=', True)
        ]
        return self.search(domain).mapped('technician_id')


class FSMSkill(models.Model):
    _name = 'fsm.skill'
    _description = 'Technician Skill'
    _order = 'name'
    
    name = fields.Char(string='Skill Name', required=True)
    description = fields.Text(string='Description')
    technician_ids = fields.Many2many('fsm.technician', string='Technicians')
    active = fields.Boolean(default=True)
    
    _sql_constraints = [
        ('unique_skill_name', 'UNIQUE(name)', 'Skill name must be unique!')
    ]