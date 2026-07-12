# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class TransitFuelLog(models.Model):
    _name = 'transit.fuel.log'
    _description = 'Transit Fuel Log'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'
    _rec_name = 'name'

    name = fields.Char(string='Reference', compute='_compute_name', store=True)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company, required=True,
    )

    vehicle_id = fields.Many2one('transit.vehicle', string='Vehicle', required=True, tracking=True)
    driver_id = fields.Many2one('transit.driver', string='Driver')
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today, tracking=True)

    odometer = fields.Float(string='Odometer Reading (km)', required=True)
    fuel_quantity = fields.Float(string='Fuel Quantity (L)', required=True)
    fuel_cost = fields.Monetary(string='Total Cost')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
    )
    fuel_station = fields.Char(string='Fuel Station')
    full_tank = fields.Boolean(string='Full Tank', default=True)

    distance_since_last = fields.Float(string='Distance Since Last Fill (km)', compute='_compute_mileage', store=True)
    mileage_kmpl = fields.Float(string='Mileage (km/L)', compute='_compute_mileage', store=True)

    notes = fields.Text(string='Notes')

    @api.depends('vehicle_id', 'date')
    def _compute_name(self):
        for log in self:
            if log.vehicle_id and log.date:
                log.name = f"{log.vehicle_id.license_plate or log.vehicle_id.name} - {log.date}"
            else:
                log.name = _('New Fuel Log')

    @api.depends('vehicle_id', 'odometer', 'fuel_quantity')
    def _compute_mileage(self):
        for log in self:
            log.distance_since_last = 0.0
            log.mileage_kmpl = 0.0
            if not log.vehicle_id or not log.odometer:
                continue
            previous = self.search([
                ('vehicle_id', '=', log.vehicle_id.id),
                ('date', '<=', log.date),
                ('odometer', '<', log.odometer),
                ('id', '!=', log._origin.id if log._origin else log.id),
            ], order='date desc, odometer desc', limit=1)
            if previous:
                distance = log.odometer - previous.odometer
                log.distance_since_last = distance
                if log.fuel_quantity:
                    log.mileage_kmpl = distance / log.fuel_quantity

    @api.constrains('odometer', 'fuel_quantity', 'fuel_cost')
    def _check_positive_values(self):
        for log in self:
            if log.odometer < 0:
                raise ValidationError(_('Odometer reading cannot be negative.'))
            if log.fuel_quantity <= 0:
                raise ValidationError(_('Fuel Quantity must be greater than zero.'))
            if log.fuel_cost < 0:
                raise ValidationError(_('Fuel Cost cannot be negative.'))
