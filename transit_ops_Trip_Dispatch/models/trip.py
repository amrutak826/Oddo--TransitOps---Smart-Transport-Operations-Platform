# -*- coding: utf-8 -*-
from datetime import date

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class TransitTrip(models.Model):
    _name = 'transit.trip'
    _description = 'Transit Trip Dispatch'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'trip_date desc, start_time desc, id desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Trip Number', required=True, copy=False, readonly=True,
        default=lambda self: _('New'), tracking=True)

    pickup_location = fields.Char(string='Pickup', required=True, tracking=True)
    destination = fields.Char(string='Destination', required=True, tracking=True)
    distance = fields.Float(string='Distance (km)', default=0.0)

    vehicle_id = fields.Many2one(
        'transit.vehicle', string='Vehicle', required=True, tracking=True,
        domain="[('status', 'not in', ('maintenance', 'retired', 'inactive'))]")
    driver_id = fields.Many2one(
        'transit.driver', string='Driver', required=True, tracking=True,
        domain="[('status', '!=', 'suspended')]")

    trip_date = fields.Date(
        string='Trip Date', required=True, default=fields.Date.context_today, tracking=True)
    start_time = fields.Float(string='Start Time', widget='float_time', required=True, default=9.0)
    end_time = fields.Float(string='End Time', widget='float_time', required=True, default=11.0)

    status = fields.Selection([
        ('draft', 'Draft'),
        ('assigned', 'Assigned'),
        ('in_transit', 'In Transit'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True, copy=False)

    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Urgent'),
    ], string='Priority', default='1', tracking=True)

    fuel_used = fields.Float(string='Fuel Used (L)', default=0.0)
    remarks = fields.Text(string='Remarks')

    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company)

    _sql_constraints = [
        ('check_time_range', 'CHECK(end_time >= start_time)',
         'End time must be after start time!'),
        ('check_distance_positive', 'CHECK(distance >= 0)',
         'Distance cannot be negative!'),
        ('check_fuel_positive', 'CHECK(fuel_used >= 0)',
         'Fuel used cannot be negative!'),
    ]

    # ============================================================
    # CRUD
    # ============================================================
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('transit.trip') or _('New')
        return super().create(vals_list)

    # ============================================================
    # CONSTRAINTS / BUSINESS RULES
    # ============================================================
    @api.constrains('vehicle_id', 'driver_id', 'trip_date', 'start_time', 'end_time', 'status')
    def _check_double_booking(self):
        """A vehicle or driver cannot be assigned to two overlapping active trips."""
        active_states = ('assigned', 'in_transit')
        for trip in self:
            if trip.status not in active_states:
                continue
            if not trip.vehicle_id or not trip.driver_id or not trip.trip_date:
                continue

            overlap_domain_base = [
                ('id', '!=', trip.id),
                ('trip_date', '=', trip.trip_date),
                ('status', 'in', active_states),
                ('start_time', '<', trip.end_time),
                ('end_time', '>', trip.start_time),
            ]

            vehicle_conflict = self.search_count(
                overlap_domain_base + [('vehicle_id', '=', trip.vehicle_id.id)])
            if vehicle_conflict:
                raise ValidationError(_(
                    'Vehicle "%s" is already assigned to another trip that overlaps with '
                    'this time slot on %s. A vehicle cannot be assigned twice.'
                ) % (trip.vehicle_id.name, trip.trip_date))

            driver_conflict = self.search_count(
                overlap_domain_base + [('driver_id', '=', trip.driver_id.id)])
            if driver_conflict:
                raise ValidationError(_(
                    'Driver "%s" is already assigned to another trip that overlaps with '
                    'this time slot on %s. A driver cannot be assigned twice.'
                ) % (trip.driver_id.name, trip.trip_date))

    @api.constrains('vehicle_id', 'status')
    def _check_vehicle_maintenance(self):
        active_states = ('assigned', 'in_transit')
        for trip in self:
            if trip.status in active_states and trip.vehicle_id.status == 'maintenance':
                raise ValidationError(_(
                    'Vehicle "%s" is currently under maintenance and cannot be assigned to a trip.'
                ) % trip.vehicle_id.name)
            if trip.status in active_states and trip.vehicle_id.status == 'retired':
                raise ValidationError(_(
                    'Vehicle "%s" is retired and cannot be assigned to a trip.'
                ) % trip.vehicle_id.name)

    @api.constrains('driver_id', 'status')
    def _check_driver_license(self):
        active_states = ('assigned', 'in_transit')
        today = date.today()
        for trip in self:
            if trip.status not in active_states:
                continue
            if not trip.driver_id.license_expiry or trip.driver_id.license_expiry < today:
                raise ValidationError(_(
                    'Driver "%s" has an expired (or missing) license and cannot be assigned to a trip.'
                ) % trip.driver_id.name)
            if trip.driver_id.status == 'suspended':
                raise ValidationError(_(
                    'Driver "%s" is suspended and cannot be assigned to a trip.'
                ) % trip.driver_id.name)

    # ============================================================
    # WORKFLOW ACTIONS
    # ============================================================
    def action_assign(self):
        for trip in self:
            if not trip.vehicle_id or not trip.driver_id:
                raise UserError(_('Please select both a vehicle and a driver before assigning.'))
            trip.status = 'assigned'
        return True

    def action_start_trip(self):
        for trip in self:
            if trip.status != 'assigned':
                raise UserError(_('Only assigned trips can be started.'))
            trip.status = 'in_transit'
            trip.vehicle_id.write({'status': 'on_trip'})
            trip.driver_id.write({'status': 'on_trip'})
        return True

    def action_complete_trip(self):
        for trip in self:
            if trip.status != 'in_transit':
                raise UserError(_('Only trips that are in transit can be completed.'))
            trip.status = 'completed'
            if trip.vehicle_id:
                trip.vehicle_id.write({
                    'status': 'active',
                    'odometer': trip.vehicle_id.odometer + trip.distance,
                    'trip_count': trip.vehicle_id.trip_count + 1,
                })
            if trip.driver_id:
                trip.driver_id.write({
                    'status': 'available',
                    'total_trips': trip.driver_id.total_trips + 1,
                })
        return True

    def action_cancel_trip(self):
        for trip in self:
            if trip.status == 'completed':
                raise UserError(_('A completed trip cannot be cancelled.'))
            if trip.status == 'in_transit':
                if trip.vehicle_id:
                    trip.vehicle_id.write({'status': 'active'})
                if trip.driver_id:
                    trip.driver_id.write({'status': 'available'})
            trip.status = 'cancelled'
        return True

    def action_reset_to_draft(self):
        for trip in self:
            if trip.status != 'cancelled':
                raise UserError(_('Only cancelled trips can be reset to draft.'))
            trip.status = 'draft'
        return True

    # ============================================================
    # ONCHANGE
    # ============================================================
    @api.onchange('pickup_location', 'destination')
    def _onchange_locations_warning(self):
        if self.pickup_location and self.destination and \
                self.pickup_location.strip().lower() == self.destination.strip().lower():
            return {'warning': {
                'title': _('Same Location'),
                'message': _('Pickup and destination appear to be the same location.'),
            }}
