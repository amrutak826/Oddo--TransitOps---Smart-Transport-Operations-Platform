# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class TransitVehicle(models.Model):
    _name = 'transit.vehicle'
    _description = 'Transit Vehicle'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'license_plate asc'
    _rec_name = 'display_name'

    # ---------------------------------------------------------------
    # Basic Information
    # ---------------------------------------------------------------
    name = fields.Char(
        string='Vehicle Name',
        required=True,
        tracking=True,
        help='Internal friendly name, e.g. "Bus 12" or "Delivery Van A".',
    )
    display_name = fields.Char(compute='_compute_display_name', store=True)
    license_plate = fields.Char(
        string='License Plate',
        required=True,
        tracking=True,
        copy=False,
        index=True,
    )
    vin = fields.Char(string='Chassis / VIN Number', copy=False)
    image_1920 = fields.Image(string='Vehicle Photo', max_width=1920, max_height=1920)
    color = fields.Char(string='Color')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company, required=True,
    )

    # ---------------------------------------------------------------
    # Classification
    # ---------------------------------------------------------------
    vehicle_type = fields.Selection([
        ('bus', 'Bus'),
        ('van', 'Van'),
        ('truck', 'Truck'),
        ('car', 'Car'),
        ('bike', 'Motorbike'),
        ('other', 'Other'),
    ], string='Vehicle Type', required=True, default='van', tracking=True)

    fuel_type = fields.Selection([
        ('diesel', 'Diesel'),
        ('petrol', 'Petrol'),
        ('cng', 'CNG'),
        ('electric', 'Electric'),
        ('hybrid', 'Hybrid'),
    ], string='Fuel Type', required=True, default='diesel')

    brand = fields.Char(string='Brand / Make')
    model = fields.Char(string='Model')
    year_of_manufacture = fields.Integer(string='Year of Manufacture')
    seating_capacity = fields.Integer(string='Seating Capacity', default=4)
    load_capacity_kg = fields.Float(string='Load Capacity (kg)')

    # ---------------------------------------------------------------
    # Status & Assignment
    # ---------------------------------------------------------------
    state = fields.Selection([
        ('active', 'Active'),
        ('on_trip', 'On Trip'),
        ('maintenance', 'Under Maintenance'),
        ('inactive', 'Inactive'),
        ('retired', 'Retired'),
    ], string='Status', default='active', required=True, tracking=True, copy=False)

    default_driver_id = fields.Many2one(
        'transit.driver', string='Default Driver',
        tracking=True,
        help='Primary driver usually assigned to this vehicle.',
    )
    odometer = fields.Float(string='Current Odometer (km)', tracking=True)
    odometer_unit = fields.Selection([
        ('km', 'Kilometers'),
        ('mi', 'Miles'),
    ], string='Odometer Unit', default='km', required=True)

    # ---------------------------------------------------------------
    # Documents & Compliance
    # ---------------------------------------------------------------
    registration_number = fields.Char(string='Registration (RC) Number')
    registration_expiry_date = fields.Date(string='Registration Expiry')
    insurance_number = fields.Char(string='Insurance Policy Number')
    insurance_expiry_date = fields.Date(string='Insurance Expiry', tracking=True)
    puc_expiry_date = fields.Date(string='Pollution Certificate (PUC) Expiry')
    permit_expiry_date = fields.Date(string='Permit Expiry')

    document_alert_state = fields.Selection([
        ('ok', 'All Valid'),
        ('warning', 'Expiring Soon'),
        ('expired', 'Expired'),
    ], string='Document Status', compute='_compute_document_alert_state',
        store=True, tracking=True)

    # ---------------------------------------------------------------
    # Financial
    # ---------------------------------------------------------------
    purchase_date = fields.Date(string='Purchase Date')
    purchase_value = fields.Monetary(string='Purchase Value')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
    )

    # ---------------------------------------------------------------
    # Relations (forward references resolved once related modules load)
    # ---------------------------------------------------------------
    trip_ids = fields.One2many('transit.trip', 'vehicle_id', string='Trips')
    maintenance_ids = fields.One2many('transit.maintenance', 'vehicle_id', string='Maintenance Records')
    fuel_log_ids = fields.One2many('transit.fuel.log', 'vehicle_id', string='Fuel Logs')

    trip_count = fields.Integer(compute='_compute_trip_count', string='Trip Count')
    maintenance_count = fields.Integer(compute='_compute_maintenance_count', string='Maintenance Count')
    fuel_log_count = fields.Integer(compute='_compute_fuel_log_count', string='Fuel Log Count')

    notes = fields.Html(string='Internal Notes')

    _sql_constraints = [
        ('license_plate_unique', 'unique(license_plate, company_id)',
         'This license plate is already registered for another vehicle in this company!'),
    ]

    # ---------------------------------------------------------------
    # Compute Methods
    # ---------------------------------------------------------------
    @api.depends('name', 'license_plate')
    def _compute_display_name(self):
        for vehicle in self:
            if vehicle.license_plate:
                vehicle.display_name = f"{vehicle.name} [{vehicle.license_plate}]"
            else:
                vehicle.display_name = vehicle.name or _('New Vehicle')

    @api.depends(
        'registration_expiry_date', 'insurance_expiry_date',
        'puc_expiry_date', 'permit_expiry_date',
    )
    def _compute_document_alert_state(self):
        today = fields.Date.context_today(self)
        warning_horizon = today + timedelta(days=30)
        for vehicle in self:
            dates = [
                d for d in (
                    vehicle.registration_expiry_date,
                    vehicle.insurance_expiry_date,
                    vehicle.puc_expiry_date,
                    vehicle.permit_expiry_date,
                ) if d
            ]
            if not dates:
                vehicle.document_alert_state = 'ok'
                continue
            if any(d < today for d in dates):
                vehicle.document_alert_state = 'expired'
            elif any(d <= warning_horizon for d in dates):
                vehicle.document_alert_state = 'warning'
            else:
                vehicle.document_alert_state = 'ok'

    def _compute_trip_count(self):
        trip_data = self.env['transit.trip']._read_group(
            [('vehicle_id', 'in', self.ids)], ['vehicle_id'], ['__count'],
        )
        mapped_data = {vehicle.id: count for vehicle, count in trip_data}
        for vehicle in self:
            vehicle.trip_count = mapped_data.get(vehicle.id, 0)

    def _compute_maintenance_count(self):
        data = self.env['transit.maintenance']._read_group(
            [('vehicle_id', 'in', self.ids)], ['vehicle_id'], ['__count'],
        )
        mapped_data = {vehicle.id: count for vehicle, count in data}
        for vehicle in self:
            vehicle.maintenance_count = mapped_data.get(vehicle.id, 0)

    def _compute_fuel_log_count(self):
        data = self.env['transit.fuel.log']._read_group(
            [('vehicle_id', 'in', self.ids)], ['vehicle_id'], ['__count'],
        )
        mapped_data = {vehicle.id: count for vehicle, count in data}
        for vehicle in self:
            vehicle.fuel_log_count = mapped_data.get(vehicle.id, 0)

    # ---------------------------------------------------------------
    # Constraints
    # ---------------------------------------------------------------
    @api.constrains('year_of_manufacture')
    def _check_year_of_manufacture(self):
        current_year = fields.Date.context_today(self).year
        for vehicle in self:
            if vehicle.year_of_manufacture and (
                vehicle.year_of_manufacture < 1950 or vehicle.year_of_manufacture > current_year + 1
            ):
                raise ValidationError(_(
                    'Year of Manufacture must be between 1950 and %(year)s.',
                    year=current_year + 1,
                ))

    @api.constrains('seating_capacity')
    def _check_seating_capacity(self):
        for vehicle in self:
            if vehicle.seating_capacity < 0:
                raise ValidationError(_('Seating Capacity cannot be negative.'))

    @api.constrains('odometer')
    def _check_odometer(self):
        for vehicle in self:
            if vehicle.odometer < 0:
                raise ValidationError(_('Odometer reading cannot be negative.'))

    # ---------------------------------------------------------------
    # Action Methods
    # ---------------------------------------------------------------
    def action_set_active(self):
        self.write({'state': 'active'})

    def action_set_maintenance(self):
        self.write({'state': 'maintenance'})

    def action_set_inactive(self):
        self.write({'state': 'inactive'})

    def action_set_retired(self):
        self.write({'state': 'retired', 'active': False})

    def action_view_trips(self):
        self.ensure_one()
        return {
            'name': _('Trips'),
            'type': 'ir.actions.act_window',
            'res_model': 'transit.trip',
            'view_mode': 'list,form,calendar',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id},
        }

    def action_view_maintenance(self):
        self.ensure_one()
        return {
            'name': _('Maintenance Records'),
            'type': 'ir.actions.act_window',
            'res_model': 'transit.maintenance',
            'view_mode': 'list,form',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id},
        }

    def action_view_fuel_logs(self):
        self.ensure_one()
        return {
            'name': _('Fuel Logs'),
            'type': 'ir.actions.act_window',
            'res_model': 'transit.fuel.log',
            'view_mode': 'list,form,graph',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id},
        }

    # ---------------------------------------------------------------
    # Cron / Automated Checks
    # ---------------------------------------------------------------
    @api.model
    def _cron_check_vehicle_documents(self):
        """Scheduled action: scans all active vehicles for documents that
        are expired or expiring within 30 days and raises a mail activity
        on the vehicle for the responsible Transit Manager to act on.
        """
        today = fields.Date.context_today(self)
        warning_horizon = today + timedelta(days=30)
        vehicles = self.search([('active', '=', True)])
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        if not activity_type:
            return

        manager_group = self.env.ref('transit_ops.group_transit_manager', raise_if_not_found=False)
        responsible_user = self.env.user
        if manager_group and manager_group.users:
            responsible_user = manager_group.users[0]

        doc_labels = {
            'registration_expiry_date': _('Registration (RC)'),
            'insurance_expiry_date': _('Insurance'),
            'puc_expiry_date': _('Pollution Certificate (PUC)'),
            'permit_expiry_date': _('Permit'),
        }

        for vehicle in vehicles:
            expiring_docs = []
            for field_name, label in doc_labels.items():
                date_value = getattr(vehicle, field_name)
                if date_value and date_value <= warning_horizon:
                    if date_value < today:
                        status = _('EXPIRED on %s') % date_value
                    else:
                        status = _('expiring on %s') % date_value
                    expiring_docs.append(f"{label}: {status}")

            if not expiring_docs:
                continue

            note = '<br/>'.join(expiring_docs)
            existing = self.env['mail.activity'].search([
                ('res_model', '=', 'transit.vehicle'),
                ('res_id', '=', vehicle.id),
                ('activity_type_id', '=', activity_type.id),
                ('summary', '=', _('Vehicle Document Expiry Alert')),
            ], limit=1)
            if existing:
                existing.write({'note': note})
            else:
                vehicle.activity_schedule(
                    activity_type_id=activity_type.id,
                    summary=_('Vehicle Document Expiry Alert'),
                    note=note,
                    user_id=responsible_user.id,
                    date_deadline=today,
                )
