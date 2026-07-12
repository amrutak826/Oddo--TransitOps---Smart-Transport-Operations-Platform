# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class TransitDriver(models.Model):
    _name = 'transit.driver'
    _description = 'Transit Driver'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name asc'
    _rec_name = 'display_name'

    name = fields.Char(string='Driver Name', required=True, tracking=True)
    display_name = fields.Char(compute='_compute_display_name', store=True)
    employee_code = fields.Char(string='Employee Code', copy=False)
    image_1920 = fields.Image(string='Photo', max_width=1920, max_height=1920)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company, required=True,
    )
    user_id = fields.Many2one('res.users', string='Related User', tracking=True,
                               help='Login user linked to this driver, used for record-level access.')

    phone = fields.Char(string='Phone')
    mobile = fields.Char(string='Mobile')
    email = fields.Char(string='Email')
    address = fields.Text(string='Address')
    date_of_birth = fields.Date(string='Date of Birth')
    date_of_joining = fields.Date(string='Date of Joining', default=fields.Date.context_today)

    license_number = fields.Char(string='License Number', required=True, copy=False, tracking=True)
    license_type = fields.Selection([
        ('lmv', 'Light Motor Vehicle'),
        ('hmv', 'Heavy Motor Vehicle'),
        ('transport', 'Transport / Commercial'),
        ('motorcycle', 'Motorcycle'),
    ], string='License Type', required=True, default='lmv')
    license_expiry_date = fields.Date(string='License Expiry', tracking=True)
    license_alert_state = fields.Selection([
        ('ok', 'Valid'),
        ('warning', 'Expiring Soon'),
        ('expired', 'Expired'),
    ], string='License Status', compute='_compute_license_alert_state', store=True, tracking=True)

    state = fields.Selection([
        ('available', 'Available'),
        ('on_trip', 'On Trip'),
        ('on_leave', 'On Leave'),
        ('inactive', 'Inactive'),
    ], string='Status', default='available', required=True, tracking=True, copy=False)

    vehicle_ids = fields.One2many('transit.vehicle', 'default_driver_id', string='Assigned Vehicles')
    trip_ids = fields.One2many('transit.trip', 'driver_id', string='Trips')
    trip_count = fields.Integer(compute='_compute_trip_count', string='Trip Count')
    vehicle_count = fields.Integer(compute='_compute_vehicle_count', string='Vehicle Count')

    notes = fields.Html(string='Internal Notes')

    _sql_constraints = [
        ('license_number_unique', 'unique(license_number, company_id)',
         'This license number is already registered for another driver in this company!'),
    ]

    @api.depends('name', 'employee_code')
    def _compute_display_name(self):
        for driver in self:
            if driver.employee_code:
                driver.display_name = f"{driver.name} [{driver.employee_code}]"
            else:
                driver.display_name = driver.name or _('New Driver')

    @api.depends('license_expiry_date')
    def _compute_license_alert_state(self):
        today = fields.Date.context_today(self)
        warning_horizon = today + timedelta(days=30)
        for driver in self:
            if not driver.license_expiry_date:
                driver.license_alert_state = 'ok'
            elif driver.license_expiry_date < today:
                driver.license_alert_state = 'expired'
            elif driver.license_expiry_date <= warning_horizon:
                driver.license_alert_state = 'warning'
            else:
                driver.license_alert_state = 'ok'

    def _compute_trip_count(self):
        data = self.env['transit.trip']._read_group(
            [('driver_id', 'in', self.ids)], ['driver_id'], ['__count'],
        )
        mapped_data = {driver.id: count for driver, count in data}
        for driver in self:
            driver.trip_count = mapped_data.get(driver.id, 0)

    def _compute_vehicle_count(self):
        data = self.env['transit.vehicle']._read_group(
            [('default_driver_id', 'in', self.ids)], ['default_driver_id'], ['__count'],
        )
        mapped_data = {driver.id: count for driver, count in data}
        for driver in self:
            driver.vehicle_count = mapped_data.get(driver.id, 0)

    @api.constrains('date_of_birth')
    def _check_date_of_birth(self):
        today = fields.Date.context_today(self)
        for driver in self:
            if driver.date_of_birth and driver.date_of_birth > today:
                raise ValidationError(_('Date of Birth cannot be in the future.'))

    def action_set_available(self):
        self.write({'state': 'available'})

    def action_set_on_leave(self):
        self.write({'state': 'on_leave'})

    def action_set_inactive(self):
        self.write({'state': 'inactive', 'active': False})

    def action_view_trips(self):
        self.ensure_one()
        return {
            'name': _('Trips'),
            'type': 'ir.actions.act_window',
            'res_model': 'transit.trip',
            'view_mode': 'list,form,calendar',
            'domain': [('driver_id', '=', self.id)],
            'context': {'default_driver_id': self.id},
        }

    def action_view_vehicles(self):
        self.ensure_one()
        return {
            'name': _('Assigned Vehicles'),
            'type': 'ir.actions.act_window',
            'res_model': 'transit.vehicle',
            'view_mode': 'list,form,kanban',
            'domain': [('default_driver_id', '=', self.id)],
            'context': {'default_default_driver_id': self.id},
        }

    @api.model
    def _cron_check_driver_licenses(self):
        today = fields.Date.context_today(self)
        warning_horizon = today + timedelta(days=30)
        drivers = self.search([
            ('active', '=', True),
            ('license_expiry_date', '!=', False),
            ('license_expiry_date', '<=', warning_horizon),
        ])
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        if not activity_type:
            return
        manager_group = self.env.ref('transit_ops.group_transit_manager', raise_if_not_found=False)
        responsible_user = self.env.user
        if manager_group and manager_group.users:
            responsible_user = manager_group.users[0]

        for driver in drivers:
            status = _('EXPIRED') if driver.license_expiry_date < today else _('expiring soon')
            note = _('Driving license %(status)s on %(date)s.', status=status, date=driver.license_expiry_date)
            existing = self.env['mail.activity'].search([
                ('res_model', '=', 'transit.driver'),
                ('res_id', '=', driver.id),
                ('activity_type_id', '=', activity_type.id),
                ('summary', '=', _('Driver License Expiry Alert')),
            ], limit=1)
            if existing:
                existing.write({'note': note})
            else:
                driver.activity_schedule(
                    activity_type_id=activity_type.id,
                    summary=_('Driver License Expiry Alert'),
                    note=note,
                    user_id=responsible_user.id,
                    date_deadline=today,
                )
