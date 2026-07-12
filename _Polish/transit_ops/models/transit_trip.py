# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class TransitTrip(models.Model):
    _name = 'transit.trip'
    _description = 'Transit Trip'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'scheduled_departure desc, id desc'
    _rec_name = 'name'

    name = fields.Char(string='Trip Reference', required=True, copy=False,
                        readonly=True, default=lambda self: _('New'))
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company, required=True,
    )
    active = fields.Boolean(default=True)

    vehicle_id = fields.Many2one('transit.vehicle', string='Vehicle', required=True, tracking=True)
    driver_id = fields.Many2one('transit.driver', string='Driver', required=True, tracking=True)

    origin = fields.Char(string='Origin', required=True)
    destination = fields.Char(string='Destination', required=True)
    purpose = fields.Char(string='Purpose')
    passenger_count = fields.Integer(string='Passenger Count')
    distance_km = fields.Float(string='Distance (km)')

    scheduled_departure = fields.Datetime(string='Scheduled Departure', required=True, tracking=True)
    scheduled_arrival = fields.Datetime(string='Scheduled Arrival', required=True, tracking=True)
    actual_departure = fields.Datetime(string='Actual Departure', copy=False)
    actual_arrival = fields.Datetime(string='Actual Arrival', copy=False)

    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'High'),
        ('2', 'Urgent'),
    ], string='Priority', default='0')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True, copy=False)

    notes = fields.Html(string='Notes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('transit.trip') or _('New')
        return super().create(vals_list)

    @api.constrains('scheduled_departure', 'scheduled_arrival')
    def _check_schedule_window(self):
        for trip in self:
            if trip.scheduled_departure and trip.scheduled_arrival \
                    and trip.scheduled_arrival <= trip.scheduled_departure:
                raise ValidationError(_('Scheduled Arrival must be after Scheduled Departure.'))

    @api.constrains('distance_km')
    def _check_distance(self):
        for trip in self:
            if trip.distance_km < 0:
                raise ValidationError(_('Distance cannot be negative.'))

    def action_confirm(self):
        for trip in self:
            if trip.state != 'draft':
                raise UserError(_('Only draft trips can be confirmed.'))
            trip.state = 'scheduled'

    def action_start(self):
        for trip in self:
            if trip.state != 'scheduled':
                raise UserError(_('Only scheduled trips can be started.'))
            if trip.vehicle_id.state == 'maintenance':
                raise UserError(_('Vehicle is under maintenance and cannot start a trip.'))
            trip.write({
                'state': 'in_progress',
                'actual_departure': fields.Datetime.now(),
            })
            trip.vehicle_id.write({'state': 'on_trip'})
            trip.driver_id.write({'state': 'on_trip'})

    def action_complete(self):
        for trip in self:
            if trip.state != 'in_progress':
                raise UserError(_('Only trips in progress can be completed.'))
            trip.write({
                'state': 'completed',
                'actual_arrival': fields.Datetime.now(),
            })
            trip.vehicle_id.write({'state': 'active'})
            trip.driver_id.write({'state': 'available'})
            if trip.distance_km:
                new_odometer = trip.vehicle_id.odometer + trip.distance_km
                if new_odometer > trip.vehicle_id.odometer:
                    trip.vehicle_id.write({'odometer': new_odometer})

    def action_cancel(self):
        for trip in self:
            if trip.state in ('completed', 'cancelled'):
                raise UserError(_('This trip cannot be cancelled from its current status.'))
            if trip.state == 'in_progress':
                trip.vehicle_id.write({'state': 'active'})
                trip.driver_id.write({'state': 'available'})
            trip.state = 'cancelled'

    def action_reset_draft(self):
        for trip in self:
            trip.write({
                'state': 'draft',
                'actual_departure': False,
                'actual_arrival': False,
            })
