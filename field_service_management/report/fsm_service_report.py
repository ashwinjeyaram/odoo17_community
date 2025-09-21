# -*- coding: utf-8 -*-
from odoo import models, fields, api,tools

class FSMServiceReport(models.Model):
    _name = 'fsm.service.report'
    _description = 'Service Report'
    _auto = False
    _order = 'call_date desc'
    
    # Dimensions
    call_id = fields.Many2one('fsm.call', string='Service Call', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    technician_id = fields.Many2one('fsm.technician', string='Technician', readonly=True)
    service_partner_id = fields.Many2one('fsm.service.partner', string='Service Partner', readonly=True)
    
    # Dates
    call_date = fields.Datetime(string='Call Date', readonly=True)
    closed_date = fields.Datetime(string='Closed Date', readonly=True)
    
    # Measures
    call_count = fields.Integer(string='Call Count', readonly=True)
    resolution_time = fields.Float(string='Resolution Time (Hours)', readonly=True)
    total_charge = fields.Monetary(string='Total Charge', readonly=True)
    
    # Other fields
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
    ], string='Status', readonly=True)
    
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Urgent')
    ], string='Priority', readonly=True)
    
    pincode = fields.Char(string='Pincode', readonly=True)
    warranty_status = fields.Selection([
        ('yes', 'Under Warranty'),
        ('no', 'Out of Warranty'),
        ('stock_set', 'Stock Set'),
        ('extended', 'Extended Warranty')
    ], string='Warranty Status', readonly=True)
    
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    
    def init(self):
        """Initialize the SQL view for the report"""
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    row_number() OVER () AS id,
                    c.id as call_id,
                    c.partner_id,
                    c.technician_id,
                    c.service_partner_id,
                    c.call_date,
                    c.closed_date,
                    1 as call_count,
                    c.resolution_time,
                    c.total_charge,
                    c.state,
                    c.priority,
                    c.pincode,
                    c.warranty_status,
                    c.company_id
                FROM
                    fsm_call c
                WHERE
                    c.active = True
            )
        """ % self._table)