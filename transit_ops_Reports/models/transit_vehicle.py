# -*- coding: utf-8 -*-
from datetime import date, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class TransitVehicle(models.Model):
    _name = 'transit.vehicle'
    _description = 'Fleet Vehicle'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'
    _rec_name = 'display_name'

    # ================= Identification =================
    name = fields.Char(
        string='Registration Number', required=True, copy=False,
        tracking=True, index=True,
        help='Vehicle registration / license plate number.')
    display_name = fields.Char(compute='_compute_display_name', store=True)
    sequence_code = fields.Char(string='Fleet Code', copy=False, readonly=True,
                                 default=lambda self: _('New'))

    vehicle_type = fields.Selection([
        ('bus', 'Bus'),
        ('van', 'Van'),
        ('truck', 'Truck'),
        ('car', 'Car'),
        ('bike', 'Two Wheeler'),
        ('other', 'Other'),
    ], string='Vehicle Type', required=True, default='bus', tracking=True)

    make = fields.Char(string='Make', tracking=True)
    model = fields.Char(string='Model', tracking=True)
    year = fields.Integer(string='Year of Manufacture')
    color = fields.Char(string='Color')
    chassis_number = fields.Char(string='Chassis Number', copy=False)
    engine_number = fields.Char(string='Engine Number', copy=False)
    seating_capacity = fields.Integer(string='Seating Capacity', default=0)
    fuel_type = fields.Selection([
        ('diesel', 'Diesel'),
        ('petrol', 'Petrol'),
        ('cng', 'CNG'),
        ('electric', 'Electric'),
        ('hybrid', 'Hybrid'),
    ], string='Fuel Type', default='diesel', tracking=True)

    odometer = fields.Float(string='Current Odometer (km)', default=0.0, tracking=True)

    # ================= Status =================
    state = fields.Selection([
        ('available', 'Available'),
        ('on_trip', 'On Trip'),
        ('maintenance', 'Under Maintenance'),
        ('inactive', 'Inactive'),
    ], string='Status', default='available', tracking=True, index=True)

    active = fields.Boolean(default=True)

    # ================= Assignment =================
    driver_id = fields.Many2one('transit.driver', string='Default Driver', tracking=True)
    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)

    # ================= Document / Compliance =================
    insurance_number = fields.Char(string='Insurance Policy No.')
    insurance_expiry = fields.Date(string='Insurance Expiry', tracking=True)
    permit_number = fields.Char(string='Permit No.')
    permit_expiry = fields.Date(string='Permit Expiry', tracking=True)
    puc_number = fields.Char(string='PUC Certificate No.')
    puc_expiry = fields.Date(string='PUC Expiry', tracking=True)
    fitness_expiry = fields.Date(string='Fitness Certificate Expiry', tracking=True)
    registration_date = fields.Date(string='Registration Date')

    document_status = fields.Selection([
        ('valid', 'Valid'),
        ('expiring_soon', 'Expiring Soon'),
        ('expired', 'Expired'),
    ], string='Document Status', compute='_compute_document_status', store=True)

    # ================= Relations =================
    trip_ids = fields.One2many('transit.trip', 'vehicle_id', string='Trips')
    trip_count = fields.Integer(compute='_compute_trip_count', string='Trip Count')

    maintenance_ids = fields.One2many('transit.maintenance', 'vehicle_id', string='Maintenance Records')
    maintenance_count = fields.Integer(compute='_compute_maintenance_count', string='Maintenance Count')

    fuel_log_ids = fields.One2many('transit.fuel.log', 'vehicle_id', string='Fuel Logs')
    fuel_log_count = fields.Integer(compute='_compute_fuel_log_count', string='Fuel Log Count')

    total_fuel_cost = fields.Monetary(compute='_compute_totals', string='Total Fuel Cost', store=True)
    total_maintenance_cost = fields.Monetary(compute='_compute_totals', string='Total Maintenance Cost', store=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    image = fields.Image(string='Photo', max_width=1024, max_height=1024)
    notes = fields.Text(string='Internal Notes')

    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)',
         'A vehicle with this registration number already exists!'),
    ]

    # ================= Compute Methods =================
    @api.depends('name', 'vehicle_type')
    def _compute_display_name(self):
        for rec in self:
            vt = dict(self._fields['vehicle_type'].selection).get(rec.vehicle_type, '')
            rec.display_name = f"{rec.name} ({vt})" if vt else rec.name or ''

    @api.depends('insurance_expiry', 'permit_expiry', 'puc_expiry', 'fitness_expiry')
    def _compute_document_status(self):
        today = fields.Date.context_today(self)
        warn_before = today + timedelta(days=15)
        for rec in self:
            expiries = [d for d in [rec.insurance_expiry, rec.permit_expiry,
                                     rec.puc_expiry, rec.fitness_expiry] if d]
            if not expiries:
                rec.document_status = 'valid'
                continue
            if any(d < today for d in expiries):
                rec.document_status = 'expired'
            elif any(d <= warn_before for d in expiries):
                rec.document_status = 'expiring_soon'
            else:
                rec.document_status = 'valid'

    def _compute_trip_count(self):
        for rec in self:
            rec.trip_count = len(rec.trip_ids)

    def _compute_maintenance_count(self):
        for rec in self:
            rec.maintenance_count = len(rec.maintenance_ids)

    def _compute_fuel_log_count(self):
        for rec in self:
            rec.fuel_log_count = len(rec.fuel_log_ids)

    @api.depends('fuel_log_ids.total_cost', 'maintenance_ids.cost')
    def _compute_totals(self):
        for rec in self:
            rec.total_fuel_cost = sum(rec.fuel_log_ids.mapped('total_cost'))
            rec.total_maintenance_cost = sum(rec.maintenance_ids.mapped('cost'))

    # ================= Constraints =================
    @api.constrains('year')
    def _check_year(self):
        current_year = date.today().year
        for rec in self:
            if rec.year and (rec.year < 1950 or rec.year > current_year + 1):
                raise ValidationError(_('Please enter a valid year of manufacture.'))

    @api.constrains('seating_capacity')
    def _check_seating_capacity(self):
        for rec in self:
            if rec.seating_capacity < 0:
                raise ValidationError(_('Seating capacity cannot be negative.'))

    # ================= CRUD =================
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('sequence_code', _('New')) == _('New'):
                vals['sequence_code'] = self.env['ir.sequence'].next_by_code(
                    'transit.vehicle') or _('New')
        return super().create(vals_list)

    # ================= Actions =================
    def action_set_maintenance(self):
        self.write({'state': 'maintenance'})

    def action_set_available(self):
        self.write({'state': 'available'})

    def action_set_inactive(self):
        self.write({'state': 'inactive'})

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

    def action_view_fuel_logs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Fuel Logs'),
            'res_model': 'transit.fuel.log',
            'view_mode': 'list,form',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id},
        }
