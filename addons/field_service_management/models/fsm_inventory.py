# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError

class FSMInventory(models.Model):
    _name = 'fsm.inventory'
    _description = 'FSM Inventory Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'create_date desc'
    
    name = fields.Char(string='Reference', readonly=True, copy=False, default='New')
    
    # Type of Movement
    movement_type = fields.Selection([
        ('inward', 'Material Inward'),
        ('outward', 'Material Outward'),
        ('return', 'Return to Warehouse'),
        ('transfer', 'Internal Transfer'),
        ('adjustment', 'Stock Adjustment')
    ], string='Movement Type', required=True, tracking=True)
    
    # Source and Destination
    source_location_id = fields.Many2one('stock.location', string='Source Location')
    dest_location_id = fields.Many2one('stock.location', string='Destination Location')
    
    # Related Records
    technician_id = fields.Many2one('fsm.technician', string='Technician')
    service_partner_id = fields.Many2one('fsm.service.partner', string='Service Partner')
    call_id = fields.Many2one('fsm.call', string='Service Call')
    spare_request_id = fields.Many2one('fsm.spare.request', string='Spare Request')
    
    # Movement Lines
    line_ids = fields.One2many('fsm.inventory.line', 'inventory_id', string='Movement Lines')
    
    # Dates
    movement_date = fields.Datetime(string='Movement Date', default=fields.Datetime.now, required=True)
    scheduled_date = fields.Datetime(string='Scheduled Date')
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('in_transit', 'In Transit'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')
    ], default='draft', string='Status', tracking=True)
    
    # Additional Information
    reference = fields.Char(string='External Reference')
    notes = fields.Text(string='Notes')
    
    # Stock Picking Reference
    picking_id = fields.Many2one('stock.picking', string='Stock Picking')
    
    # Statistics
    total_quantity = fields.Float(string='Total Quantity', compute='_compute_totals', store=True)
    total_value = fields.Monetary(string='Total Value', compute='_compute_totals', store=True)
    
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            sequence_code = f"fsm.inventory.{vals.get('movement_type', 'general')}"
            vals['name'] = self.env['ir.sequence'].next_by_code(sequence_code) or \
                          self.env['ir.sequence'].next_by_code('fsm.inventory') or 'New'
        return super(FSMInventory, self).create(vals)
    
    @api.depends('line_ids.quantity', 'line_ids.unit_value')
    def _compute_totals(self):
        for record in self:
            record.total_quantity = sum(record.line_ids.mapped('quantity'))
            record.total_value = sum(record.line_ids.mapped('total_value'))
    
    @api.onchange('movement_type')
    def _onchange_movement_type(self):
        """Set default locations based on movement type"""
        if self.movement_type == 'inward':
            # Supplier to Stock
            self.source_location_id = self.env.ref('stock.stock_location_suppliers', False)
            self.dest_location_id = self.env.ref('stock.stock_location_stock', False)
        elif self.movement_type == 'outward':
            # Stock to Customer
            self.source_location_id = self.env.ref('stock.stock_location_stock', False)
            self.dest_location_id = self.env.ref('stock.stock_location_customers', False)
        elif self.movement_type == 'return':
            # Customer to Stock
            self.source_location_id = self.env.ref('stock.stock_location_customers', False)
            self.dest_location_id = self.env.ref('stock.stock_location_stock', False)
    
    def action_confirm(self):
        self.ensure_one()
        if not self.line_ids:
            raise ValidationError('Please add at least one line item!')
        
        # Validate stock availability for outward movements
        if self.movement_type in ['outward', 'transfer']:
            for line in self.line_ids:
                available_qty = self._get_available_quantity(
                    line.product_id, 
                    self.source_location_id
                )
                if available_qty < line.quantity:
                    raise ValidationError(
                        f"Insufficient stock for {line.product_id.name}. "
                        f"Available: {available_qty}, Required: {line.quantity}"
                    )
        
        self.state = 'confirmed'
        
        # Create stock picking if needed
        self._create_stock_picking()
    
    def action_process(self):
        self.ensure_one()
        if self.state != 'confirmed':
            raise UserError('Only confirmed movements can be processed!')
        
        self.state = 'in_transit'
        
        # Process stock picking
        if self.picking_id:
            self.picking_id.action_confirm()
            self.picking_id.action_assign()
    
    def action_done(self):
        self.ensure_one()
        if self.state not in ['confirmed', 'in_transit']:
            raise UserError('Invalid state for completion!')
        
        # Complete stock picking
        if self.picking_id:
            for move in self.picking_id.move_lines:
                move.quantity_done = move.product_uom_qty
            self.picking_id.button_validate()
        
        self.state = 'done'
        self.message_post(body='Inventory movement completed.')
    
    def action_cancel(self):
        self.ensure_one()
        if self.state == 'done':
            raise UserError('Completed movements cannot be cancelled!')
        
        # Cancel stock picking
        if self.picking_id and self.picking_id.state not in ['done', 'cancel']:
            self.picking_id.action_cancel()
        
        self.state = 'cancelled'
    
    def _get_available_quantity(self, product, location):
        """Get available quantity for a product in a location"""
        quants = self.env['stock.quant'].search([
            ('product_id', '=', product.id),
            ('location_id', '=', location.id)
        ])
        return sum(quants.mapped('quantity'))
    
    def _create_stock_picking(self):
        """Create stock picking for inventory movement"""
        if not self.source_location_id or not self.dest_location_id:
            return
        
        picking_type = self._get_picking_type()
        if not picking_type:
            return
        
        picking_vals = {
            'picking_type_id': picking_type.id,
            'location_id': self.source_location_id.id,
            'location_dest_id': self.dest_location_id.id,
            'scheduled_date': self.scheduled_date or self.movement_date,
            'origin': self.name,
            'partner_id': self.technician_id.partner_id.id if self.technician_id else False,
        }
        
        picking = self.env['stock.picking'].create(picking_vals)
        
        # Create stock moves
        for line in self.line_ids:
            move_vals = {
                'picking_id': picking.id,
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,
                'product_uom': line.product_id.uom_id.id,
                'location_id': self.source_location_id.id,
                'location_dest_id': self.dest_location_id.id,
                'name': line.product_id.name,
            }
            self.env['stock.move'].create(move_vals)
        
        self.picking_id = picking
    
    def _get_picking_type(self):
        """Get appropriate picking type based on movement type"""
        if self.movement_type == 'inward':
            return self.env['stock.picking.type'].search([
                ('code', '=', 'incoming'),
                ('company_id', '=', self.company_id.id)
            ], limit=1)
        elif self.movement_type in ['outward', 'return']:
            return self.env['stock.picking.type'].search([
                ('code', '=', 'outgoing'),
                ('company_id', '=', self.company_id.id)
            ], limit=1)
        elif self.movement_type == 'transfer':
            return self.env['stock.picking.type'].search([
                ('code', '=', 'internal'),
                ('company_id', '=', self.company_id.id)
            ], limit=1)
        return False


class FSMInventoryLine(models.Model):
    _name = 'fsm.inventory.line'
    _description = 'FSM Inventory Line'
    _rec_name = 'product_id'
    
    inventory_id = fields.Many2one('fsm.inventory', string='Inventory', required=True, ondelete='cascade')
    
    # Product Information
    product_id = fields.Many2one('product.product', string='Product', required=True)
    spare_id = fields.Many2one('fsm.spare', string='Spare Part', domain=[('product_id', '!=', False)])
    description = fields.Text(string='Description', readonly=True)
    
    # Quantity and UoM
    quantity = fields.Float(string='Quantity', default=1.0, required=True)
    uom_id = fields.Many2one('uom.uom', string='UoM', related='product_id.uom_id', readonly=True)
    
    # Value
    unit_value = fields.Monetary(string='Unit Value', currency_field='currency_id')
    total_value = fields.Monetary(string='Total Value', compute='_compute_total_value', store=True)
    currency_id = fields.Many2one('res.currency', related='inventory_id.currency_id', readonly=True)
    
    # Tracking
    lot_id = fields.Many2one('stock.production.lot', string='Lot/Serial Number')
    
    # Status
    is_defective = fields.Boolean(string='Defective', default=False)
    defect_description = fields.Text(string='Defect Description')
    
    @api.depends('quantity', 'unit_value')
    def _compute_total_value(self):
        for line in self:
            line.total_value = line.quantity * line.unit_value
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.unit_value = self.product_id.standard_price
            # Try to find corresponding spare
            spare = self.env['fsm.spare'].search([
                ('product_id', '=', self.product_id.id)
            ], limit=1)
            if spare:
                self.spare_id = spare
    
    @api.onchange('spare_id')
    def _onchange_spare_id(self):
        if self.spare_id:
            self.product_id = self.spare_id.product_id
            self.unit_value = self.spare_id.standard_price
    
    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError('Quantity must be positive!')


class FSMStockRequest(models.Model):
    _name = 'fsm.stock.request'
    _description = 'Stock Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'create_date desc'
    
    name = fields.Char(string='Request Number', readonly=True, copy=False, default='New')
    
    # Requester Information
    requested_by = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user, required=True)
    technician_id = fields.Many2one('fsm.technician', string='Technician')
    service_partner_id = fields.Many2one('fsm.service.partner', string='Service Partner')
    
    # Request Details
    request_date = fields.Datetime(string='Request Date', default=fields.Datetime.now, required=True)
    expected_date = fields.Datetime(string='Expected Date')
    urgency = fields.Selection([
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent')
    ], default='normal', string='Urgency')
    
    # Items
    line_ids = fields.One2many('fsm.stock.request.line', 'request_id', string='Requested Items')
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('partially_fulfilled', 'Partially Fulfilled'),
        ('fulfilled', 'Fulfilled'),
        ('cancelled', 'Cancelled')
    ], default='draft', string='Status', tracking=True)
    
    # Approval
    approved_by = fields.Many2one('res.users', string='Approved By')
    approval_date = fields.Datetime(string='Approval Date')
    
    # Notes
    reason = fields.Text(string='Reason for Request', required=True)
    notes = fields.Text(string='Additional Notes')
    
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('fsm.stock.request') or 'New'
        return super(FSMStockRequest, self).create(vals)
    
    def action_submit(self):
        self.ensure_one()
        if not self.line_ids:
            raise ValidationError('Please add at least one item to request!')
        self.state = 'submitted'
        self.message_post(body='Stock request submitted for approval.')
    
    def action_approve(self):
        self.ensure_one()
        self.write({
            'state': 'approved',
            'approved_by': self.env.user.id,
            'approval_date': fields.Datetime.now()
        })
        self.message_post(body='Stock request approved.')
        
        # Create inventory movement
        self._create_inventory_movement()
    
    def action_cancel(self):
        self.ensure_one()
        if self.state in ['fulfilled']:
            raise UserError('Fulfilled requests cannot be cancelled!')
        self.state = 'cancelled'
    
    def _create_inventory_movement(self):
        """Create inventory movement for approved request"""
        inventory_vals = {
            'movement_type': 'outward',
            'technician_id': self.technician_id.id,
            'service_partner_id': self.service_partner_id.id,
            'reference': self.name,
            'notes': self.reason,
        }
        
        inventory = self.env['fsm.inventory'].create(inventory_vals)
        
        # Create inventory lines
        for line in self.line_ids:
            inv_line_vals = {
                'inventory_id': inventory.id,
                'product_id': line.product_id.id,
                'quantity': line.quantity,
                'unit_value': line.product_id.standard_price,
            }
            self.env['fsm.inventory.line'].create(inv_line_vals)
        
        return inventory


class FSMStockRequestLine(models.Model):
    _name = 'fsm.stock.request.line'
    _description = 'Stock Request Line'
    _rec_name = 'product_id'
    
    request_id = fields.Many2one('fsm.stock.request', string='Request', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    spare_id = fields.Many2one('fsm.spare', string='Spare Part')
    
    quantity = fields.Float(string='Requested Quantity', default=1.0, required=True)
    fulfilled_quantity = fields.Float(string='Fulfilled Quantity', default=0.0)
    uom_id = fields.Many2one('uom.uom', string='UoM', related='product_id.uom_id', readonly=True)
    
    notes = fields.Text(string='Notes')
    
    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError('Quantity must be positive!')