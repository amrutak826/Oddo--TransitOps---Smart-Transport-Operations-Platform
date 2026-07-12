# -*- coding: utf-8 -*-
from datetime import date

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class TransitDriver(models.Model):
    _name = 'transit.driver'
    _description = 'Transit Driver'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name asc'
    _rec_name = 'name'

    # ------------------------------------------------------------------
    # Basic Info
    # ------------------------------------------------------------------
    name = fields.Char(string='Driver Name', required=True, tracking=True)
    employee_id = fields.Many2one(
        'hr.employee', string='Linked Employee',
        help='Optional link to an HR Employee record.'
    )
    photo = fields.Image(string='Photo', max_width=1024, max_height=1024)

    phone = fields.Char(string='Phone', tracking=True)
    mobile = fields.Char(string='Mobile')
    email = fields.Char(string='Email')
    address = fields.Text(string='Address')
    date_of_birth = fields.Date(string='Date of Birth')
    blood_group = fields.Selection([
        ('a+', 'A+'), ('a-', 'A-'),
        ('b+', 'B+'), ('b-', 'B-'),
        ('ab+', 'AB+'), ('ab-', 'AB-'),
        ('o+', 'O+'), ('o-', 'O-'),
    ], string='Blood Group')

    emergency_contact_name = fields.Char(string='Emergency Contact Name')
    emergency_contact_phone = fields.Char(string='Emergency Contact Phone')

    # ------------------------------------------------------------------
    # License Info
    # ------------------------------------------------------------------
    license_number = fields.Char(string='License Number', required=True, copy=False, tracking=True)
    license_type = fields.Selection([
        ('lmv', 'LMV - Light Motor Vehicle'),
        ('hmv', 'HMV - Heavy Motor Vehicle'),
        ('transport', 'Transport License'),
        ('motorcycle', 'Motorcycle'),
    ], string='License Type', default='lmv', required=True)
    license_expiry = fields.Date(string='License Expiry', required=True, tracking=True)
    license_status = fields.Selection([
        ('valid', 'Valid'),
        ('expiring_soon', 'Expiring Soon'),
        ('expired', 'Expired'),
    ], string='License Status', compute='_compute_license_status', store=True, tracking=True)

    date_joined = fields.Date(string='Date Joined', default=fields.Date.context_today)

    # ------------------------------------------------------------------
    # Status & Assignment
    # ------------------------------------------------------------------
    status = fields.Selection([
        ('available', 'Available'),
        ('on_trip', 'On Trip'),
        ('on_leave', 'On Leave'),
        ('inactive', 'Inactive'),
    ], string='Status', default='available', required=True, tracking=True)

    current_vehicle_id = fields.Many2one(
        'transit.vehicle', string='Current Vehicle',
        compute='_compute_current_vehicle', store=False
    )

    rating = fields.Float(string='Performance Rating', default=0.0, help='Rating out of 5.0')

    trip_ids = fields.One2many('transit.trip', 'driver_id', string='Trips')
    trip_count = fields.Integer(string='Trip Count', compute='_compute_trip_count')

    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company
    )
    notes = fields.Text(string='Notes')

    # ------------------------------------------------------------------
    # Compute Methods
    # ------------------------------------------------------------------
    @api.depends('license_expiry')
    def _compute_license_status(self):
        today = date.today()
        for driver in self:
            if not driver.license_expiry:
                driver.license_status = 'valid'
            elif driver.license_expiry < today:
                driver.license_status = 'expired'
            elif (driver.license_expiry - today).days <= 30:
                driver.license_status = 'expiring_soon'
            else:
                driver.license_status = 'valid'

    def _compute_current_vehicle(self):
        for driver in self:
            vehicle = self.env['transit.vehicle'].search(
                [('current_driver_id', '=', driver.id)], limit=1
            )
            driver.current_vehicle_id = vehicle.id if vehicle else False

    def _compute_trip_count(self):
        for driver in self:
            driver.trip_count = len(driver.trip_ids)

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('date_of_birth')
    def _check_minimum_age(self):
        today = date.today()
        for driver in self:
            if driver.date_of_birth:
                age = today.year - driver.date_of_birth.year - (
                    (today.month, today.day) < (driver.date_of_birth.month, driver.date_of_birth.day)
                )
                if age < 18:
                    raise ValidationError(_('Driver must be at least 18 years old.'))

    @api.constrains('rating')
    def _check_rating(self):
        for driver in self:
            if driver.rating < 0 or driver.rating > 5:
                raise ValidationError(_('Rating must be between 0 and 5.'))

    _sql_constraints = [
        (
            'license_number_unique',
            'unique(license_number, company_id)',
            'A driver with this license number already exists!'
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
            'domain': [('driver_id', '=', self.id)],
            'context': {'default_driver_id': self.id},
        }

    def action_set_on_leave(self):
        for driver in self:
            driver.status = 'on_leave'

    def action_set_available(self):
        for driver in self:
            driver.status = 'available'

    def action_set_inactive(self):
        for driver in self:
            driver.status = 'inactive'
            driver.active = False
