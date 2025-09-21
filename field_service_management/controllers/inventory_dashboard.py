# -*- coding: utf-8 -*-
import json
from odoo import http, fields
from odoo.http import request
from datetime import datetime, date, timedelta


class FSMInventoryDashboardController(http.Controller):

    @http.route('/fsm/inventory/dashboard/data', type='json', auth='user')
    def get_inventory_dashboard_data(self):
        """Get all inventory dashboard KPI data"""
        try:
            # Current Stock Levels
            spare_parts = request.env['fsm.spare'].search([('active', '=', True)])

            # Stock movements in last 30 days
            thirty_days_ago = fields.Date.today() - timedelta(days=30)
            stock_moves = request.env['stock.move'].search([
                ('date', '>=', thirty_days_ago),
                ('state', '=', 'done'),
                ('product_id', 'in', spare_parts.mapped('product_id').ids)
            ])

            # Inward movements (receipts, returns)
            inward_moves = stock_moves.filtered(lambda m: m.location_dest_id.usage == 'internal')

            # Outward movements (deliveries, consumptions)
            outward_moves = stock_moves.filtered(lambda m: m.location_id.usage == 'internal')

            # Stock requests
            spare_requests = request.env['fsm.spare.request'].search([])

            # Calculate totals
            total_inward_qty = sum(inward_moves.mapped('product_uom_qty'))
            total_outward_qty = sum(outward_moves.mapped('product_uom_qty'))

            # Low stock items (below minimum stock)
            low_stock_items = spare_parts.filtered(lambda s: s.qty_available < s.min_stock_qty)

            # Out of stock items
            out_of_stock_items = spare_parts.filtered(lambda s: s.qty_available <= 0)

            # Overstock items (above reorder quantity * 2)
            overstock_items = spare_parts.filtered(lambda s: s.qty_available > (s.reorder_qty * 2))

            # Recent stock movements (last 7 days)
            seven_days_ago = fields.Date.today() - timedelta(days=7)
            recent_moves = stock_moves.filtered(lambda m: m.date.date() >= seven_days_ago)

            # Stock value calculation
            total_stock_value = sum(spare.qty_available * spare.standard_price for spare in spare_parts)

            return {
                'success': True,
                'data': {
                    # Stock Overview
                    'total_products': len(spare_parts),
                    'total_stock_value': round(total_stock_value, 2),
                    'low_stock_items': len(low_stock_items),
                    'out_of_stock_items': len(out_of_stock_items),
                    'overstock_items': len(overstock_items),

                    # Stock Movements (Last 30 Days)
                    'total_inward_qty': round(total_inward_qty, 2),
                    'total_outward_qty': round(total_outward_qty, 2),
                    'inward_moves_count': len(inward_moves),
                    'outward_moves_count': len(outward_moves),
                    'recent_moves_count': len(recent_moves),

                    # Stock Requests
                    'total_requests': len(spare_requests),
                    'pending_requests': len(spare_requests.filtered(lambda r: r.state in ['draft', 'requested'])),
                    'approved_requests': len(spare_requests.filtered(lambda r: r.state == 'approved')),
                    'issued_requests': len(spare_requests.filtered(lambda r: r.state == 'issued')),
                    'today_requests': len(spare_requests.filtered(lambda r: r.request_date.date() == fields.Date.today())),

                    # Stock Turnover
                    'stock_turnover_ratio': round(total_outward_qty / (total_stock_value or 1), 4),
                }
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/fsm/inventory/current_stock', type='json', auth='user')
    def get_current_stock(self):
        """Open current stock view"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Current Stock Levels',
            'res_model': 'fsm.spare',
            'view_mode': 'tree,form',
            'views': [[False, 'tree'], [False, 'form']],
            'domain': [('active', '=', True)],
            'context': {'create': False},
            'target': 'current',
        }

    @http.route('/fsm/inventory/low_stock', type='json', auth='user')
    def get_low_stock(self):
        """Open low stock items view"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Low Stock Items',
            'res_model': 'fsm.spare',
            'view_mode': 'tree,form',
            'views': [[False, 'tree'], [False, 'form']],
            'domain': [('active', '=', True), ('qty_available', '<', 'min_stock_qty')],
            'context': {'create': False},
            'target': 'current',
        }

    @http.route('/fsm/inventory/out_of_stock', type='json', auth='user')
    def get_out_of_stock(self):
        """Open out of stock items view"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Out of Stock Items',
            'res_model': 'fsm.spare',
            'view_mode': 'tree,form',
            'views': [[False, 'tree'], [False, 'form']],
            'domain': [('active', '=', True), ('qty_available', '<=', 0)],
            'context': {'create': False},
            'target': 'current',
        }

    @http.route('/fsm/inventory/overstock', type='json', auth='user')
    def get_overstock(self):
        """Open overstock items view"""
        # Get overstock items using computed field logic
        spare_parts = request.env['fsm.spare'].search([('active', '=', True)])
        overstock_ids = []
        for spare in spare_parts:
            if spare.qty_available > (spare.reorder_qty * 2):
                overstock_ids.append(spare.id)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Overstock Items',
            'res_model': 'fsm.spare',
            'view_mode': 'tree,form',
            'views': [[False, 'tree'], [False, 'form']],
            'domain': [('id', 'in', overstock_ids)],
            'context': {'create': False},
            'target': 'current',
        }

    @http.route('/fsm/inventory/inward_movements', type='json', auth='user')
    def get_inward_movements(self):
        """Open inward stock movements view"""
        thirty_days_ago = fields.Date.today() - timedelta(days=30)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Inward Stock Movements (Last 30 Days)',
            'res_model': 'stock.move',
            'view_mode': 'tree,form',
            'views': [[False, 'tree'], [False, 'form']],
            'domain': [
                ('date', '>=', thirty_days_ago.strftime('%Y-%m-%d')),
                ('state', '=', 'done'),
                ('location_dest_id.usage', '=', 'internal')
            ],
            'context': {'create': False},
            'target': 'current',
        }

    @http.route('/fsm/inventory/outward_movements', type='json', auth='user')
    def get_outward_movements(self):
        """Open outward stock movements view"""
        thirty_days_ago = fields.Date.today() - timedelta(days=30)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Outward Stock Movements (Last 30 Days)',
            'res_model': 'stock.move',
            'view_mode': 'tree,form',
            'views': [[False, 'tree'], [False, 'form']],
            'domain': [
                ('date', '>=', thirty_days_ago.strftime('%Y-%m-%d')),
                ('state', '=', 'done'),
                ('location_id.usage', '=', 'internal')
            ],
            'context': {'create': False},
            'target': 'current',
        }

    @http.route('/fsm/inventory/stock_requests', type='json', auth='user')
    def get_stock_requests(self):
        """Open all stock requests view"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'All Stock Requests',
            'res_model': 'fsm.spare.request',
            'view_mode': 'tree,form',
            'views': [[False, 'tree'], [False, 'form']],
            'domain': [],
            'context': {'create': False},
            'target': 'current',
        }

    @http.route('/fsm/inventory/pending_requests', type='json', auth='user')
    def get_pending_requests(self):
        """Open pending stock requests view"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Pending Stock Requests',
            'res_model': 'fsm.spare.request',
            'view_mode': 'tree,form',
            'views': [[False, 'tree'], [False, 'form']],
            'domain': [('state', 'in', ['draft', 'requested'])],
            'context': {'create': False},
            'target': 'current',
        }

    @http.route('/fsm/inventory/approved_requests', type='json', auth='user')
    def get_approved_requests(self):
        """Open approved stock requests view"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Approved Stock Requests',
            'res_model': 'fsm.spare.request',
            'view_mode': 'tree,form',
            'views': [[False, 'tree'], [False, 'form']],
            'domain': [('state', '=', 'approved')],
            'context': {'create': False},
            'target': 'current',
        }

    @http.route('/fsm/inventory/today_requests', type='json', auth='user')
    def get_today_requests(self):
        """Open today's stock requests view"""
        today = fields.Date.today()
        return {
            'type': 'ir.actions.act_window',
            'name': "Today's Stock Requests",
            'res_model': 'fsm.spare.request',
            'view_mode': 'tree,form',
            'views': [[False, 'tree'], [False, 'form']],
            'domain': [('request_date', '>=', today.strftime('%Y-%m-%d 00:00:00')),
                      ('request_date', '<=', today.strftime('%Y-%m-%d 23:59:59'))],
            'context': {'create': False},
            'target': 'current',
        }