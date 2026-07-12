# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class TransitDriver(models.Model):
    _name = 'transit.driver'
    _description = 'Transit Driver'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name asc'

    # ------------------------------------------------------------------
    # Basic Information
    # ------------------------------------------------------------------
    name = fields.Char(string='Driver Name', required=True, tracking=True, index=True)
    driver_code = fields.Char(
        string='Driver Code', copy=False, readonly=True,
        default=lambda self: _('New'))
    photo = fields.Image(string='Photo', max_width=1024, max_height=1024)

    phone = fields.Char(string='Phone', tracking=True)
    mobile = fields.Char(string='Mobile')
    email = fields.Char(string='Email')
    address = fields.Text(string='Address')

    date_of_birth = fields.Date(string='Date of Birth')
    date_of_joining = fields.Date(string='Date of Joining', default=fields.Date.context_today)
    blood_group = fields.Selection([
        ('a+', 'A+'), ('a-', 'A-'),
        ('b+', 'B+'), ('b-', 'B-'),
        ('ab+', 'AB+'), ('ab-', 'AB-'),
        ('o+', 'O+'), ('o-', 'O-'),
    ], string='Blood Group')

    emergency_contact_name = fields.Char(string='Emergency Contact Name')
    emergency_contact_phone = fields.Char(string='Emergency Contact Phone')

    # ------------------------------------------------------------------
    # License Information
    # ------------------------------------------------------------------
    license_number = fields.Char(string='License Number', required=True, copy=False, tracking=True)
    license_type = fields.Selection([
        ('light', 'Light Motor Vehicle'),
        ('heavy', 'Heavy Motor Vehicle'),
        ('commercial', 'Commercial'),
        ('two_wheeler', 'Two Wheeler'),
    ], string='License Type', default='heavy')
    license_issue_date = fields.Date(string='License Issue Date')
    license_expiry = fields.Date(string='License Expiry', required=True, tracking=True)

    license_alert_level = fields.Selection([
        ('none', 'OK'),
        ('warning', 'Expiring Soon'),
        ('danger', 'Expired'),
    ], string='License Status', compute='_compute_license_alert_level', store=True)

    # ------------------------------------------------------------------
    # Employment / Status
    # ------------------------------------------------------------------
    status = fields.Selection([
        ('available', 'Available'),
        ('on_trip', 'On Trip'),
        ('on_leave', 'On Leave'),
        ('suspended', 'Suspended'),
        ('inactive', 'Inactive'),
    ], string='Status', default='available', required=True, tracking=True)

    employee_id = fields.Many2one('hr.employee', string='Linked Employee')
    user_id = fields.Many2one(
        'res.users', string='Linked User', tracking=True,
        help='Odoo user account for this driver, used for portal/app access '
             'and record-level security so the driver only sees their own data.')
    assigned_vehicle_id = fields.Many2one(
        'transit.vehicle', string='Assigned Vehicle', tracking=True)

    # ------------------------------------------------------------------
    # Relations & Stats
    # ------------------------------------------------------------------
    trip_ids = fields.One2many('transit.trip', 'driver_id', string='Trips')
    trip_count = fields.Integer(compute='_compute_trip_count', string='Trip Count')
    total_distance_km = fields.Float(
        compute='_compute_trip_stats', string='Total Distance (km)')
    completed_trip_count = fields.Integer(
        compute='_compute_trip_stats', string='Completed Trips')

    rating = fields.Float(string='Performance Rating', default=5.0, tracking=True)

    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company)

    _sql_constraints = [
        ('license_number_unique',
         'UNIQUE(license_number, company_id)',
         'A driver with this license number already exists!'),
    ]

    # ------------------------------------------------------------------
    # Compute Methods
    # ------------------------------------------------------------------
    @api.depends('license_expiry')
    def _compute_license_alert_level(self):
        today = fields.Date.context_today(self)
        warning_window = today + timedelta(days=30)
        for driver in self:
            if not driver.license_expiry:
                driver.license_alert_level = 'none'
            elif driver.license_expiry < today:
                driver.license_alert_level = 'danger'
            elif driver.license_expiry <= warning_window:
                driver.license_alert_level = 'warning'
            else:
                driver.license_alert_level = 'none'

    def _compute_trip_count(self):
        trip_data = self.env['transit.trip']._read_group(
            [('driver_id', 'in', self.ids)], ['driver_id'], ['__count'])
        mapped_data = {driver.id: count for driver, count in trip_data}
        for driver in self:
            driver.trip_count = mapped_data.get(driver.id, 0)

    def _compute_trip_stats(self):
        for driver in self:
            completed = driver.trip_ids.filtered(lambda t: t.state == 'completed')
            driver.completed_trip_count = len(completed)
            driver.total_distance_km = sum(completed.mapped('distance_km'))

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('rating')
    def _check_rating(self):
        for driver in self:
            if driver.rating < 0 or driver.rating > 5:
                raise ValidationError(_('Rating must be between 0 and 5.'))

    @api.constrains('email')
    def _check_email(self):
        for driver in self:
            if driver.email and '@' not in driver.email:
                raise ValidationError(_('Please enter a valid email address.'))

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('driver_code', _('New')) == _('New'):
                vals['driver_code'] = self.env['ir.sequence'].next_by_code(
                    'transit.driver') or _('New')
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_set_available(self):
        self.write({'status': 'available'})

    def action_set_on_leave(self):
        self.write({'status': 'on_leave'})

    def action_set_suspended(self):
        self.write({'status': 'suspended'})

    def action_view_trips(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('transit_ops.action_transit_trip')
        action['domain'] = [('driver_id', '=', self.id)]
        action['context'] = {'default_driver_id': self.id}
        return action

    # ------------------------------------------------------------------
    # Cron
    # ------------------------------------------------------------------
    @api.model
    def _cron_check_license_expiry(self):
        """Scheduled action: notify about driver licenses expiring soon or expired."""
        drivers = self.search([('license_alert_level', 'in', ['warning', 'danger'])])
        Notification = self.env['transit.notification']
        for driver in drivers:
            severity = 'high' if driver.license_alert_level == 'danger' else 'medium'
            message = _(
                'Driving license for %(driver)s expires on %(date)s.'
            ) % {'driver': driver.name, 'date': driver.license_expiry}
            existing = Notification.search([
                ('driver_id', '=', driver.id),
                ('notification_type', '=', 'license_expiry'),
                ('state', '=', 'unread'),
            ], limit=1)
            if not existing:
                Notification.create({
                    'title': _('License Expiry Alert'),
                    'message': message,
                    'notification_type': 'license_expiry',
                    'severity': severity,
                    'driver_id': driver.id,
                })
        return True
