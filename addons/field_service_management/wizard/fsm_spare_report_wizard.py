# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class FSMSpareReportWizard(models.TransientModel):
    _name = 'fsm.spare.report.wizard'
    _description = 'Spare Request Report Wizard'

    # Date filters
    date_from = fields.Date(string='Start Date', required=True, default=fields.Date.today())
    date_to = fields.Date(string='End Date', required=True, default=fields.Date.today())

    # Additional filters
    technician_ids = fields.Many2many('fsm.technician', string='Technicians')
    spare_ids = fields.Many2many('fsm.spare', string='Spare Parts')
    state_filter = fields.Selection([
        ('all', 'All Status'),
        ('draft', 'Draft'),
        ('requested', 'Requested'),
        ('approved', 'Approved'),
        ('issued', 'Issued'),
        ('received', 'Received'),
        ('returned', 'Returned'),
        ('cancelled', 'Cancelled')
    ], string='Status Filter', default='all')

    call_ids = fields.Many2many('fsm.call', string='Service Calls')
    partner_ids = fields.Many2many('res.partner', string='Customers')

    # Report options
    group_by = fields.Selection([
        ('technician', 'Group by Technician'),
        ('date', 'Group by Date'),
        ('status', 'Group by Status'),
        ('call', 'Group by Service Call'),
        ('spare', 'Group by Spare Part')
    ], string='Group By', default='technician')

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from > record.date_to:
                raise ValidationError('Start date cannot be later than end date!')

    def action_print_report(self):
        """Generate PDF report"""
        # Build domain for filtering
        domain = [
            ('request_date', '>=', self.date_from),
            ('request_date', '<=', self.date_to)
        ]

        # Add filters based on wizard fields
        if self.technician_ids:
            domain.append(('technician_id', 'in', self.technician_ids.ids))

        if self.spare_ids:
            domain.append(('spare_line_ids.spare_id', 'in', self.spare_ids.ids))

        if self.state_filter != 'all':
            domain.append(('state', '=', self.state_filter))

        if self.call_ids:
            domain.append(('call_id', 'in', self.call_ids.ids))

        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))

        # Get filtered records
        spare_requests = self.env['fsm.spare.request'].search(domain, order='request_date desc')

        if not spare_requests:
            raise ValidationError('No spare requests found for the selected criteria!')

        # Prepare data for report
        data = {
            'wizard_id': self.id,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'technician_ids': self.technician_ids.ids,
            'spare_ids': self.spare_ids.ids,
            'state_filter': self.state_filter,
            'call_ids': self.call_ids.ids,
            'partner_ids': self.partner_ids.ids,
            'group_by': self.group_by,
            'request_ids': spare_requests.ids
        }

        return self.env.ref('field_service_management.action_report_spare_request').report_action(self, data=data)