# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class TransitTrip(models.Model):
    _name = 'transit.trip'
    _description = 'Transit Trip'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'scheduled_departure desc, id desc'

    name = fields.Char(
        string='Trip Reference', copy=False, readonly=True,
        default=lambda self: _('New'))

    vehicle_id = fields.Many2one(
        'transit.vehicle', string='Vehicle', required=True, tracking=True,
        domain="[('status', 'in', ('active', 'on_trip'))]")
    driver_id = fields.Many2one(
        'transit.driver', string='Driver', required=True, tracking=True,
        domain="[('status', 'in', ('available', 'on_trip'))]")

    origin = fields.Char(string='Origin', required=True)
    destination = fields.Char(string='Destination', required=True)

    scheduled_departure = fields.Datetime(string='Scheduled Departure', required=True, tracking=True)
    scheduled_arrival = fields.Datetime(string='Scheduled Arrival')
    actual_departure = fields.Datetime(string='Actual Departure', readonly=True)
    actual_arrival = fields.Datetime(string='Actual Arrival', readonly=True)

    distance_km = fields.Float(string='Distance (km)')
    passenger_count = fields.Integer(string='Passenger Count')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)

    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company)

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('scheduled_departure', 'scheduled_arrival')
    def _check_schedule(self):
        for trip in self:
            if trip.scheduled_departure and trip.scheduled_arrival \
                    and trip.scheduled_arrival < trip.scheduled_departure:
                raise ValidationError(_(
                    'Scheduled arrival cannot be before scheduled departure.'))

    @api.constrains('distance_km')
    def _check_distance(self):
        for trip in self:
            if trip.distance_km < 0:
                raise ValidationError(_('Distance cannot be negative.'))

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('transit.trip') or _('New')
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Actions / State Machine
    # ------------------------------------------------------------------
    def action_confirm(self):
        for trip in self:
            if trip.state != 'draft':
                raise ValidationError(_('Only draft trips can be confirmed.'))
        self.write({'state': 'scheduled'})

    def action_start(self):
        for trip in self:
            if trip.state != 'scheduled':
                raise ValidationError(_('Only scheduled trips can be started.'))
            trip.vehicle_id.write({'status': 'on_trip'})
            trip.driver_id.write({'status': 'on_trip'})
        self.write({
            'state': 'in_progress',
            'actual_departure': fields.Datetime.now(),
        })

    def action_complete(self):
        for trip in self:
            if trip.state != 'in_progress':
                raise ValidationError(_('Only trips in progress can be completed.'))
            trip.vehicle_id.write({'status': 'active'})
            trip.driver_id.write({'status': 'available'})
        self.write({
            'state': 'completed',
            'actual_arrival': fields.Datetime.now(),
        })

    def action_cancel(self):
        for trip in self:
            if trip.state == 'in_progress':
                trip.vehicle_id.write({'status': 'active'})
                trip.driver_id.write({'status': 'available'})
        self.write({'state': 'cancelled'})

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})
