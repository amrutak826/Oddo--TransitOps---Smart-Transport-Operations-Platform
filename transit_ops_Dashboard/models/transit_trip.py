# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class TransitTrip(models.Model):
    _name = 'transit.trip'
    _description = 'Trip Dispatch'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'scheduled_start desc'
    _rec_name = 'name'

    name = fields.Char(string='Trip Reference', copy=False, readonly=True,
                        default=lambda self: _('New'))

    vehicle_id = fields.Many2one('transit.vehicle', string='Vehicle', required=True, tracking=True)
    driver_id = fields.Many2one('transit.driver', string='Driver', required=True, tracking=True)

    origin = fields.Char(string='Origin', required=True)
    destination = fields.Char(string='Destination', required=True)

    scheduled_start = fields.Datetime(string='Scheduled Start', required=True, tracking=True,
                                       default=fields.Datetime.now)
    scheduled_end = fields.Datetime(string='Scheduled End')
    actual_start = fields.Datetime(string='Actual Start')
    actual_end = fields.Datetime(string='Actual End')

    distance_km = fields.Float(string='Distance (km)')
    passenger_count = fields.Integer(string='Passenger Count')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, index=True)

    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'High'),
        ('2', 'Urgent'),
    ], string='Priority', default='0')

    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    notes = fields.Text(string='Trip Notes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('transit.trip') or _('New')
        trips = super().create(vals_list)
        for trip in trips:
            if trip.state in ('scheduled', 'in_progress'):
                trip.vehicle_id.state = 'on_trip'
                trip.driver_id.state = 'on_trip'
        return trips

    @api.constrains('scheduled_start', 'scheduled_end')
    def _check_schedule(self):
        for rec in self:
            if rec.scheduled_start and rec.scheduled_end and rec.scheduled_end < rec.scheduled_start:
                raise ValidationError(_('Scheduled end must be after scheduled start.'))

    def action_confirm(self):
        for rec in self:
            rec.state = 'scheduled'
            rec.vehicle_id.state = 'on_trip'
            rec.driver_id.state = 'on_trip'

    def action_start(self):
        for rec in self:
            rec.write({'state': 'in_progress', 'actual_start': fields.Datetime.now()})

    def action_complete(self):
        for rec in self:
            rec.write({'state': 'completed', 'actual_end': fields.Datetime.now()})
            rec.vehicle_id.state = 'available'
            rec.driver_id.state = 'available'
            if rec.distance_km:
                rec.vehicle_id.odometer += rec.distance_km

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'
            rec.vehicle_id.state = 'available'
            rec.driver_id.state = 'available'

    def action_reset_draft(self):
        self.write({'state': 'draft'})
