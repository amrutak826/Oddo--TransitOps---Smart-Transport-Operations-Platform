# -*- coding: utf-8 -*-
from odoo import api, fields, models


class TransitDriver(models.Model):
    _name = 'transit.driver'
    _description = 'Transit Driver'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name asc'
    _rec_name = 'name'

    name = fields.Char(string='Driver Name', required=True, tracking=True)
    driver_code = fields.Char(
        string='Driver Code', required=True, copy=False, readonly=True,
        default=lambda self: 'New'
    )
    user_id = fields.Many2one(
        'res.users', string='Related User', tracking=True,
        help='Login user linked to this driver, used for record-rule based access '
             'and for routing personal notifications.'
    )
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')

    license_number = fields.Char(string='License Number', tracking=True)
    license_expiry_date = fields.Date(string='License Expiry Date', tracking=True)

    state = fields.Selection([
        ('active', 'Active'),
        ('on_leave', 'On Leave'),
        ('inactive', 'Inactive'),
    ], string='Status', default='active', tracking=True, required=True)

    vehicle_ids = fields.One2many('transit.vehicle', 'driver_id', string='Assigned Vehicles')
    trip_ids = fields.One2many('transit.trip', 'driver_id', string='Trips')

    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company, required=True
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('license_number_unique', 'unique(license_number, company_id)',
         'A driver with this license number already exists!'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('driver_code', 'New') == 'New':
                vals['driver_code'] = self.env['ir.sequence'].next_by_code('transit.driver') or 'New'
        return super().create(vals_list)
