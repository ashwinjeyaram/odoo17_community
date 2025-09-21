# -*- coding: utf-8 -*-
from odoo import models, fields, api

class FSMState(models.Model):
    _name = 'fsm.state'
    _description = 'FSM State Master'
    _order = 'name'
    
    name = fields.Char(string='State Name', required=True)
    code = fields.Char(string='State Code')
    country_id = fields.Many2one('res.country', string='Country', default=lambda self: self.env.ref('base.in', False))
    district_ids = fields.One2many('fsm.district', 'state_id', string='Districts')
    active = fields.Boolean(default=True)
    
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'State name must be unique!'),
        ('code_uniq', 'unique(code)', 'State code must be unique!')
    ]


class FSMDistrict(models.Model):
    _name = 'fsm.district'
    _description = 'FSM District Master'
    _order = 'name'
    
    name = fields.Char(string='District Name', required=True)
    state_id = fields.Many2one('fsm.state', string='State', required=True)
    code = fields.Char(string='District Code')
    pincode_ids = fields.One2many('fsm.pincode', 'district_id', string='Pincodes')
    active = fields.Boolean(default=True)
    
    _sql_constraints = [
        ('name_state_uniq', 'unique(name, state_id)', 'District name must be unique within a state!'),
    ]


class FSMPincode(models.Model):
    _name = 'fsm.pincode'
    _description = 'FSM Pincode Master'
    _order = 'pincode'
    _rec_name = 'pincode'
    
    pincode = fields.Char(string='Pincode', required=True)
    district_id = fields.Many2one('fsm.district', string='District', required=True)
    state_id = fields.Many2one('fsm.state', string='State', required=True)
    area_ids = fields.One2many('fsm.area', 'pincode_id', string='Areas')
    active = fields.Boolean(default=True)
    
    @api.onchange('district_id')
    def _onchange_district_id(self):
        if self.district_id:
            self.state_id = self.district_id.state_id
    
    @api.model
    def name_get(self):
        result = []
        for record in self:
            name = f"{record.pincode}"
            if record.district_id:
                name += f" - {record.district_id.name}"
            if record.state_id:
                name += f", {record.state_id.name}"
            result.append((record.id, name))
        return result
    
    _sql_constraints = [
        ('pincode_uniq', 'unique(pincode, district_id)', 'Pincode must be unique within a district!'),
    ]


class FSMArea(models.Model):
    _name = 'fsm.area'
    _description = 'FSM Area Master'
    _order = 'name'
    
    name = fields.Char(string='Area Name', required=True)
    pincode_id = fields.Many2one('fsm.pincode', string='Pincode', required=True)
    district_id = fields.Many2one('fsm.district', string='District', related='pincode_id.district_id', readonly=True, store=True)
    state_id = fields.Many2one('fsm.state', string='State', related='pincode_id.state_id', readonly=True, store=True)
    active = fields.Boolean(default=True)
    
    _sql_constraints = [
        ('name_pincode_uniq', 'unique(name, pincode_id)', 'Area name must be unique within a pincode!'),
    ]