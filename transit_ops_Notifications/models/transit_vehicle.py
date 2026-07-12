# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from datetime import date, timedelta


class TransitVehicle(models.Model):
    _name = 'transit.vehicle'
    _description = 'Transit Vehicle'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name asc'
    _rec_name = 'name'

    name = fields.Char(
        string='Vehicle Number', required=True, tracking=True, copy=False,
        help='Registration / plate number of the vehicle.'
    )
    vehicle_code = fields.Char(
        string='Internal Code', required=True, copy=False, readonly=True,
        default=lambda self: 'New'
    )
    vehicle_type = fields.Selection([
        ('bus', 'Bus'),
        ('van', 'Van'),
        ('truck', 'Truck'),
        ('car', 'Car'),
        ('minibus', 'Mini Bus'),
        ('other', 'Other'),
    ], string='Vehicle Type', required=True, default='bus', tracking=True)

    brand = fields.Char(string='Brand/Make')
    model = fields.Char(string='Model')
    year = fields.Integer(string='Manufacture Year')
    color = fields.Char(string='Color')
    seating_capacity = fields.Integer(string='Seating Capacity', default=0)
    fuel_type = fields.Selection([
        ('diesel', 'Diesel'),
        ('petrol', 'Petrol'),
        ('cng', 'CNG'),
        ('electric', 'Electric'),
        ('hybrid', 'Hybrid'),
    ], string='Fuel Type', default='diesel', required=True)

    odometer = fields.Float(string='Current Odometer (km)', default=0.0, tracking=True)

    driver_id = fields.Many2one(
        'transit.driver', string='Current Driver',
        domain="[('state', '=', 'active')]", tracking=True
    )

    state = fields.Selection([
        ('available', 'Available'),
        ('on_trip', 'On Trip'),
        ('maintenance', 'Under Maintenance'),
        ('inactive', 'Inactive'),
    ], string='Status', default='available', tracking=True, required=True)

    registration_date = fields.Date(string='Registration Date')
    insurance_expiry = fields.Date(string='Insurance Expiry', tracking=True)
    permit_expiry = fields.Date(string='Permit Expiry', tracking=True)
    puc_expiry = fields.Date(string='PUC/Emission Expiry', tracking=True)
    fitness_expiry = fields.Date(string='Fitness Certificate Expiry', tracking=True)

    insurance_status = fields.Selection([
        ('valid', 'Valid'),
        ('expiring_soon', 'Expiring Soon'),
        ('expired', 'Expired'),
        ('not_set', 'Not Set'),
    ], string='Insurance Status', compute='_compute_compliance_status', store=True)

    compliance_alert = fields.Boolean(
        string='Compliance Alert', compute='_compute_compliance_status', store=True,
        help='True if any document is expired or expiring within 30 days.'
    )

    image = fields.Image(string='Vehicle Photo', max_width=1024, max_height=1024)

    trip_ids = fields.One2many('transit.trip', 'vehicle_id', string='Trips')
    trip_count = fields.Integer(string='Trip Count', compute='_compute_trip_count')

    maintenance_ids = fields.One2many('transit.maintenance', 'vehicle_id', string='Maintenance Records')
    maintenance_count = fields.Integer(string='Maintenance Count', compute='_compute_maintenance_count')

    fuel_log_ids = fields.One2many('transit.fuel.log', 'vehicle_id', string='Fuel Logs')
    fuel_log_count = fields.Integer(string='Fuel Log Count', compute='_compute_fuel_log_count')

    total_fuel_cost = fields.Monetary(
        string='Total Fuel Cost', compute='_compute_total_fuel_cost', currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id
    )

    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company, required=True
    )
    notes = fields.Text(string='Internal Notes')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_unique', 'unique(name, company_id)', 'A vehicle with this registration number already exists!'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('vehicle_code', 'New') == 'New':
                vals['vehicle_code'] = self.env['ir.sequence'].next_by_code('transit.vehicle') or 'New'
        return super().create(vals_list)

    @api.depends('insurance_expiry', 'permit_expiry', 'puc_expiry', 'fitness_expiry')
    def _compute_compliance_status(self):
        today = fields.Date.context_today(self)
        soon = today + timedelta(days=30)
        for rec in self:
            dates = [d for d in (
                rec.insurance_expiry, rec.permit_expiry, rec.puc_expiry, rec.fitness_expiry
            ) if d]

            if not rec.insurance_expiry:
                rec.insurance_status = 'not_set'
            elif rec.insurance_expiry < today:
                rec.insurance_status = 'expired'
            elif rec.insurance_expiry <= soon:
                rec.insurance_status = 'expiring_soon'
            else:
                rec.insurance_status = 'valid'

            alert = False
            for d in dates:
                if d <= soon:
                    alert = True
                    break
            rec.compliance_alert = alert

    def _compute_trip_count(self):
        trip_data = self.env['transit.trip']._read_group(
            [('vehicle_id', 'in', self.ids)], ['vehicle_id'], ['__count']
        )
        mapped = {vehicle.id: count for vehicle, count in trip_data}
        for rec in self:
            rec.trip_count = mapped.get(rec.id, 0)

    def _compute_maintenance_count(self):
        data = self.env['transit.maintenance']._read_group(
            [('vehicle_id', 'in', self.ids)], ['vehicle_id'], ['__count']
        )
        mapped = {vehicle.id: count for vehicle, count in data}
        for rec in self:
            rec.maintenance_count = mapped.get(rec.id, 0)

    def _compute_fuel_log_count(self):
        data = self.env['transit.fuel.log']._read_group(
            [('vehicle_id', 'in', self.ids)], ['vehicle_id'], ['__count']
        )
        mapped = {vehicle.id: count for vehicle, count in data}
        for rec in self:
            rec.fuel_log_count = mapped.get(rec.id, 0)

    def _compute_total_fuel_cost(self):
        data = self.env['transit.fuel.log']._read_group(
            [('vehicle_id', 'in', self.ids)], ['vehicle_id'], ['total_cost:sum']
        )
        mapped = {vehicle.id: total for vehicle, total in data}
        for rec in self:
            rec.total_fuel_cost = mapped.get(rec.id, 0.0)

    @api.constrains('year')
    def _check_year(self):
        current_year = date.today().year
        for rec in self:
            if rec.year and (rec.year < 1980 or rec.year > current_year + 1):
                raise ValidationError('Please enter a valid manufacture year.')

    @api.constrains('seating_capacity')
    def _check_seating_capacity(self):
        for rec in self:
            if rec.seating_capacity < 0:
                raise ValidationError('Seating capacity cannot be negative.')

    def action_set_available(self):
        self.write({'state': 'available'})

    def action_set_maintenance(self):
        self.write({'state': 'maintenance'})

    def action_set_inactive(self):
        self.write({'state': 'inactive'})

    def action_view_trips(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Trips',
            'res_model': 'transit.trip',
            'view_mode': 'list,form',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id},
        }

    def action_view_maintenance(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Maintenance Records',
            'res_model': 'transit.maintenance',
            'view_mode': 'list,form',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id},
        }

    def action_view_fuel_logs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Fuel Logs',
            'res_model': 'transit.fuel.log',
            'view_mode': 'list,form',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id},
        }

    def name_get(self):
        result = []
        for rec in self:
            label = rec.name
            if rec.brand or rec.model:
                label = f"{rec.name} ({rec.brand or ''} {rec.model or ''})".strip()
            result.append((rec.id, label))
        return result
