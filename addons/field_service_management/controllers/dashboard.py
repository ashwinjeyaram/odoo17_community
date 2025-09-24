# -*- coding: utf-8 -*-
import json 
from odoo import http, fields
from odoo.http import request
from datetime import datetime, date


class FSMDashboardController(http.Controller):

    @http.route('/fsm/dashboard/data', type='json', auth='user')
    def get_dashboard_data(self):
        """Get all dashboard KPI data"""
        try:
            # Unassigned Calls Data - Fix states based on actual model
            unassigned_calls = request.env['fsm.call'].search([
                ('state', 'in', ['draft', 'confirmed']),
                ('technician_id', '=', False)
            ])

            today = fields.Date.today()
            today_calls = unassigned_calls.filtered(lambda c: c.create_date.date() == today)
            overdue_calls = unassigned_calls.filtered(lambda c: c.sla_deadline and c.sla_deadline < fields.Datetime.now())

            # Spare Requests Data - Fix model name and states
            spare_requests = request.env['fsm.spare.request'].search([])

            # Since there's no is_urgent field, let's use priority from related call or request_date
            # Calculate urgent requests as those requested today or with high priority calls
            urgent_spare_requests = spare_requests.filtered(lambda r:
                r.request_date.date() == today or
                (r.call_id and r.call_id.priority == '3')
            )

            # Customer Feedback Data - Fix completed state name
            feedback_records = request.env['fsm.feedback'].search([])
            completed_calls = request.env['fsm.call'].search([('state', 'in', ['resolved', 'closed'])])  # Fix state names
            calls_with_feedback = feedback_records.mapped('call_id')
            pending_feedback_calls = completed_calls.filtered(lambda c: c.id not in calls_with_feedback.ids)

            # Calculate average rating - handle string ratings properly
            avg_rating = 0.0
            if feedback_records:
                ratings = [int(f.rating) for f in feedback_records if f.rating and f.rating.isdigit()]
                avg_rating = sum(ratings) / len(ratings) if ratings else 0.0

            return {
                'success': True,
                'data': {
                    # Unassigned Calls
                    'total_unassigned_calls': len(unassigned_calls),
                    'urgent_unassigned_calls': len(unassigned_calls.filtered(lambda c: c.priority == '3')),
                    'today_unassigned_calls': len(today_calls),
                    'overdue_unassigned_calls': len(overdue_calls),

                    # Spare Requests
                    'total_spare_requests': len(spare_requests),
                    'pending_spare_requests': len(spare_requests.filtered(lambda r: r.state in ['draft', 'requested'])),
                    'approved_spare_requests': len(spare_requests.filtered(lambda r: r.state == 'approved')),
                    'urgent_spare_requests': len(urgent_spare_requests),

                    # Customer Feedback
                    'total_customer_feedback': len(feedback_records),
                    'excellent_feedback': len(feedback_records.filtered(lambda f: f.rating == '5')),
                    'good_feedback': len(feedback_records.filtered(lambda f: f.rating in ['3', '4'])),
                    'poor_feedback': len(feedback_records.filtered(lambda f: f.rating in ['1', '2'])),
                    'pending_feedback': len(pending_feedback_calls),
                    'avg_feedback_rating': round(avg_rating, 1),
                }
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/fsm/dashboard/unassigned_calls', type='json', auth='user')
    def get_unassigned_calls(self):
        """Open unassigned calls view"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Unassigned Service Calls',
            'res_model': 'fsm.call',
            'view_mode': 'tree,form',
            'views': [[False, 'tree'], [False, 'form']],
            'domain': [('state', 'in', ['draft', 'confirmed']), ('technician_id', '=', False)],
            'context': {'create': False},
            'target': 'current',
        }

    @http.route('/fsm/dashboard/urgent_unassigned_calls', type='json', auth='user')
    def get_urgent_unassigned_calls(self):
        """Open urgent unassigned calls view"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Urgent Unassigned Calls',
            'res_model': 'fsm.call',
            'view_mode': 'tree,form',
            'views': [[False, 'tree'], [False, 'form']],
            'domain': [('state', 'in', ['draft', 'confirmed']), ('technician_id', '=', False), ('priority', '=', '3')],
            'context': {'create': False},
            'target': 'current',
        }

    @http.route('/fsm/dashboard/overdue_unassigned_calls', type='json', auth='user')
    def get_overdue_unassigned_calls(self):
        """Open overdue unassigned calls view"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Overdue Unassigned Calls',
            'res_model': 'fsm.call',
            'view_mode': 'tree,form',
            'views': [[False, 'tree'], [False, 'form']],
            'domain': [
                ('state', 'in', ['draft', 'confirmed']),
                ('technician_id', '=', False),
                ('sla_deadline', '<', fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            ],
            'context': {'create': False},
            'target': 'current',
        }

    @http.route('/fsm/dashboard/spare_requests', type='json', auth='user')
    def get_spare_requests(self):
        """Open spare requests view"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'All Spare Requests',
            'res_model': 'fsm.spare.request',
            'view_mode': 'tree,form',
            'views': [[False, 'tree'], [False, 'form']],
            'domain': [],
            'context': {'create': False},
            'target': 'current',
        }

    @http.route('/fsm/dashboard/pending_spare_requests', type='json', auth='user')
    def get_pending_spare_requests(self):
        """Open pending spare requests view"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Pending Spare Requests',
            'res_model': 'fsm.spare.request',
            'view_mode': 'tree,form',
            'views': [[False, 'tree'], [False, 'form']],
            'domain': [('state', 'in', ['draft', 'requested'])],
            'context': {'create': False},
            'target': 'current',
        }

    @http.route('/fsm/dashboard/urgent_spare_requests', type='json', auth='user')
    def get_urgent_spare_requests(self):
        """Open urgent spare requests view"""
        today = fields.Date.today()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Urgent Spare Requests',
            'res_model': 'fsm.spare.request',
            'view_mode': 'tree,form',
            'views': [[False, 'tree'], [False, 'form']],
            'domain': ['|',
                       ('request_date', '>=', today.strftime('%Y-%m-%d')),
                       ('call_id.priority', '=', '3')],
            'context': {'create': False},
            'target': 'current',
        }

    @http.route('/fsm/dashboard/customer_feedback', type='json', auth='user')
    def get_customer_feedback(self):
        """Open customer feedback view"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'All Customer Feedback',
            'res_model': 'fsm.feedback',
            'view_mode': 'tree,form',
            'views': [[False, 'tree'], [False, 'form']],
            'domain': [],
            'context': {'create': False},
            'target': 'current',
        }

    @http.route('/fsm/dashboard/excellent_feedback', type='json', auth='user')
    def get_excellent_feedback(self):
        """Open excellent feedback view"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Excellent Feedback',
            'res_model': 'fsm.feedback',
            'view_mode': 'tree,form',
            'views': [[False, 'tree'], [False, 'form']],
            'domain': [('rating', '=', '5')],
            'context': {'create': False},
            'target': 'current',
        }

    @http.route('/fsm/dashboard/poor_feedback', type='json', auth='user')
    def get_poor_feedback(self):
        """Open poor feedback view"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Poor Feedback',
            'res_model': 'fsm.feedback',
            'view_mode': 'tree,form',
            'views': [[False, 'tree'], [False, 'form']],
            'domain': [('rating', 'in', ['1', '2'])],
            'context': {'create': False},
            'target': 'current',
        }

    @http.route('/fsm/dashboard/pending_feedback', type='json', auth='user')
    def get_pending_feedback(self):
        """Open pending feedback view"""
        feedback_records = request.env['fsm.feedback'].search([])
        calls_with_feedback = feedback_records.mapped('call_id')
        completed_calls = request.env['fsm.call'].search([('state', 'in', ['resolved', 'closed'])])
        pending_call_ids = completed_calls.filtered(lambda c: c.id not in calls_with_feedback.ids).ids

        return {
            'type': 'ir.actions.act_window',
            'name': 'Calls Pending Feedback',
            'res_model': 'fsm.call',
            'view_mode': 'tree,form',
            'views': [[False, 'tree'], [False, 'form']],
            'domain': [('id', 'in', pending_call_ids)],
            'context': {'create': False},
            'target': 'current',
        }