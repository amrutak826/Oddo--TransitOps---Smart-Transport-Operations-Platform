# -*- coding: utf-8 -*-
from odoo import api, fields, models


class TransitTrip(models.Model):
    _name = 'transit.trip'
    _description = 'Transit Trip'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'scheduled_departure desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Trip Reference', required=True, copy=False, readonly=True,
        default=lambda self: 'New'
    )
    vehicle_id = fields.Many2one('transit.vehicle', string='Vehicle', tracking=True)
    driver_id = fields.Many2one('transit.driver', string='Driver', tracking=True)

    origin = fields.Char(string='Origin')
    destination = fields.Char(string='Destination')

    scheduled_departure = fields.Datetime(string='Scheduled Departure', tracking=True)
    scheduled_arrival = fields.Datetime(string='Scheduled Arrival', tracking=True)
    actual_departure = fields.Datetime(string='Actual Departure')
    actual_arrival = fields.Datetime(string='Actual Arrival')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('ongoing', 'Ongoing'),
        ('delayed', 'Delayed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, required=True)

    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company, required=True
    )
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('transit.trip') or 'New'
        return super().create(vals_list)

    def action_start_trip(self):
        self.write({'state': 'ongoing', 'actual_departure': fields.Datetime.now()})

    def action_complete_trip(self):
        self.write({'state': 'completed', 'actual_arrival': fields.Datetime.now()})

    def action_cancel_trip(self):
        self.write({'state': 'cancelled'})
