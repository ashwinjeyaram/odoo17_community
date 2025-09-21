# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, date, timedelta

class FSMDashboard(models.Model):
    _name = 'fsm.dashboard'
    _description = 'Field Service Dashboard'
    _auto = False  # Don't create database table
    _order = 'id'
    
    # Today's Statistics
    total_calls_today = fields.Integer(string='Total Calls Today', compute='_compute_today_stats')
    pending_calls_today = fields.Integer(string='Pending Calls Today', compute='_compute_today_stats')
    completed_calls_today = fields.Integer(string='Completed Calls Today', compute='_compute_today_stats')
    cancelled_calls_today = fields.Integer(string='Cancelled Calls Today', compute='_compute_today_stats')
    
    # Technician Status
    available_technicians = fields.Integer(string='Available Technicians', compute='_compute_technician_stats')
    busy_technicians = fields.Integer(string='Busy Technicians', compute='_compute_technician_stats')
    offline_technicians = fields.Integer(string='Offline Technicians', compute='_compute_technician_stats')
    total_technicians = fields.Integer(string='Total Technicians', compute='_compute_technician_stats')
    
    # Service Calls Overview
    pending_calls = fields.Integer(string='Pending Calls', compute='_compute_call_stats')
    assigned_calls = fields.Integer(string='Assigned Calls', compute='_compute_call_stats')
    in_progress_calls = fields.Integer(string='In Progress Calls', compute='_compute_call_stats')
    completed_calls = fields.Integer(string='Completed Calls', compute='_compute_call_stats')
    
    # Priority Analysis
    urgent_calls = fields.Integer(string='Urgent Calls', compute='_compute_priority_stats')
    high_priority_calls = fields.Integer(string='High Priority Calls', compute='_compute_priority_stats')
    normal_calls = fields.Integer(string='Normal Calls', compute='_compute_priority_stats')
    low_calls = fields.Integer(string='Low Priority Calls', compute='_compute_priority_stats')
    
    # Performance Metrics
    avg_response_time = fields.Float(string='Avg Response Time (Hours)', compute='_compute_performance_metrics')
    avg_resolution_time = fields.Float(string='Avg Resolution Time (Hours)', compute='_compute_performance_metrics')
    first_call_resolution_rate = fields.Float(string='First Call Resolution Rate', compute='_compute_performance_metrics')
    sla_success_rate = fields.Float(string='SLA Success Rate', compute='_compute_performance_metrics')
    calls_within_sla = fields.Integer(string='Calls Within SLA', compute='_compute_performance_metrics')
    calls_breached_sla = fields.Integer(string='Calls Breached SLA', compute='_compute_performance_metrics')
    
    
    # Related fields
    technician_performance_ids = fields.One2many('fsm.technician', 'id', string='Technician Performance', compute='_compute_technician_performance')
    area_performance_ids = fields.One2many('fsm.technician.pincode', 'id', string='Area Performance', compute='_compute_area_performance')
    recent_call_ids = fields.One2many('fsm.call', 'id', string='Recent Calls', compute='_compute_recent_calls')
    
    @api.depends()
    def _compute_today_stats(self):
        for record in self:
            today = fields.Date.today()
            calls_today = self.env['fsm.call'].search([
                ('create_date', '>=', datetime.combine(today, datetime.min.time())),
                ('create_date', '<=', datetime.combine(today, datetime.max.time()))
            ])
            record.total_calls_today = len(calls_today)
            record.pending_calls_today = len(calls_today.filtered(lambda c: c.state == 'draft'))
            record.completed_calls_today = len(calls_today.filtered(lambda c: c.state == 'done'))
            record.cancelled_calls_today = len(calls_today.filtered(lambda c: c.state == 'cancelled'))
    
    @api.depends()
    def _compute_technician_stats(self):
        for record in self:
            technicians = self.env['fsm.technician'].search([])
            record.total_technicians = len(technicians)
            record.available_technicians = len(technicians.filtered(lambda t: t.state == 'available'))
            record.busy_technicians = len(technicians.filtered(lambda t: t.state == 'busy'))
            record.offline_technicians = len(technicians.filtered(lambda t: t.state == 'offline'))
    
    @api.depends()
    def _compute_call_stats(self):
        for record in self:
            calls = self.env['fsm.call'].search([])
            record.pending_calls = len(calls.filtered(lambda c: c.state == 'draft'))
            record.assigned_calls = len(calls.filtered(lambda c: c.state == 'assigned'))
            record.in_progress_calls = len(calls.filtered(lambda c: c.state == 'in_progress'))
            record.completed_calls = len(calls.filtered(lambda c: c.state == 'done'))
    
    @api.depends()
    def _compute_priority_stats(self):
        for record in self:
            calls = self.env['fsm.call'].search([('state', 'not in', ['done', 'cancelled'])])
            record.urgent_calls = len(calls.filtered(lambda c: c.priority == '3'))
            record.high_priority_calls = len(calls.filtered(lambda c: c.priority == '2'))
            record.normal_calls = len(calls.filtered(lambda c: c.priority == '1'))
            record.low_calls = len(calls.filtered(lambda c: c.priority == '0'))
    
    @api.depends()
    def _compute_performance_metrics(self):
        for record in self:
            # These are placeholder calculations - implement actual logic as needed
            record.avg_response_time = 2.5
            record.avg_resolution_time = 24.0
            record.first_call_resolution_rate = 0.75
            record.sla_success_rate = 0.85
            record.calls_within_sla = 85
            record.calls_breached_sla = 15
    
    @api.depends()
    def _compute_technician_performance(self):
        for record in self:
            record.technician_performance_ids = self.env['fsm.technician'].search([], limit=10)
    
    @api.depends()
    def _compute_area_performance(self):
        for record in self:
            record.area_performance_ids = self.env['fsm.technician.pincode'].search([], limit=10)
    
    @api.depends()
    def _compute_recent_calls(self):
        for record in self:
            record.recent_call_ids = self.env['fsm.call'].search([], limit=20, order='create_date desc')
    
    def action_view_pending_calls(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Pending Calls',
            'res_model': 'fsm.call',
            'view_mode': 'tree,form',
            'domain': [('state', '=', 'draft')],
        }
    
    def action_view_assigned_calls(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Assigned Calls',
            'res_model': 'fsm.call',
            'view_mode': 'tree,form',
            'domain': [('state', '=', 'assigned')],
        }
    
    def action_view_in_progress_calls(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'In Progress Calls',
            'res_model': 'fsm.call',
            'view_mode': 'tree,form',
            'domain': [('state', '=', 'in_progress')],
        }
    
    def action_view_completed_calls(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Completed Calls',
            'res_model': 'fsm.call',
            'view_mode': 'tree,form',
            'domain': [('state', '=', 'done')],
        }
    
    def action_view_urgent_calls(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Urgent Calls',
            'res_model': 'fsm.call',
            'view_mode': 'tree,form',
            'domain': [('priority', '=', '3'), ('state', 'not in', ['done', 'cancelled'])],
        }
    
    def action_view_high_priority_calls(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'High Priority Calls',
            'res_model': 'fsm.call',
            'view_mode': 'tree,form',
            'domain': [('priority', '=', '2'), ('state', 'not in', ['done', 'cancelled'])],
        }
    
    def action_view_normal_calls(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Normal Priority Calls',
            'res_model': 'fsm.call',
            'view_mode': 'tree,form',
            'domain': [('priority', '=', '1'), ('state', 'not in', ['done', 'cancelled'])],
        }
    
    def action_view_low_calls(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Low Priority Calls',
            'res_model': 'fsm.call',
            'view_mode': 'tree,form',
            'domain': [('priority', '=', '0'), ('state', 'not in', ['done', 'cancelled'])],
        }
    
    def action_refresh_dashboard(self):
        # Simply reload the form
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'fsm.dashboard',
            'view_mode': 'form',
            'target': 'main',
        }