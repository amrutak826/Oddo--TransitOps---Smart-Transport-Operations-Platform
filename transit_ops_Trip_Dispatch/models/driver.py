# -*- coding: utf-8 -*-
from datetime import date

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class TransitDriver(models.Model):
    _name = 'transit.driver'
    _description = 'Transit Driver'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'
    _rec_name = 'name'

    name = fields.Char(string='Full Name', required=True, tracking=True)
    employee_code = fields.Char(string='Employee ID', copy=False)
    photo = fields.Image(string='Photo', max_width=1024, max_height=1024)

    license_number = fields.Char(string='License Number', required=True, tracking=True)
    license_type = fields.Selection([
        ('light', 'Light Motor Vehicle'),
        ('heavy', 'Heavy Motor Vehicle'),
        ('commercial', 'Commercial'),
        ('two_wheeler', 'Two Wheeler'),
    ], string='License Type', default='heavy', required=True)
    license_expiry = fields.Date(string='License Expiry', required=True, tracking=True)
    license_days_left = fields.Integer(
        string='License Days Left', compute='_compute_license_alert', store=True)
    license_alert = fields.Boolean(
        string='License Alert', compute='_compute_license_alert', store=True,
        help='True if license expires within 30 days or has already expired.')

    phone = fields.Char(string='Phone')
    mobile = fields.Char(string='Mobile', required=True)
    email = fields.Char(string='Email')
    address = fields.Text(string='Address')
    date_of_birth = fields.Date(string='Date of Birth')
    date_joined = fields.Date(string='Date Joined', default=fields.Date.context_today)

    status = fields.Selection([
        ('available', 'Available'),
        ('on_trip', 'On Trip'),
        ('off_duty', 'Off Duty'),
        ('suspended', 'Suspended'),
    ], string='Status', default='available', required=True, tracking=True)

    vehicle_id = fields.Many2one(
        'transit.vehicle', string='Assigned Vehicle', tracking=True)
    rating = fields.Float(string='Rating (out of 5)', default=5.0)
    total_trips = fields.Integer(string='Total Trips', default=0)

    user_id = fields.Many2one('res.users', string='Related User')
    active = fields.Boolean(default=True)
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company)

    _sql_constraints = [
        ('license_number_uniq', 'unique(license_number, company_id)',
         'A driver with this license number already exists!'),
    ]

    @api.depends('license_expiry')
    def _compute_license_alert(self):
        today = date.today()
        for driver in self:
            days = (driver.license_expiry - today).days if driver.license_expiry else 9999
            driver.license_days_left = days
            driver.license_alert = days <= 30

    @api.constrains('rating')
    def _check_rating(self):
        for driver in self:
            if driver.rating is not None and not (0 <= driver.rating <= 5):
                raise ValidationError('Rating must be between 0 and 5.')

    def action_set_available(self):
        self.write({'status': 'available'})

    def action_set_off_duty(self):
        self.write({'status': 'off_duty'})

    def action_suspend_driver(self):
        self.write({'status': 'suspended', 'vehicle_id': False})

    def name_get(self):
        result = []
        for driver in self:
            label = driver.name
            if driver.employee_code:
                label = f"{driver.name} [{driver.employee_code}]"
            result.append((driver.id, label))
        return result
