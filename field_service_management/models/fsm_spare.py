# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class FSMSpare(models.Model):
    _name = 'fsm.spare'
    _description = 'Spare Part'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'create_date desc'
    
    name = fields.Char(string='Part Name', required=True, tracking=True)
    code = fields.Char(string='Part Code', required=True, tracking=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    
    # Classification
    category_id = fields.Many2one('fsm.spare.category', string='Category')
    brand = fields.Char(string='Brand')
    model_compatibility = fields.Text(string='Compatible Models')
    
    # Stock Information
    qty_available = fields.Float(string='Quantity Available', compute='_compute_qty_available', store=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', related='product_id.uom_id', readonly=True)
    min_stock_qty = fields.Float(string='Minimum Stock Quantity', default=1.0)
    reorder_qty = fields.Float(string='Reorder Quantity', default=10.0)
    
    # Pricing
    list_price = fields.Monetary(string='Sale Price', readonly=False)
    standard_price = fields.Monetary(string='Cost' , readonly=False)
    currency_id = fields.Many2one('res.currency', readonly=True)
    
    # Warranty
    warranty_type = fields.Selection([
        ('none', 'No Warranty'),
        ('limited', 'Limited Warranty'),
        ('full', 'Full Warranty')
    ], default='none', string='Warranty Type')
    warranty_duration = fields.Integer(string='Warranty Duration (Days)')
    
    # Location
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    location_id = fields.Many2one('stock.location', string='Stock Location')
    
    # Statistics
    request_count = fields.Integer(string='Request Count', compute='_compute_statistics', store=True)
    return_count = fields.Integer(string='Return Count', compute='_compute_statistics', store=True)
    defect_rate = fields.Float(string='Defect Rate (%)', compute='_compute_statistics', store=True)
    
    # Relations
    spare_request_line_ids = fields.One2many('fsm.spare.request.line', 'spare_id', string='Request Lines')
    
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    
    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Part code must be unique!'),
        ('unique_product', 'UNIQUE(product_id)', 'This product is already linked to another spare part!')
    ]
    
    @api.depends('product_id', 'location_id')
    def _compute_qty_available(self):
        for record in self:
            if record.product_id and record.location_id:
                quants = self.env['stock.quant'].search([
                    ('product_id', '=', record.product_id.id),
                    ('location_id', '=', record.location_id.id)
                ])
                record.qty_available = sum(quants.mapped('quantity'))
            else:
                record.qty_available = 0.0
    
    @api.depends('spare_request_line_ids', 'spare_request_line_ids.is_returned', 'spare_request_line_ids.is_defective')
    def _compute_statistics(self):
        for record in self:
            request_lines = record.spare_request_line_ids
            record.request_count = len(request_lines)
            record.return_count = len(request_lines.filtered('is_returned'))
            
            if record.request_count > 0:
                defective_count = len(request_lines.filtered('is_defective'))
                record.defect_rate = (defective_count / record.request_count) * 100
            else:
                record.defect_rate = 0.0
    
    @api.constrains('min_stock_qty', 'reorder_qty')
    def _check_stock_quantities(self):
        for record in self:
            if record.min_stock_qty < 0:
                raise ValidationError('Minimum stock quantity cannot be negative!')
            if record.reorder_qty <= 0:
                raise ValidationError('Reorder quantity must be positive!')
            if record.reorder_qty <= record.min_stock_qty:
                raise ValidationError('Reorder quantity must be greater than minimum stock quantity!')
    
    def action_check_stock(self):
        """Check stock and create purchase order if needed"""
        for record in self:
            if record.qty_available < record.min_stock_qty:
                # Create purchase order or alert
                self.message_post(
                    body=f"Stock level ({record.qty_available}) is below minimum ({record.min_stock_qty}). Reorder required.",
                    subject="Low Stock Alert"
                )
                # TODO: Create automatic purchase order
    
    @api.model
    def check_all_stock_levels(self):
        """Cron job to check stock levels for all spare parts"""
        low_stock_spares = self.search([])
        for spare in low_stock_spares:
            if spare.qty_available < spare.min_stock_qty:
                spare.action_check_stock()


class FSMSpareCategory(models.Model):
    _name = 'fsm.spare.category'
    _description = 'Spare Part Category'
    _parent_name = 'parent_id'
    _parent_store = True
    _rec_name = 'complete_name'
    _order = 'complete_name'
    
    name = fields.Char(string='Category Name', required=True)
    complete_name = fields.Char(string='Complete Name', compute='_compute_complete_name', store=True)
    parent_id = fields.Many2one('fsm.spare.category', string='Parent Category', index=True, ondelete='cascade')
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many('fsm.spare.category', 'parent_id', string='Child Categories')
    spare_ids = fields.One2many('fsm.spare', 'category_id', string='Spare Parts')
    spare_count = fields.Integer(string='Spare Count', compute='_compute_spare_count')
    active = fields.Boolean(default=True)
    
    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for category in self:
            if category.parent_id:
                category.complete_name = f'{category.parent_id.complete_name} / {category.name}'
            else:
                category.complete_name = category.name
    
    @api.depends('spare_ids')
    def _compute_spare_count(self):
        for record in self:
            record.spare_count = len(record.spare_ids)
    
    @api.constrains('parent_id')
    def _check_category_recursion(self):
        if not self._check_recursion():
            raise ValidationError('You cannot create recursive categories!')
    
    def name_get(self):
        return [(category.id, category.complete_name) for category in self]


class FSMSpareRequest(models.Model):
    _name = 'fsm.spare.request'
    _description = 'Spare Parts Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'create_date desc'
    
    name = fields.Char(string='Request Number', readonly=True, copy=False, default='New')
    call_id = fields.Many2one('fsm.call', string='Service Call', required=True, tracking=True)
    technician_id = fields.Many2one('fsm.technician', string='Technician', related='call_id.technician_id', store=True, readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', related='call_id.partner_id', store=True, readonly=True)
    
    # Request Lines
    spare_line_ids = fields.One2many('fsm.spare.request.line', 'request_id', string='Spare Parts')
    
    # Dates
    request_date = fields.Datetime(string='Request Date', default=fields.Datetime.now, required=True)
    approved_date = fields.Datetime(string='Approved Date')
    issued_date = fields.Datetime(string='Issued Date')
    received_date = fields.Datetime(string='Received Date')
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('requested', 'Requested'),
        ('approved', 'Approved'),
        ('issued', 'Issued'),
        ('received', 'Received'),
        ('returned', 'Returned'),
        ('cancelled', 'Cancelled')
    ], default='draft', string='Status', tracking=True)
    
    # Approval
    approved_by = fields.Many2one('res.users', string='Approved By')
    rejection_reason = fields.Text(string='Rejection Reason')
    
    # Notes
    notes = fields.Text(string='Notes')
    
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('fsm.spare.request') or 'New'
        return super(FSMSpareRequest, self).create(vals)
    
    def action_request(self):
        self.ensure_one()
        if not self.spare_line_ids:
            raise ValidationError('Please add at least one spare part to request!')
        old_state = self.state
        self.state = 'requested'
        
        # Check stock availability
        for line in self.spare_line_ids:
            if line.spare_id.qty_available < line.quantity:
                self.message_post(
                    body=f"Low stock alert: {line.spare_id.name} - Available: {line.spare_id.qty_available}, Requested: {line.quantity}"
                )
        
        # Create notification transaction
        self.env['fsm.notification.transaction'].create({
            'spare_request_id': self.id,
            'call_id': self.call_id.id if self.call_id else False,
            'technician_id': self.technician_id.id if self.technician_id else False,
            'notification_type': 'spare_requested',
            'old_status': old_state,
            'new_status': 'requested',
            'description': f'Spare request {self.name} created for call {self.call_id.name if self.call_id else ""}'
        })
    
    def action_approve(self):
        self.ensure_one()
        old_state = self.state
        self.write({
            'state': 'approved',
            'approved_date': fields.Datetime.now(),
            'approved_by': self.env.user.id
        })
        
        # Create notification transaction
        self.env['fsm.notification.transaction'].create({
            'spare_request_id': self.id,
            'call_id': self.call_id.id if self.call_id else False,
            'technician_id': self.technician_id.id if self.technician_id else False,
            'notification_type': 'spare_approved',
            'old_status': old_state,
            'new_status': 'approved',
            'description': f'Spare request {self.name} approved'
        })
    
    def action_issue(self):
        self.ensure_one()
        old_state = self.state
        # TODO: Create stock picking
        self.write({
            'state': 'issued',
            'issued_date': fields.Datetime.now()
        })
        
        # Create notification transaction
        self.env['fsm.notification.transaction'].create({
            'spare_request_id': self.id,
            'call_id': self.call_id.id if self.call_id else False,
            'technician_id': self.technician_id.id if self.technician_id else False,
            'notification_type': 'spare_issued',
            'old_status': old_state,
            'new_status': 'issued',
            'description': f'Spare request {self.name} issued'
        })
    
    def action_receive(self):
        self.ensure_one()
        old_state = self.state
        self.write({
            'state': 'received',
            'received_date': fields.Datetime.now()
        })
        
        # Create notification transaction
        self.env['fsm.notification.transaction'].create({
            'spare_request_id': self.id,
            'call_id': self.call_id.id if self.call_id else False,
            'technician_id': self.technician_id.id if self.technician_id else False,
            'notification_type': 'spare_received',
            'old_status': old_state,
            'new_status': 'received',
            'description': f'Spare request {self.name} received'
        })
    
    def action_cancel(self):
        self.ensure_one()
        old_state = self.state
        self.state = 'cancelled'
        
        # Create notification transaction
        self.env['fsm.notification.transaction'].create({
            'spare_request_id': self.id,
            'call_id': self.call_id.id if self.call_id else False,
            'technician_id': self.technician_id.id if self.technician_id else False,
            'notification_type': 'status_changed',
            'old_status': old_state,
            'new_status': 'cancelled',
            'description': f'Spare request {self.name} cancelled'
        })


class FSMSpareRequestLine(models.Model):
    _name = 'fsm.spare.request.line'
    _description = 'Spare Request Line'
    _rec_name = 'spare_id'
    
    request_id = fields.Many2one('fsm.spare.request', string='Request', required=True, ondelete='cascade')
    spare_id = fields.Many2one('fsm.spare', string='Spare Part', required=True)
    product_id = fields.Many2one('product.product', related='spare_id.product_id', readonly=True)
    
    quantity = fields.Float(string='Quantity', default=1.0, required=True)
    uom_id = fields.Many2one('uom.uom', related='spare_id.uom_id', readonly=True)
    
    # Pricing
    unit_price = fields.Monetary(string='Unit Price', related='spare_id.list_price', readonly=True)
    subtotal = fields.Monetary(string='Subtotal', compute='_compute_subtotal', store=True)
    currency_id = fields.Many2one('res.currency', related='spare_id.currency_id', readonly=True)
    
    # Return Information
    is_returned = fields.Boolean(string='Returned', default=False)
    return_date = fields.Datetime(string='Return Date')
    is_defective = fields.Boolean(string='Defective', default=False)
    return_reason = fields.Text(string='Return Reason')
    
    @api.depends('quantity', 'unit_price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.unit_price
    
    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError('Quantity must be positive!')
    
    def action_return(self):
        self.write({
            'is_returned': True,
            'return_date': fields.Datetime.now()
        })