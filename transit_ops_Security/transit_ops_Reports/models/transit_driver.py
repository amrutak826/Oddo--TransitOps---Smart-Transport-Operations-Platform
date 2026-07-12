# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class TransitDriver(models.Model):
    _name = 'transit.driver'
    _description = 'Transport Driver'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'
    _rec_name = 'name'

    name = fields.Char(string='Driver Name', required=True, tracking=True)
    sequence_code = fields.Char(string='Driver Code', copy=False, readonly=True,
                                 default=lambda self: _('New'))
    user_id = fields.Many2one('res.users', string='Related User', tracking=True,
                               help='Linked backend user, used for record-level security '
                                    'so a driver only sees their own trips/logs.')
    image = fields.Image(string='Photo', max_width=1024, max_height=1024)

    phone = fields.Char(string='Phone')
    mobile = fields.Char(string='Mobile')
    email = fields.Char(string='Email')
    address = fields.Text(string='Address')

    license_number = fields.Char(string='License Number', required=True, copy=False, tracking=True)
    license_type = fields.Selection([
        ('lmv', 'LMV'),
        ('hmv', 'HMV'),
        ('psv', 'PSV (Public Service Vehicle)'),
        ('motorcycle', 'Motorcycle'),
    ], string='License Type', default='hmv')
    license_expiry = fields.Date(string='License Expiry', tracking=True)
    license_status = fields.Selection([
        ('valid', 'Valid'),
        ('expiring_soon', 'Expiring Soon'),
        ('expired', 'Expired'),
    ], string='License Status', compute='_compute_license_status', store=True)

    date_joined = fields.Date(string='Date Joined', default=fields.Date.context_today)
    experience_years = fields.Integer(string='Years of Experience')

    state = fields.Selection([
        ('available', 'Available'),
        ('on_trip', 'On Trip'),
        ('on_leave', 'On Leave'),
        ('inactive', 'Inactive'),
    ], string='Status', default='available', tracking=True, index=True)
    active = fields.Boolean(default=True)

    vehicle_ids = fields.One2many('transit.vehicle', 'driver_id', string='Assigned Vehicles')
    vehicle_count = fields.Integer(compute='_compute_vehicle_count')

    trip_ids = fields.One2many('transit.trip', 'driver_id', string='Trips')
    trip_count = fields.Integer(compute='_compute_trip_count')

    fuel_log_ids = fields.One2many('transit.fuel.log', 'driver_id', string='Fuel Logs')
    expense_ids = fields.One2many('transit.expense', 'driver_id', string='Expenses')

    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    notes = fields.Text(string='Internal Notes')

    _sql_constraints = [
        ('license_number_uniq', 'unique(license_number, company_id)',
         'A driver with this license number already exists!'),
    ]

    @api.depends('license_expiry')
    def _compute_license_status(self):
        today = fields.Date.context_today(self)
        warn_before = today + timedelta(days=30)
        for rec in self:
            if not rec.license_expiry:
                rec.license_status = 'valid'
            elif rec.license_expiry < today:
                rec.license_status = 'expired'
            elif rec.license_expiry <= warn_before:
                rec.license_status = 'expiring_soon'
            else:
                rec.license_status = 'valid'

    def _compute_vehicle_count(self):
        for rec in self:
            rec.vehicle_count = len(rec.vehicle_ids)

    def _compute_trip_count(self):
        for rec in self:
            rec.trip_count = len(rec.trip_ids)

    @api.constrains('experience_years')
    def _check_experience(self):
        for rec in self:
            if rec.experience_years and rec.experience_years < 0:
                raise ValidationError(_('Years of experience cannot be negative.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('sequence_code', _('New')) == _('New'):
                vals['sequence_code'] = self.env['ir.sequence'].next_by_code(
                    'transit.driver') or _('New')
        return super().create(vals_list)

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
