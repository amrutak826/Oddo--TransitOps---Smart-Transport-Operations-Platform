# -*- coding: utf-8 -*-
from datetime import date

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class TransitVehicle(models.Model):
    _name = 'transit.vehicle'
    _description = 'Transit Vehicle'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'
    _rec_name = 'name'

    name = fields.Char(
        string='License Plate', required=True, tracking=True,
        help='Vehicle registration / license plate number.')
    vehicle_type = fields.Selection([
        ('bus', 'Bus'),
        ('minibus', 'Minibus'),
        ('van', 'Van'),
        ('truck', 'Truck'),
        ('car', 'Car'),
        ('bike', 'Motorbike'),
    ], string='Vehicle Type', required=True, default='bus', tracking=True)
    brand = fields.Char(string='Brand')
    model = fields.Char(string='Model')
    year = fields.Integer(string='Manufacture Year')
    color = fields.Char(string='Color')
    capacity = fields.Integer(string='Seating Capacity', default=1)
    chassis_number = fields.Char(string='Chassis Number', copy=False)
    engine_number = fields.Char(string='Engine Number', copy=False)
    fuel_type = fields.Selection([
        ('diesel', 'Diesel'),
        ('petrol', 'Petrol'),
        ('cng', 'CNG'),
        ('electric', 'Electric'),
        ('hybrid', 'Hybrid'),
    ], string='Fuel Type', default='diesel', required=True)

    odometer = fields.Float(string='Odometer (km)', default=0.0, tracking=True)

    status = fields.Selection([
        ('active', 'Active'),
        ('on_trip', 'On Trip'),
        ('maintenance', 'In Maintenance'),
        ('inactive', 'Inactive'),
        ('retired', 'Retired'),
    ], string='Status', default='active', required=True, tracking=True)

    purchase_date = fields.Date(string='Purchase Date')
    insurance_expiry = fields.Date(string='Insurance Expiry', tracking=True)
    registration_expiry = fields.Date(string='Registration Expiry', tracking=True)
    fitness_expiry = fields.Date(string='Fitness Certificate Expiry', tracking=True)

    insurance_days_left = fields.Integer(
        string='Insurance Days Left', compute='_compute_document_alerts', store=True)
    registration_days_left = fields.Integer(
        string='Registration Days Left', compute='_compute_document_alerts', store=True)
    document_alert = fields.Boolean(
        string='Document Alert', compute='_compute_document_alerts', store=True,
        help='True if any document expires within 30 days or has already expired.')

    driver_id = fields.Many2one(
        'transit.driver', string='Assigned Driver', tracking=True,
        domain="[('status', '!=', 'suspended')]")
    image = fields.Image(string='Vehicle Photo', max_width=1024, max_height=1024)
    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company)

    trip_count = fields.Integer(string='Trip Count', default=0)

    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)',
         'A vehicle with this license plate already exists!'),
    ]

    @api.depends('insurance_expiry', 'registration_expiry')
    def _compute_document_alerts(self):
        today = date.today()
        for vehicle in self:
            ins_days = (vehicle.insurance_expiry - today).days if vehicle.insurance_expiry else 9999
            reg_days = (vehicle.registration_expiry - today).days if vehicle.registration_expiry else 9999
            vehicle.insurance_days_left = ins_days
            vehicle.registration_days_left = reg_days
            vehicle.document_alert = ins_days <= 30 or reg_days <= 30

    @api.constrains('year')
    def _check_year(self):
        current_year = date.today().year
        for vehicle in self:
            if vehicle.year and (vehicle.year < 1950 or vehicle.year > current_year + 1):
                raise ValidationError('Please enter a valid manufacture year.')

    @api.constrains('capacity')
    def _check_capacity(self):
        for vehicle in self:
            if vehicle.capacity is not None and vehicle.capacity < 0:
                raise ValidationError('Seating capacity cannot be negative.')

    def action_set_maintenance(self):
        self.write({'status': 'maintenance'})

    def action_set_active(self):
        self.write({'status': 'active'})

    def action_retire_vehicle(self):
        self.write({'status': 'retired', 'active': False})

    def name_get(self):
        result = []
        for vehicle in self:
            label = vehicle.name
            if vehicle.brand or vehicle.model:
                label = f"{vehicle.name} ({vehicle.brand or ''} {vehicle.model or ''})".strip()
            result.append((vehicle.id, label))
        return result
