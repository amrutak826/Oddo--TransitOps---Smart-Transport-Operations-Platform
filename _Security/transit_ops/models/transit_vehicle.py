# -*- coding: utf-8 -*-
from datetime import date, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class TransitVehicle(models.Model):
    _name = 'transit.vehicle'
    _description = 'Transit Vehicle'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name asc'
    _rec_name = 'display_name'

    # ------------------------------------------------------------------
    # Basic Information
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Registration Number', required=True, copy=False,
        tracking=True, index=True,
        help='Vehicle registration / license plate number.')
    fleet_number = fields.Char(
        string='Fleet Number', copy=False, tracking=True,
        help='Internal fleet identification code.')
    display_name = fields.Char(compute='_compute_display_name', store=True)

    vehicle_type = fields.Selection([
        ('bus', 'Bus'),
        ('van', 'Van'),
        ('truck', 'Truck'),
        ('car', 'Car'),
        ('minibus', 'Mini Bus'),
        ('other', 'Other'),
    ], string='Vehicle Type', required=True, default='bus', tracking=True)

    brand = fields.Char(string='Brand')
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
    ], string='Fuel Type', default='diesel', tracking=True)

    seating_capacity = fields.Integer(string='Seating Capacity')
    odometer = fields.Float(string='Odometer (km)', tracking=True)

    image = fields.Image(string='Vehicle Photo', max_width=1024, max_height=1024)

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------
    status = fields.Selection([
        ('active', 'Active'),
        ('on_trip', 'On Trip'),
        ('maintenance', 'In Maintenance'),
        ('inactive', 'Inactive'),
        ('retired', 'Retired'),
    ], string='Status', default='active', tracking=True, required=True)

    current_driver_id = fields.Many2one(
        'transit.driver', string='Current Driver', tracking=True,
        domain="[('status', '!=', 'inactive')]")

    # ------------------------------------------------------------------
    # Documents & Compliance
    # ------------------------------------------------------------------
    purchase_date = fields.Date(string='Purchase Date')
    insurance_expiry = fields.Date(string='Insurance Expiry', tracking=True)
    fitness_expiry = fields.Date(string='Fitness Certificate Expiry', tracking=True)
    permit_expiry = fields.Date(string='Permit Expiry', tracking=True)
    puc_expiry = fields.Date(string='PUC (Pollution) Expiry', tracking=True)

    document_alert_level = fields.Selection([
        ('none', 'OK'),
        ('warning', 'Expiring Soon'),
        ('danger', 'Expired'),
    ], string='Document Status', compute='_compute_document_alert_level',
        store=True, help='Worst-case status across all tracked documents.')

    next_document_to_expire = fields.Char(
        string='Next Expiring Document', compute='_compute_document_alert_level', store=True)
    next_document_expiry_date = fields.Date(
        string='Next Expiry Date', compute='_compute_document_alert_level', store=True)

    # ------------------------------------------------------------------
    # Relations
    # ------------------------------------------------------------------
    trip_ids = fields.One2many('transit.trip', 'vehicle_id', string='Trips')
    maintenance_ids = fields.One2many('transit.maintenance', 'vehicle_id', string='Maintenance Records')
    fuel_expense_ids = fields.One2many('transit.fuel.expense', 'vehicle_id', string='Fuel & Expense Records')

    trip_count = fields.Integer(compute='_compute_trip_count', string='Trip Count')
    maintenance_count = fields.Integer(compute='_compute_maintenance_count', string='Maintenance Count')

    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company)
    color_tag = fields.Integer(string='Kanban Color Index')

    _sql_constraints = [
        ('registration_number_unique',
         'UNIQUE(name, company_id)',
         'A vehicle with this registration number already exists!'),
    ]

    # ------------------------------------------------------------------
    # Compute Methods
    # ------------------------------------------------------------------
    @api.depends('name', 'fleet_number')
    def _compute_display_name(self):
        for vehicle in self:
            if vehicle.fleet_number:
                vehicle.display_name = f"[{vehicle.fleet_number}] {vehicle.name or ''}"
            else:
                vehicle.display_name = vehicle.name or ''

    @api.depends(
        'insurance_expiry', 'fitness_expiry', 'permit_expiry', 'puc_expiry')
    def _compute_document_alert_level(self):
        today = fields.Date.context_today(self)
        warning_window = today + timedelta(days=30)
        for vehicle in self:
            documents = [
                ('Insurance', vehicle.insurance_expiry),
                ('Fitness Certificate', vehicle.fitness_expiry),
                ('Permit', vehicle.permit_expiry),
                ('PUC Certificate', vehicle.puc_expiry),
            ]
            documents = [d for d in documents if d[1]]
            if not documents:
                vehicle.document_alert_level = 'none'
                vehicle.next_document_to_expire = False
                vehicle.next_document_expiry_date = False
                continue

            documents.sort(key=lambda d: d[1])
            closest_name, closest_date = documents[0]
            vehicle.next_document_to_expire = closest_name
            vehicle.next_document_expiry_date = closest_date

            if closest_date < today:
                vehicle.document_alert_level = 'danger'
            elif closest_date <= warning_window:
                vehicle.document_alert_level = 'warning'
            else:
                vehicle.document_alert_level = 'none'

    def _compute_trip_count(self):
        trip_data = self.env['transit.trip']._read_group(
            [('vehicle_id', 'in', self.ids)], ['vehicle_id'], ['__count'])
        mapped_data = {vehicle.id: count for vehicle, count in trip_data}
        for vehicle in self:
            vehicle.trip_count = mapped_data.get(vehicle.id, 0)

    def _compute_maintenance_count(self):
        maint_data = self.env['transit.maintenance']._read_group(
            [('vehicle_id', 'in', self.ids)], ['vehicle_id'], ['__count'])
        mapped_data = {vehicle.id: count for vehicle, count in maint_data}
        for vehicle in self:
            vehicle.maintenance_count = mapped_data.get(vehicle.id, 0)

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('year')
    def _check_year(self):
        current_year = date.today().year
        for vehicle in self:
            if vehicle.year and (vehicle.year < 1950 or vehicle.year > current_year + 1):
                raise ValidationError(_(
                    'Please enter a valid manufacture year between 1950 and %s.'
                ) % (current_year + 1))

    @api.constrains('seating_capacity')
    def _check_seating_capacity(self):
        for vehicle in self:
            if vehicle.seating_capacity < 0:
                raise ValidationError(_('Seating capacity cannot be negative.'))

    @api.constrains('odometer')
    def _check_odometer(self):
        for vehicle in self:
            if vehicle.odometer < 0:
                raise ValidationError(_('Odometer reading cannot be negative.'))

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_set_active(self):
        self.write({'status': 'active'})

    def action_set_maintenance(self):
        self.write({'status': 'maintenance'})

    def action_set_inactive(self):
        self.write({'status': 'inactive'})

    def action_set_retired(self):
        self.write({'status': 'retired', 'active': False})

    def action_view_trips(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('transit_ops.action_transit_trip')
        action['domain'] = [('vehicle_id', '=', self.id)]
        action['context'] = {'default_vehicle_id': self.id}
        return action

    def action_view_maintenance(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('transit_ops.action_transit_maintenance')
        action['domain'] = [('vehicle_id', '=', self.id)]
        action['context'] = {'default_vehicle_id': self.id}
        return action

    # ------------------------------------------------------------------
    # Cron
    # ------------------------------------------------------------------
    @api.model
    def _cron_check_document_expiry(self):
        """Scheduled action: notify responsible users about vehicles with
        documents that are expired or expiring within 30 days."""
        vehicles = self.search([('document_alert_level', 'in', ['warning', 'danger'])])
        Notification = self.env['transit.notification']
        for vehicle in vehicles:
            severity = 'high' if vehicle.document_alert_level == 'danger' else 'medium'
            message = _(
                '%(doc)s for vehicle %(vehicle)s expires on %(date)s.'
            ) % {
                'doc': vehicle.next_document_to_expire,
                'vehicle': vehicle.display_name,
                'date': vehicle.next_document_expiry_date,
            }
            existing = Notification.search([
                ('vehicle_id', '=', vehicle.id),
                ('notification_type', '=', 'document_expiry'),
                ('state', '=', 'unread'),
            ], limit=1)
            if not existing:
                Notification.create({
                    'title': _('Document Expiry Alert'),
                    'message': message,
                    'notification_type': 'document_expiry',
                    'severity': severity,
                    'vehicle_id': vehicle.id,
                })
        return True
