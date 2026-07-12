# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class TransitFuelLog(models.Model):
    _name = 'transit.fuel.log'
    _description = 'Fuel Log'
    _order = 'date desc'
    _rec_name = 'name'

    name = fields.Char(string='Reference', copy=False, readonly=True,
                        default=lambda self: _('New'))

    vehicle_id = fields.Many2one('transit.vehicle', string='Vehicle', required=True)
    driver_id = fields.Many2one('transit.driver', string='Driver', required=True)

    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    fuel_type = fields.Selection([
        ('diesel', 'Diesel'),
        ('petrol', 'Petrol'),
        ('cng', 'CNG'),
        ('electric', 'Electric'),
    ], string='Fuel Type', default='diesel')

    quantity = fields.Float(string='Quantity (L / kg / kWh)', required=True)
    unit_price = fields.Monetary(string='Unit Price')
    total_cost = fields.Monetary(string='Total Cost', compute='_compute_total_cost',
                                  store=True, readonly=False)
    odometer_reading = fields.Float(string='Odometer Reading (km)')
    station = fields.Char(string='Fuel Station')

    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    notes = fields.Text(string='Notes')

    @api.depends('quantity', 'unit_price')
    def _compute_total_cost(self):
        for rec in self:
            if not rec.total_cost:
                rec.total_cost = rec.quantity * rec.unit_price

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('transit.fuel.log') or _('New')
        logs = super().create(vals_list)
        for log in logs:
            if log.odometer_reading and log.odometer_reading > log.vehicle_id.odometer:
                log.vehicle_id.odometer = log.odometer_reading
        return logs
