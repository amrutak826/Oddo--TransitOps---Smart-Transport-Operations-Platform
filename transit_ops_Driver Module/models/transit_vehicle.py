# -*- coding: utf-8 -*-

from datetime import date

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class TransitVehicle(models.Model):
    _name = 'transit.vehicle'
    _description = 'Transit Vehicle'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'vehicle_number'
    _order = 'vehicle_number'

    # ------------------------------------------------------------------
    # Selections
    # ------------------------------------------------------------------
    VEHICLE_TYPE_SELECTION = [
        ('bus', 'Bus'),
        ('mini_bus', 'Mini Bus'),
        ('van', 'Van'),
        ('truck', 'Truck'),
        ('car', 'Car'),
        ('other', 'Other'),
    ]

    FUEL_TYPE_SELECTION = [
        ('diesel', 'Diesel'),
        ('petrol', 'Petrol'),
        ('cng', 'CNG'),
        ('electric', 'Electric'),
        ('hybrid', 'Hybrid'),
    ]

    STATUS_SELECTION = [
        ('available', 'Available'),
        ('on_trip', 'On Trip'),
        ('expired_docs', 'Documents Expired'),
        ('inactive', 'Inactive'),
    ]

    # ------------------------------------------------------------------
    # Core identification
    # ------------------------------------------------------------------
    vehicle_number = fields.Char(
        string='Vehicle Number', required=True, copy=False, tracking=True,
        help="Unique registration/license plate number, e.g. KA-01-AB-1234.")
    vehicle_type = fields.Selection(
        VEHICLE_TYPE_SELECTION, string='Vehicle Type', required=True,
        default='bus', tracking=True)
    brand = fields.Char(string='Brand')
    vehicle_model = fields.Char(string='Model')
    manufacturing_year = fields.Integer(string='Manufacturing Year')
    capacity = fields.Integer(string='Capacity', help="Seating capacity of the vehicle.")
    fuel_type = fields.Selection(
        FUEL_TYPE_SELECTION, string='Fuel Type', required=True, default='diesel')
    current_km = fields.Float(string='Current KM', digits=(16, 1), tracking=True,
                               help="Latest recorded odometer reading.")

    # ------------------------------------------------------------------
    # Documents / dates
    # ------------------------------------------------------------------
    registration_date = fields.Date(string='Registration Date', required=True,
                                     default=fields.Date.context_today)
    insurance_expiry = fields.Date(string='Insurance Expiry', required=True, tracking=True)
    fitness_expiry = fields.Date(string='Fitness Expiry', required=True, tracking=True)

    # ------------------------------------------------------------------
    # Status & assignment
    # ------------------------------------------------------------------
    status = fields.Selection(
        STATUS_SELECTION, string='Status', compute='_compute_status',
        store=True, tracking=True,
        help="Automatically derived from the vehicle's active flag, "
             "document validity and current trip assignment.")
    assigned_driver_id = fields.Many2one(
        'transit.driver', string='Assigned Driver', tracking=True,
        domain="[('active', '=', True)]")
    assigned_trip_id = fields.Many2one(
        'transit.trip', string='Assigned Trip', tracking=True,
        help="The trip this vehicle is currently allocated to, if any.")

    # ------------------------------------------------------------------
    # Media / notes
    # ------------------------------------------------------------------
    image_1920 = fields.Image(string='Image', max_width=1920, max_height=1920)
    image_128 = fields.Image(string='Image (Thumbnail)', related='image_1920',
                              max_width=128, max_height=128, store=True)
    notes = fields.Text(string='Notes')

    # ------------------------------------------------------------------
    # Misc / smart button support
    # ------------------------------------------------------------------
    active = fields.Boolean(string='Active', default=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    trip_count = fields.Integer(string='Trip Count', compute='_compute_trip_count')

    _sql_constraints = [
        ('vehicle_number_unique', 'unique(vehicle_number)',
         'Vehicle Number must be unique! A vehicle with this number already exists.'),
    ]

    # ==================================================================
    # Compute methods
    # ==================================================================
    @api.depends('active', 'insurance_expiry', 'fitness_expiry',
                 'assigned_trip_id', 'assigned_trip_id.state')
    def _compute_status(self):
        today = fields.Date.context_today(self)
        for vehicle in self:
            if not vehicle.active:
                vehicle.status = 'inactive'
            elif ((vehicle.insurance_expiry and vehicle.insurance_expiry < today) or
                    (vehicle.fitness_expiry and vehicle.fitness_expiry < today)):
                vehicle.status = 'expired_docs'
            elif vehicle.assigned_trip_id and vehicle.assigned_trip_id.state == 'ongoing':
                vehicle.status = 'on_trip'
            else:
                vehicle.status = 'available'

    def _compute_trip_count(self):
        trip_data = self.env['transit.trip']._read_group(
            [('vehicle_id', 'in', self.ids)], ['vehicle_id'], ['__count'])
        counts = {vehicle.id: count for vehicle, count in trip_data}
        for vehicle in self:
            vehicle.trip_count = counts.get(vehicle.id, 0)

    def _compute_display_name(self):
        for vehicle in self:
            label = vehicle.vehicle_number or _('New')
            extra = ' '.join(filter(None, [vehicle.brand, vehicle.vehicle_model]))
            vehicle.display_name = f"{label} ({extra})" if extra else label

    # ==================================================================
    # Constraints
    # ==================================================================
    @api.constrains('registration_date', 'insurance_expiry', 'fitness_expiry')
    def _check_expiry_dates(self):
        for vehicle in self:
            if vehicle.registration_date and vehicle.insurance_expiry \
                    and vehicle.insurance_expiry <= vehicle.registration_date:
                raise ValidationError(_(
                    "Insurance Expiry (%(expiry)s) must be after the Registration Date (%(reg)s) "
                    "for vehicle %(vehicle)s.") % {
                        'expiry': vehicle.insurance_expiry,
                        'reg': vehicle.registration_date,
                        'vehicle': vehicle.vehicle_number,
                })
            if vehicle.registration_date and vehicle.fitness_expiry \
                    and vehicle.fitness_expiry <= vehicle.registration_date:
                raise ValidationError(_(
                    "Fitness Expiry (%(expiry)s) must be after the Registration Date (%(reg)s) "
                    "for vehicle %(vehicle)s.") % {
                        'expiry': vehicle.fitness_expiry,
                        'reg': vehicle.registration_date,
                        'vehicle': vehicle.vehicle_number,
                })

    @api.constrains('manufacturing_year')
    def _check_manufacturing_year(self):
        current_year = date.today().year
        for vehicle in self:
            if vehicle.manufacturing_year and not (1980 <= vehicle.manufacturing_year <= current_year + 1):
                raise ValidationError(_(
                    "Manufacturing Year (%(year)s) looks invalid for vehicle %(vehicle)s. "
                    "It must be between 1980 and %(max_year)s.") % {
                        'year': vehicle.manufacturing_year,
                        'vehicle': vehicle.vehicle_number,
                        'max_year': current_year + 1,
                })

    @api.constrains('capacity')
    def _check_capacity(self):
        for vehicle in self:
            if vehicle.capacity and vehicle.capacity <= 0:
                raise ValidationError(_(
                    "Capacity must be a positive number for vehicle %s.") % vehicle.vehicle_number)

    # ==================================================================
    # CRUD overrides
    # ==================================================================
    def unlink(self):
        for vehicle in self:
            if vehicle.active:
                raise UserError(_(
                    "Vehicle %s is active and cannot be deleted. "
                    "Please archive it first if it is no longer in service.") % vehicle.vehicle_number)
            if vehicle.status == 'on_trip':
                raise UserError(_(
                    "Vehicle %s is currently on a trip and cannot be deleted.") % vehicle.vehicle_number)
        return super().unlink()

    # ==================================================================
    # Actions
    # ==================================================================
    def action_view_trips(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Trips'),
            'res_model': 'transit.trip',
            'view_mode': 'list,form',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id},
        }

    def action_archive_vehicle(self):
        """Convenience action wired to a form button: safely take a vehicle
        out of service instead of deleting it."""
        self.write({'active': False, 'assigned_trip_id': False})
