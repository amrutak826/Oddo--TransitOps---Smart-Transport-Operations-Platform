# -*- coding: utf-8 -*-
from odoo import api, fields, models


class TransitFuelLog(models.Model):
    _name = 'transit.fuel.log'
    _description = 'Transit Vehicle Fuel Log'
    _order = 'date desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True,
        default=lambda self: 'New'
    )
    vehicle_id = fields.Many2one('transit.vehicle', string='Vehicle', required=True)
    driver_id = fields.Many2one('transit.driver', string='Driver')

    date = fields.Date(string='Date', default=fields.Date.context_today, required=True)
    quantity = fields.Float(string='Quantity (L)', required=True)
    unit_price = fields.Float(string='Unit Price', required=True)
    total_cost = fields.Float(string='Total Cost', compute='_compute_total_cost', store=True)

    odometer = fields.Float(string='Odometer Reading (km)')
    station = fields.Char(string='Fuel Station')

    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company, required=True
    )
    active = fields.Boolean(default=True)

    @api.depends('quantity', 'unit_price')
    def _compute_total_cost(self):
        for rec in self:
            rec.total_cost = rec.quantity * rec.unit_price

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('transit.fuel.log') or 'New'
        return super().create(vals_list)
