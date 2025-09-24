# -*- coding: utf-8 -*-
from odoo import models, fields, api, Command
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta

class FSMCall(models.Model):
    _name = 'fsm.call'
    _description = 'Service Call'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'priority desc, create_date desc'
    _rec_name = 'name'
    
    name = fields.Char(string='Call Number', readonly=True, copy=False, default='New', tracking=True)
    
    # Service Type
    service_type = fields.Selection([
        ('inservice', 'In Service'),
        ('outservice', 'Out Service')
    ], string='Service Type', default='inservice', required=True)
    
    # Customer Information
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True,
                                options="{'create': True, 'create_edit': True}")
    phone = fields.Char(string='Phone', related='partner_id.phone', readonly=False, store=True)
    mobile = fields.Char(string='Mobile', related='partner_id.mobile', readonly=False, store=True)
    email = fields.Char(string='Email', related='partner_id.email', readonly=False, store=True)
    
    # Address Information
    street = fields.Char(string='Street', related='partner_id.street', readonly=False, store=True)
    street2 = fields.Char(string='Street2', related='partner_id.street2', readonly=False, store=True)
    city = fields.Char(string='City', related='partner_id.city', readonly=False, store=True)
    state_id = fields.Many2one('res.country.state', string='State', related='partner_id.state_id', readonly=False, store=True)
    zip = fields.Char(string='ZIP', related='partner_id.zip', readonly=False, store=True)
    country_id = fields.Many2one('res.country', string='Country', related='partner_id.country_id', readonly=False, store=True)
    
    # Location Master Fields
    fsm_state_id = fields.Many2one('fsm.state', string='State')
    fsm_district_id = fields.Many2one('fsm.district', string='District')
    fsm_pincode_id = fields.Many2one('fsm.pincode', string='Pincode')
    fsm_area_id = fields.Many2one('fsm.area', string='Area')
    pincode = fields.Char(string='Service Pincode', required=True)
    
    # Product Information
    product_id = fields.Many2one('product.template', string='Product')
    model_name = fields.Many2one('product.template.attribute.value', string='Model', 
                                 domain="[('product_tmpl_id', '=', product_id)]")
    serial_number = fields.Char(string='Serial Number')
    purchase_date = fields.Date(string='Purchase Date')
    dealer_id = fields.Many2one('fsm.dealer', string='Dealer')
    dealer_phone = fields.Char(string='Dealer Phone')
    fault_id = fields.Many2one('fsm.fault', string='Fault')
    
    # Warranty Information
    warranty_status = fields.Selection([
        ('yes', 'Under Warranty'),
        ('no', 'Out of Warranty'),
        ('stock_set', 'Stock Set'),
        ('extended', 'Extended Warranty')
    ], string='Warranty Status', default='yes')
    warranty_type = fields.Selection([
        ('none', 'No Warranty'),
        ('limited', 'Limited Warranty'),
        ('full', 'Full Warranty')
    ], string='Warranty Type', default='none')
    warranty_expiry_date = fields.Date(string='Warranty Expiry Date', compute='_compute_warranty_expiry_date', store=True, readonly=False)
    
    # Service Information
    call_type = fields.Selection([
        ('installation', 'Installation'),
        ('repair', 'Repair'),
        ('maintenance', 'Maintenance'),
        ('inspection', 'Inspection'),
        ('complaint', 'Complaint'),
        ('sales_enquiry', 'Sales Enquiry'),
        ('spare_enquiry', 'Spare Enquiry'),
        ('others', 'Others')
    ], string='Call Type', default='repair', required=True)
    
    nature_complaint = fields.Text(string='Nature of Complaint', required=True, tracking=True)
    symptoms = fields.Text(string='Symptoms/Issues')
    
    # Assignment
    technician_id = fields.Many2one('fsm.technician', string='Assigned Technician', tracking=True)
    service_partner_id = fields.Many2one('fsm.service.partner', string='Service Partner', tracking=True)
    auto_assigned = fields.Boolean(string='Auto Assigned', default=False)
    
    # Priority and SLA
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Urgent')
    ], default='1', string='Priority', tracking=True)
    
    sla_deadline = fields.Datetime(string='SLA Deadline', compute='_compute_sla_deadline', store=True)
    is_sla_breached = fields.Boolean(string='SLA Breached', compute='_compute_sla_status', store=True)
    
    # State Management
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('pending_spares', 'Pending Spares'),
        ('pending_customer', 'Pending Customer'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled')
    ], default='draft', string='Status', tracking=True, group_expand='_group_expand_states')
    
    # Dates and Time Tracking
    call_date = fields.Datetime(string='Call Date', default=fields.Datetime.now, required=True, tracking=True)
    confirmed_date = fields.Datetime(string='Confirmed Date')
    assigned_date = fields.Datetime(string='Assigned Date')
    start_date = fields.Datetime(string='Start Date')
    resolved_date = fields.Datetime(string='Resolved Date')
    closed_date = fields.Datetime(string='Closed Date')
    
    # Time Metrics
    response_time = fields.Float(string='Response Time (Hours)', compute='_compute_time_metrics', store=True)
    resolution_time = fields.Float(string='Resolution Time (Hours)', compute='_compute_time_metrics', store=True)
    closing_days = fields.Integer(string='Days to Close', compute='_compute_time_metrics', store=True)
    aging_days = fields.Integer(string='Age (Days)', compute='_compute_aging', store=True)
    
    # Service Details
    service_notes = fields.Text(string='Service Notes')
    resolution = fields.Text(string='Resolution')
    parts_used = fields.Text(string='Parts Used')
    
    # Related Records
    spare_request_ids = fields.One2many('fsm.spare.request', 'call_id', string='Spare Requests')
    spare_request_count = fields.Integer(string='Spare Requests', compute='_compute_spare_request_count')
    feedback_ids = fields.One2many('fsm.feedback', 'call_id', string='Feedback')
    expense_ids = fields.One2many('fsm.expense', 'call_id', string='Expenses')
    attachment_ids = fields.Many2many('ir.attachment', 'fsm_call_attachment_rel', 'call_id', 'attachment_id', string='Attachments')
    
    # Charges
    service_charge = fields.Monetary(string='Service Charge', currency_field='currency_id')
    spare_charge = fields.Monetary(string='Spare Parts Charge', currency_field='currency_id')
    total_charge = fields.Monetary(string='Total Charge', compute='_compute_total_charge', store=True)
    is_paid = fields.Boolean(string='Paid', default=False)

    # OTP Information
    current_otp = fields.Char(string='Current OTP', readonly=True, help="Generated OTP for closing this call")
    otp_generated_date = fields.Datetime(string='OTP Generated Date', readonly=True)
    
    # Other Fields
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    user_id = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user)
    active = fields.Boolean(default=True)
    
    # Tags
    tag_ids = fields.Many2many('fsm.call.tag', string='Tags')
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            # Generate sequence based on call type
            call_type = vals.get('call_type', 'repair')
            
            # Define prefixes for each call type
            prefixes = {
                'installation': 'INST',
                'repair': 'REPR',
                'maintenance': 'MAINT',
                'inspection': 'INSP',
                'complaint': 'COMPL',
                'sales_enquiry': 'SALE',
                'spare_enquiry': 'SPARE',
                'others': 'OTHR'
            }
            
            # Get prefix for the call type or default to CALL
            prefix = prefixes.get(call_type, 'CALL')
            
            # Generate a simple sequence number with date
            current_date = fields.Date.today()
            year = current_date.year
            month = str(current_date.month).zfill(2)
            
            # Simple counter approach - find the last record with the same prefix
            last_record = self.search([('name', 'like', f'{prefix}-{year}{month}-')], 
                                    order='name desc', limit=1)
            if last_record:
                # Extract the number part and increment
                last_name = last_record.name
                try:
                    last_number = int(last_name.split('-')[-1])
                    new_number = str(last_number + 1).zfill(5)
                except:
                    new_number = '00001'
            else:
                new_number = '00001'
            
            vals['name'] = f"{prefix}-{year}{month}-{new_number}"
        
        # Auto-assign technician if not specified
        if not vals.get('technician_id') and vals.get('pincode'):
            technician = self._get_available_technician(vals.get('pincode'))
            if technician:
                vals['technician_id'] = technician.id
                vals['auto_assigned'] = True
                vals['service_partner_id'] = technician.service_partner_id.id
        
        return super(FSMCall, self).create(vals)
    
    @api.model
    def _get_available_technician(self, pincode):
        """Get available technician for pincode"""
        TechnicianPincode = self.env['fsm.technician.pincode']
        return TechnicianPincode.get_available_technician(pincode)
    
    @api.depends('priority', 'call_date')
    def _compute_sla_deadline(self):
        for record in self:
            if record.call_date:
                # SLA hours based on priority
                sla_hours = {
                    '0': 72,  # Low - 3 days
                    '1': 48,  # Normal - 2 days
                    '2': 24,  # High - 1 day
                    '3': 4    # Urgent - 4 hours
                }.get(record.priority, 48)
                
                record.sla_deadline = record.call_date + timedelta(hours=sla_hours)
            else:
                record.sla_deadline = False
    
    @api.depends('sla_deadline', 'state')
    def _compute_sla_status(self):
        for record in self:
            if record.sla_deadline and record.state not in ['closed', 'cancelled']:
                record.is_sla_breached = fields.Datetime.now() > record.sla_deadline
            else:
                record.is_sla_breached = False
    
    @api.depends('call_date', 'assigned_date', 'resolved_date', 'closed_date')
    def _compute_time_metrics(self):
        """Compute time metrics for the service call:
        - Response time: Time between call creation and assignment
        - Resolution time: Time between call creation and resolution
        - Closing days: Days between call creation and closure
        """
        for record in self:
            # Response time (hours)
            if record.call_date and record.assigned_date:
                delta = record.assigned_date - record.call_date
                record.response_time = delta.total_seconds() / 3600
            else:
                record.response_time = 0
            
            # Resolution time (hours)
            if record.call_date and record.resolved_date:
                delta = record.resolved_date - record.call_date
                record.resolution_time = delta.total_seconds() / 3600
            else:
                record.resolution_time = 0
            
            # Closing days
            if record.call_date and record.closed_date:
                delta = record.closed_date - record.call_date
                record.closing_days = delta.days
            else:
                record.closing_days = 0
    
    @api.depends('call_date', 'state')
    def _compute_aging(self):
        for record in self:
            if record.call_date and record.state not in ['closed', 'cancelled']:
                delta = fields.Datetime.now() - record.call_date
                record.aging_days = delta.days
            else:
                record.aging_days = 0
    
    @api.depends('spare_request_ids')
    def _compute_spare_request_count(self):
        for record in self:
            record.spare_request_count = len(record.spare_request_ids)
    
    @api.depends('service_charge', 'spare_charge')
    def _compute_total_charge(self):
        for record in self:
            record.total_charge = record.service_charge + record.spare_charge
    
    @api.model
    def _group_expand_states(self, states, domain, order):
        """Expand all states in kanban view"""
        return [key for key, val in type(self).state.selection]
    
    # Workflow Actions
    def action_confirm(self):
        self.ensure_one()
        if self.state != 'draft':
            raise UserError('Only draft calls can be confirmed!')
        
        old_state = self.state
        self.write({
            'state': 'confirmed',
            'confirmed_date': fields.Datetime.now()
        })
        self.message_post(body='Service call confirmed.')
        
        # Create notification transaction
        self.env['fsm.notification.transaction'].create({
            'call_id': self.id,
            'notification_type': 'call_created',
            'old_status': old_state,
            'new_status': 'confirmed',
            'description': f'Service call {self.name} confirmed'
        })
    
    def action_assign(self):
        self.ensure_one()
        if self.state not in ['draft', 'confirmed']:
            raise UserError('Call must be in Draft or Confirmed state to assign!')
        
        if not self.technician_id:
            # Try auto-assignment
            technician = self._get_available_technician(self.pincode)
            if not technician:
                raise ValidationError(f"No available technician for pincode {self.pincode}")
            self.technician_id = technician.id
            self.service_partner_id = technician.service_partner_id.id
            self.auto_assigned = True
        
        old_state = self.state
        self.write({
            'state': 'assigned',
            'assigned_date': fields.Datetime.now()
        })
        
        # Send notification to technician
        self.message_post(
            body=f'Call assigned to {self.technician_id.name}',
            partner_ids=self.technician_id.user_id.partner_id.ids
        )
        
        # Create activity for technician
        self.activity_schedule(
            'mail.mail_activity_data_todo',
            summary=f'Service Call {self.name}',
            user_id=self.technician_id.user_id.id
        )
        
        # Create notification transaction
        self.env['fsm.notification.transaction'].create({
            'call_id': self.id,
            'technician_id': self.technician_id.id,
            'service_partner_id': self.service_partner_id.id if self.service_partner_id else False,
            'notification_type': 'call_assigned',
            'old_status': old_state,
            'new_status': 'assigned',
            'description': f'Service call {self.name} assigned to {self.technician_id.name}'
        })
    
    def action_start(self):
        self.ensure_one()
        if self.state != 'assigned':
            raise UserError('Only assigned calls can be started!')
        
        old_state = self.state
        self.write({
            'state': 'in_progress',
            'start_date': fields.Datetime.now()
        })
        self.message_post(body='Service started.')
        
        # Create notification transaction
        self.env['fsm.notification.transaction'].create({
            'call_id': self.id,
            'technician_id': self.technician_id.id if self.technician_id else False,
            'service_partner_id': self.service_partner_id.id if self.service_partner_id else False,
            'notification_type': 'call_started',
            'old_status': old_state,
            'new_status': 'in_progress',
            'description': f'Service call {self.name} started'
        })
    
    def action_pending_spares(self):
        self.ensure_one()
        old_state = self.state
        self.state = 'pending_spares'
        self.message_post(body='Waiting for spare parts.')
        
        # Create notification transaction
        self.env['fsm.notification.transaction'].create({
            'call_id': self.id,
            'technician_id': self.technician_id.id if self.technician_id else False,
            'service_partner_id': self.service_partner_id.id if self.service_partner_id else False,
            'notification_type': 'status_changed',
            'old_status': old_state,
            'new_status': 'pending_spares',
            'description': f'Service call {self.name} status changed to pending spares'
        })
    
    def action_pending_customer(self):
        self.ensure_one()
        old_state = self.state
        self.state = 'pending_customer'
        self.message_post(body='Waiting for customer response.')
        
        # Create notification transaction
        self.env['fsm.notification.transaction'].create({
            'call_id': self.id,
            'technician_id': self.technician_id.id if self.technician_id else False,
            'service_partner_id': self.service_partner_id.id if self.service_partner_id else False,
            'notification_type': 'status_changed',
            'old_status': old_state,
            'new_status': 'pending_customer',
            'description': f'Service call {self.name} status changed to pending customer'
        })
    
    def has_attachments(self):
        """Check if the call has attachments"""
        self.ensure_one()
        return bool(self.attachment_ids)
    
    def action_resolve(self):
        self.ensure_one()
        if not self.resolution:
            raise ValidationError('Please provide resolution details!')
        
        # Check if attachments exist, if not, open attachment wizard
        if not self.has_attachments():
            return {
                'name': 'Add Attachments',
                'type': 'ir.actions.act_window',
                'res_model': 'fsm.call.attachment.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {'default_call_id': self.id}
            }
        
        old_state = self.state
        self.write({
            'state': 'resolved',
            'resolved_date': fields.Datetime.now()
        })
        self.message_post(body='Service resolved.')
        
        # Generate OTP for closing the call
        notification = self.env['fsm.notification.transaction'].create({
            'call_id': self.id,
            'technician_id': self.technician_id.id if self.technician_id else False,
            'service_partner_id': self.service_partner_id.id if self.service_partner_id else False,
            'notification_type': 'otp_generated',
            'old_status': old_state,
            'new_status': 'resolved',
            'description': f'OTP generated for closing call {self.name}'
        })
        # Generate OTP
        otp = notification.generate_otp()

        # Update call with OTP information
        self.write({
            'current_otp': otp,
            'otp_generated_date': fields.Datetime.now()
        })

        # Send message with OTP
        self.message_post(
            body=f"OTP {otp} generated for closing this service call. Technician must enter this code to close the call."
        )
        
        # Create notification transaction
        self.env['fsm.notification.transaction'].create({
            'call_id': self.id,
            'technician_id': self.technician_id.id if self.technician_id else False,
            'service_partner_id': self.service_partner_id.id if self.service_partner_id else False,
            'notification_type': 'call_resolved',
            'old_status': old_state,
            'new_status': 'resolved',
            'description': f'Service call {self.name} resolved'
        })
    
    def action_close(self):
        self.ensure_one()
        if self.state != 'resolved':
            raise UserError('Only resolved calls can be closed!')
        
        # Check if attachments exist, if not, open attachment wizard
        if not self.has_attachments():
            return {
                'name': 'Add Attachments',
                'type': 'ir.actions.act_window',
                'res_model': 'fsm.call.attachment.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {'default_call_id': self.id}
            }
        
        old_state = self.state
        self.write({
            'state': 'closed',
            'closed_date': fields.Datetime.now()
        })
        self.message_post(body='Service call closed.')
        
        # Create notification transaction
        self.env['fsm.notification.transaction'].create({
            'call_id': self.id,
            'technician_id': self.technician_id.id if self.technician_id else False,
            'service_partner_id': self.service_partner_id.id if self.service_partner_id else False,
            'notification_type': 'call_closed',
            'old_status': old_state,
            'new_status': 'closed',
            'description': f'Service call {self.name} closed'
        })
    
    def action_cancel(self):
        self.ensure_one()
        if self.state in ['closed']:
            raise UserError('Closed calls cannot be cancelled!')
        
        old_state = self.state
        self.state = 'cancelled'
        self.message_post(body='Service call cancelled.')
        
        # Create notification transaction
        self.env['fsm.notification.transaction'].create({
            'call_id': self.id,
            'technician_id': self.technician_id.id if self.technician_id else False,
            'service_partner_id': self.service_partner_id.id if self.service_partner_id else False,
            'notification_type': 'call_cancelled',
            'old_status': old_state,
            'new_status': 'cancelled',
            'description': f'Service call {self.name} cancelled'
        })
    
    def action_reopen(self):
        self.ensure_one()
        if self.state not in ['closed', 'cancelled']:
            raise UserError('Only closed or cancelled calls can be reopened!')
        
        old_state = self.state
        self.state = 'confirmed'
        self.message_post(body='Service call reopened.')
        
        # Create notification transaction
        self.env['fsm.notification.transaction'].create({
            'call_id': self.id,
            'technician_id': self.technician_id.id if self.technician_id else False,
            'service_partner_id': self.service_partner_id.id if self.service_partner_id else False,
            'notification_type': 'status_changed',
            'old_status': old_state,
            'new_status': 'confirmed',
            'description': f'Service call {self.name} reopened'
        })
    
    @api.constrains('warranty_expiry_date', 'purchase_date')
    def _check_warranty_dates(self):
        for record in self:
            if record.warranty_expiry_date and record.purchase_date:
                if record.warranty_expiry_date < record.purchase_date:
                    raise ValidationError('Warranty expiry date cannot be before purchase date!')

    @api.constrains('mobile')
    def _check_mobile_number(self):
        for record in self:
            if record.mobile and record.mobile.strip():
                # Remove any spaces, dashes, or parentheses
                clean_mobile = ''.join(filter(str.isdigit, record.mobile))
                if len(clean_mobile) != 10:
                    raise ValidationError('Mobile number must be exactly 10 digits!')
                if not clean_mobile.startswith(('6', '7', '8', '9')):
                    raise ValidationError('Mobile number must start with 6, 7, 8, or 9!')
    
    @api.constrains('product_id', 'purchase_date')
    def _check_warranty_status(self):
        """Automatically update warranty status based on product and purchase date"""
        for record in self:
            if record.product_id and record.purchase_date:
                # Only update if warranty status is not manually set to extended or stock set
                if record.warranty_status not in ['extended', 'stock_set']:
                    if record.is_under_warranty():
                        record.warranty_status = 'yes'
                    else:
                        record.warranty_status = 'no'
    
    @api.onchange('fsm_state_id')
    def _onchange_fsm_state_id(self):
        if self.fsm_state_id:
            # When state is selected, filter districts to only those in this state
            # and clear pincode and area
            self.fsm_district_id = False
            self.fsm_pincode_id = False
            self.fsm_area_id = False
        else:
            # Clear all dependent fields
            self.fsm_district_id = False
            self.fsm_pincode_id = False
            self.fsm_area_id = False
            return {'domain': {'fsm_district_id': [], 'fsm_pincode_id': []}}

        # Return domain to filter districts by selected state
        return {'domain': {
            'fsm_district_id': [('state_id', '=', self.fsm_state_id.id)],
            'fsm_pincode_id': [('state_id', '=', self.fsm_state_id.id)]
        }}

    @api.onchange('fsm_district_id')
    def _onchange_fsm_district_id(self):
        if self.fsm_district_id:
            # When district is selected, set state and filter pincodes
            self.fsm_state_id = self.fsm_district_id.state_id
            self.fsm_pincode_id = False
            self.fsm_area_id = False
        else:
            # Clear pincode and area, but keep state if already set
            self.fsm_pincode_id = False
            self.fsm_area_id = False
            return {'domain': {'fsm_pincode_id': []}}

        # Return domain to filter pincodes by selected district
        return {'domain': {'fsm_pincode_id': [('district_id', '=', self.fsm_district_id.id)]}}

    @api.onchange('fsm_pincode_id')
    def _onchange_fsm_pincode_id(self):
        if self.fsm_pincode_id:
            # When pincode is selected, set district, state, and pincode value
            self.fsm_district_id = self.fsm_pincode_id.district_id
            self.fsm_state_id = self.fsm_pincode_id.state_id
            self.fsm_area_id = False
            self.pincode = self.fsm_pincode_id.pincode
        else:
            # Clear area and pincode value, but keep district and state if already set
            self.fsm_area_id = False
            self.pincode = ''
            return {'domain': {'fsm_area_id': []}}

        # Return domain to filter areas by selected pincode
        return {'domain': {'fsm_area_id': [('pincode_id', '=', self.fsm_pincode_id.id)]}}

    @api.onchange('fsm_area_id')
    def _onchange_fsm_area_id(self):
        if self.fsm_area_id:
            # When area is selected, set all related fields
            self.fsm_pincode_id = self.fsm_area_id.pincode_id
            self.fsm_district_id = self.fsm_area_id.district_id
            self.fsm_state_id = self.fsm_area_id.state_id
            self.pincode = self.fsm_pincode_id.pincode
        else:
            # Don't clear the pincode if area is deselected
            pass

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Auto-fill address from partner"""
        if self.partner_id:
            # Set the pincode value from partner's zip
            self.pincode = self.partner_id.zip or ''
            
            # Try to find matching FSM location records based on pincode
            if self.partner_id.zip:
                # Find pincode record
                pincode_record = self.env['fsm.pincode'].search([('pincode', '=', self.partner_id.zip)], limit=1)
                if pincode_record:
                    self.fsm_pincode_id = pincode_record.id
                    self.fsm_district_id = pincode_record.district_id.id
                    self.fsm_state_id = pincode_record.state_id.id

            
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Auto-fill model from product"""
        if self.product_id:
            # Clear the model_name field first
            self.model_name = False
            # Auto-fill warranty information from product template
            self.warranty_type = self.product_id.warranty_type
            if self.is_under_warranty():
                self.warranty_status = 'yes'
            else:
                self.warranty_status = 'no'
            # Trigger warranty expiry date computation
            self._compute_warranty_expiry_date()
        else:
            # Clear the model_name field if no product is selected
            self.model_name = False
            # Clear warranty information
            self.warranty_type = 'none'
            self.warranty_status = 'no'
            self.warranty_expiry_date = False
    
    @api.onchange('purchase_date')
    def _onchange_purchase_date(self):
        """Update warranty expiry date when purchase date changes"""
        self._compute_warranty_expiry_date()
        # Also update warranty status based on new purchase date
        if self.product_id:
            if self.is_under_warranty():
                self.warranty_status = 'yes'
            else:
                self.warranty_status = 'no'
    
    def action_update_warranty_expiry(self):
        """Manually update warranty expiry date based on product warranty information"""
        self._compute_warranty_expiry_date()
    
    def action_check_warranty_status(self):
        """Manually check and update warranty status based on purchase date"""
        for record in self:
            if record.product_id and record.purchase_date:
                if record.is_under_warranty():
                    record.warranty_status = 'yes'
                else:
                    record.warranty_status = 'no'
            else:
                record.warranty_status = 'no'
        
    @api.onchange('dealer_id')
    def _onchange_dealer_id(self):
        if self.dealer_id:
            self.dealer_phone = self.dealer_id.phone_number
            technician_ids = self.dealer_id.technician_ids.ids
            if technician_ids:
                self.technician_id = technician_ids[0]  # Auto-assign first technician

    
    @api.onchange('technician_id')
    def _onchange_technician_id(self):
        """Auto-fill service partner from technician"""
        if self.technician_id and self.technician_id.service_partner_id:
            self.service_partner_id = self.technician_id.service_partner_id.id
        else:
            self.service_partner_id = False
    def _compute_warranty_expiry_date(self):
        """Compute warranty expiry date based on purchase date and warranty duration"""
        for record in self:
            if record.product_id and record.purchase_date and record.product_id.warranty_duration and record.product_id.warranty_type != 'none':
                record.warranty_expiry_date = record.purchase_date + timedelta(days=record.product_id.warranty_duration)
            else:
                record.warranty_expiry_date = False
    
    def is_under_warranty(self):
        """Check if the product is under warranty based on purchase date and warranty duration"""
        self.ensure_one()
        if not self.product_id or not self.purchase_date:
            return False
        
        # If no warranty type or no duration, it's not under warranty
        if self.product_id.warranty_type == 'none' or not self.product_id.warranty_duration:
            return False
        
        # Calculate expiry date
        expiry_date = self.purchase_date + timedelta(days=self.product_id.warranty_duration)
        
        # Check if current date is before or equal to expiry date
        return fields.Date.today() <= expiry_date
    
    def action_view_spare_requests(self):
        """View related spare requests"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Spare Requests',
            'res_model': 'fsm.spare.request',
            'view_mode': 'tree,form',
            'domain': [('call_id', '=', self.id)],
            'context': {'default_call_id': self.id}
        }

    def action_open_assign_wizard(self):
        """Open technician assignment wizard"""
        self.ensure_one()
        return {
            'name': 'Assign Technician',
            'type': 'ir.actions.act_window',
            'res_model': 'fsm.technician.assignment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_call_id': self.id}
        }

    def action_close_with_otp(self):
        """Open OTP verification wizard to close the service call"""
        self.ensure_one()
        return {
            'name': 'Close Service Call',
            'type': 'ir.actions.act_window',
            'res_model': 'fsm.close.call.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_call_id': self.id}
        }


class FSMCallTag(models.Model):
    _name = 'fsm.call.tag'
    _description = 'Service Call Tag'
    _order = 'name'
    
    name = fields.Char(string='Tag Name', required=True)
    color = fields.Integer(string='Color')
    active = fields.Boolean(default=True)
    
    _sql_constraints = [
        ('unique_tag_name', 'UNIQUE(name)', 'Tag name must be unique!')
    ]