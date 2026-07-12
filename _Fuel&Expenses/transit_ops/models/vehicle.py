# -*- coding: utf-8 -*-
from datetime import date, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class TransitVehicle(models.Model):
    _name = 'transit.vehicle'
    _description = 'Transit Vehicle'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name asc'
    _rec_name = 'name'

    # ------------------------------------------------------------------
    # Basic Info
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Registration Number', required=True, tracking=True, copy=False,
        help='Vehicle registration / license plate number.'
    )
    vehicle_type = fields.Selection([
        ('bus', 'Bus'),
        ('van', 'Van'),
        ('truck', 'Truck'),
        ('car', 'Car'),
        ('other', 'Other'),
    ], string='Vehicle Type', required=True, default='bus', tracking=True)

    make = fields.Char(string='Make', help='Manufacturer, e.g. Tata, Ashok Leyland.')
    model = fields.Char(string='Model')
    year = fields.Integer(string='Manufacture Year')
    color = fields.Char(string='Color')
    chassis_number = fields.Char(string='Chassis Number', copy=False)
    engine_number = fields.Char(string='Engine Number', copy=False)

    fuel_type = fields.Selection([
        ('diesel', 'Diesel'),
        ('petrol', 'Petrol'),
        ('cng', 'CNG'),
        ('electric', 'Electric'),
        ('hybrid', 'Hybrid'),
    ], string='Fuel Type', required=True, default='diesel', tracking=True)

    seating_capacity = fields.Integer(string='Seating Capacity', default=1)
    odometer = fields.Float(string='Odometer (km)', default=0.0, tracking=True)

    owner_type = fields.Selection([
        ('owned', 'Owned'),
        ('leased', 'Leased'),
        ('rented', 'Rented'),
    ], string='Ownership', default='owned')

    purchase_date = fields.Date(string='Purchase Date')

    # ------------------------------------------------------------------
    # Status & Assignment
    # ------------------------------------------------------------------
    status = fields.Selection([
        ('available', 'Available'),
        ('on_trip', 'On Trip'),
        ('maintenance', 'Under Maintenance'),
        ('out_of_service', 'Out of Service'),
    ], string='Status', default='available', required=True, tracking=True)

    current_driver_id = fields.Many2one(
        'transit.driver', string='Current Driver', tracking=True,
        domain="[('status', '!=', 'inactive')]"
    )

    # ------------------------------------------------------------------
    # Compliance / Document Expiry
    # ------------------------------------------------------------------
    insurance_expiry = fields.Date(string='Insurance Expiry')
    puc_expiry = fields.Date(string='PUC (Pollution) Expiry')
    fitness_expiry = fields.Date(string='Fitness Certificate Expiry')
    permit_expiry = fields.Date(string='Permit Expiry')

    document_status = fields.Selection([
        ('valid', 'All Valid'),
        ('expiring_soon', 'Expiring Soon'),
        ('expired', 'Expired'),
        ('not_set', 'Not Set'),
    ], string='Document Status', compute='_compute_document_status',
        store=True, tracking=True)

    # ------------------------------------------------------------------
    # Misc
    # ------------------------------------------------------------------
    image = fields.Image(string='Vehicle Photo', max_width=1024, max_height=1024)
    notes = fields.Text(string='Notes')
    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company
    )

    trip_ids = fields.One2many('transit.trip', 'vehicle_id', string='Trips')
    trip_count = fields.Integer(string='Trip Count', compute='_compute_trip_count')

    maintenance_ids = fields.One2many(
        'transit.maintenance', 'vehicle_id', string='Maintenance Records'
    )
    maintenance_count = fields.Integer(
        string='Maintenance Count', compute='_compute_maintenance_count'
    )

    # ------------------------------------------------------------------
    # Compute Methods
    # ------------------------------------------------------------------
    @api.depends('insurance_expiry', 'puc_expiry', 'fitness_expiry', 'permit_expiry')
    def _compute_document_status(self):
        today = date.today()
        warning_window = today + timedelta(days=30)
        for vehicle in self:
            dates = [
                vehicle.insurance_expiry,
                vehicle.puc_expiry,
                vehicle.fitness_expiry,
                vehicle.permit_expiry,
            ]
            set_dates = [d for d in dates if d]
            if not set_dates:
                vehicle.document_status = 'not_set'
            elif any(d < today for d in set_dates):
                vehicle.document_status = 'expired'
            elif any(today <= d <= warning_window for d in set_dates):
                vehicle.document_status = 'expiring_soon'
            else:
                vehicle.document_status = 'valid'

    def _compute_trip_count(self):
        for vehicle in self:
            vehicle.trip_count = len(vehicle.trip_ids)

    def _compute_maintenance_count(self):
        for vehicle in self:
            vehicle.maintenance_count = len(vehicle.maintenance_ids)

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('seating_capacity')
    def _check_seating_capacity(self):
        for vehicle in self:
            if vehicle.seating_capacity is not None and vehicle.seating_capacity < 0:
                raise ValidationError(_('Seating capacity cannot be negative.'))

    @api.constrains('year')
    def _check_year(self):
        current_year = date.today().year
        for vehicle in self:
            if vehicle.year and (vehicle.year < 1950 or vehicle.year > current_year + 1):
                raise ValidationError(
                    _('Please enter a valid manufacture year between 1950 and %s.') % (current_year + 1)
                )

    @api.constrains('odometer')
    def _check_odometer(self):
        for vehicle in self:
            if vehicle.odometer < 0:
                raise ValidationError(_('Odometer reading cannot be negative.'))

    _sql_constraints = [
        (
            'name_unique',
            'unique(name, company_id)',
            'A vehicle with this registration number already exists!'
        ),
    ]

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_view_trips(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Trips'),
            'res_model': 'transit.trip',
            'view_mode': 'list,form',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id},
        }

    def action_view_maintenance(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Maintenance Records'),
            'res_model': 'transit.maintenance',
            'view_mode': 'list,form',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id},
        }

    def action_set_maintenance(self):
        for vehicle in self:
            vehicle.status = 'maintenance'

    def action_set_available(self):
        for vehicle in self:
            vehicle.status = 'available'

    def action_set_out_of_service(self):
        for vehicle in self:
            vehicle.status = 'out_of_service'

    def name_get(self):
        result = []
        for vehicle in self:
            label = vehicle.name
            if vehicle.make or vehicle.model:
                label = '%s (%s %s)' % (vehicle.name, vehicle.make or '', vehicle.model or '')
            result.append((vehicle.id, label))
        return result
