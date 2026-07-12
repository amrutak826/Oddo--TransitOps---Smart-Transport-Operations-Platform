# -*- coding: utf-8 -*-

import re

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class TransitDriver(models.Model):
    _name = 'transit.driver'
    _description = 'Transit Driver'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    # ------------------------------------------------------------------
    # Selections
    # ------------------------------------------------------------------
    STATUS_SELECTION = [
        ('available', 'Available'),
        ('assigned', 'Assigned'),
        ('license_expired', 'License Expired'),
        ('inactive', 'Inactive'),
    ]

    # ------------------------------------------------------------------
    # Identification
    # ------------------------------------------------------------------
    name = fields.Char(string='Name', required=True, tracking=True)
    code = fields.Char(
        string='Driver Code', copy=False, readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('transit.driver') or 'New')
    image_1920 = fields.Image(string='Photo', max_width=1920, max_height=1920)
    image_128 = fields.Image(string='Photo (Thumbnail)', related='image_1920',
                              max_width=128, max_height=128, store=True)

    # ------------------------------------------------------------------
    # Contact details
    # ------------------------------------------------------------------
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email', tracking=True)
    address = fields.Text(string='Address')

    # ------------------------------------------------------------------
    # License & employment
    # ------------------------------------------------------------------
    license_number = fields.Char(string='License Number', required=True, tracking=True)
    license_expiry = fields.Date(string='License Expiry', required=True, tracking=True)
    joining_date = fields.Date(string='Joining Date', default=fields.Date.context_today)
    experience_years = fields.Integer(string='Experience (Years)')

    # ------------------------------------------------------------------
    # Performance & status
    # ------------------------------------------------------------------
    safety_score = fields.Float(
        string='Safety Score', compute='_compute_safety_score', store=True,
        digits=(5, 1), tracking=True,
        help="Automatically calculated out of 100 from experience, license "
             "validity and current active status. Not manually editable.")
    status = fields.Selection(
        STATUS_SELECTION, string='Status', compute='_compute_status',
        store=True, tracking=True,
        help="Automatically derived from the driver's active flag, license "
             "validity and current vehicle assignment.")

    # ------------------------------------------------------------------
    # Assignment
    # ------------------------------------------------------------------
    vehicle_ids = fields.One2many(
        'transit.vehicle', 'assigned_driver_id', string='Assigned Vehicles (History)')
    assigned_vehicle_id = fields.Many2one(
        'transit.vehicle', string='Assigned Vehicle',
        compute='_compute_assigned_vehicle', inverse='_inverse_assigned_vehicle',
        store=True, tracking=True,
        help="The vehicle currently allocated to this driver. Setting this "
             "here will also update the vehicle's Assigned Driver field.")

    # ------------------------------------------------------------------
    # Misc
    # ------------------------------------------------------------------
    notes = fields.Text(string='Notes')
    active = fields.Boolean(string='Active', default=True, tracking=True)
    user_id = fields.Many2one(
        'res.users', string='Linked User',
        help="Optional portal/internal user account, used to let this "
             "driver see only their own record.")
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company)

    _sql_constraints = [
        ('driver_license_unique', 'unique(license_number)',
         'License Number must be unique! A driver with this license already exists.'),
    ]

    # ==================================================================
    # Compute methods
    # ==================================================================
    @api.depends('vehicle_ids', 'vehicle_ids.active')
    def _compute_assigned_vehicle(self):
        for driver in self:
            driver.assigned_vehicle_id = driver.vehicle_ids[:1]

    def _inverse_assigned_vehicle(self):
        for driver in self:
            previous_vehicles = driver.vehicle_ids - driver.assigned_vehicle_id
            if previous_vehicles:
                previous_vehicles.write({'assigned_driver_id': False})
            if driver.assigned_vehicle_id:
                driver.assigned_vehicle_id.write({'assigned_driver_id': driver.id})

    @api.depends('active', 'license_expiry', 'assigned_vehicle_id')
    def _compute_status(self):
        today = fields.Date.context_today(self)
        for driver in self:
            if not driver.active:
                driver.status = 'inactive'
            elif driver.license_expiry and driver.license_expiry < today:
                driver.status = 'license_expired'
            elif driver.assigned_vehicle_id:
                driver.status = 'assigned'
            else:
                driver.status = 'available'

    @api.depends('experience_years', 'license_expiry', 'active')
    def _compute_safety_score(self):
        """Automatic safety score out of 100.

        Baseline of 70, plus up to +20 for experience (2 points per year,
        capped at 10 years), minus penalties for a soon-to-expire or
        already-expired license, minus a penalty if the driver is inactive.
        """
        today = fields.Date.context_today(self)
        for driver in self:
            score = 70.0
            score += min(driver.experience_years or 0, 10) * 2.0

            if driver.license_expiry:
                days_to_expiry = (driver.license_expiry - today).days
                if days_to_expiry < 0:
                    score -= 30.0
                elif days_to_expiry <= 30:
                    score -= 10.0

            if not driver.active:
                score -= 15.0

            driver.safety_score = max(0.0, min(100.0, score))

    def _compute_display_name(self):
        for driver in self:
            label = driver.name or _('New')
            driver.display_name = f"{label} [{driver.code}]" if driver.code and driver.code != 'New' else label

    # ==================================================================
    # Constraints
    # ==================================================================
    @api.constrains('license_expiry', 'joining_date')
    def _check_license_expiry(self):
        for driver in self:
            if driver.joining_date and driver.license_expiry \
                    and driver.license_expiry <= driver.joining_date:
                raise ValidationError(_(
                    "License Expiry (%(expiry)s) must be after the Joining Date (%(joining)s) "
                    "for driver %(driver)s.") % {
                        'expiry': driver.license_expiry,
                        'joining': driver.joining_date,
                        'driver': driver.name,
                })

    @api.constrains('assigned_vehicle_id', 'license_expiry')
    def _check_no_expired_assignment(self):
        today = fields.Date.context_today(self)
        for driver in self:
            if driver.assigned_vehicle_id and driver.license_expiry and driver.license_expiry < today:
                raise ValidationError(_(
                    "Cannot assign a vehicle to %(driver)s: their driving license "
                    "expired on %(expiry)s. Renew the license before assigning a vehicle.") % {
                        'driver': driver.name,
                        'expiry': driver.license_expiry,
                })

    @api.constrains('email')
    def _check_email_format(self):
        for driver in self:
            if driver.email and not EMAIL_RE.match(driver.email):
                raise ValidationError(_(
                    "'%(email)s' does not look like a valid email address for driver %(driver)s.") % {
                        'email': driver.email,
                        'driver': driver.name,
                })

    @api.constrains('experience_years')
    def _check_experience_years(self):
        for driver in self:
            if driver.experience_years is not None and driver.experience_years < 0:
                raise ValidationError(_("Experience cannot be negative for driver %s.") % driver.name)

    # ==================================================================
    # CRUD overrides
    # ==================================================================
    def unlink(self):
        for driver in self:
            if driver.active:
                raise UserError(_(
                    "Driver %s is active and cannot be deleted. "
                    "Please archive them first if they are no longer employed.") % driver.name)
            if driver.assigned_vehicle_id:
                raise UserError(_(
                    "Driver %s is currently assigned to a vehicle and cannot be deleted. "
                    "Unassign the vehicle first.") % driver.name)
        return super().unlink()

    # ==================================================================
    # Actions
    # ==================================================================
    def action_view_assigned_vehicle(self):
        self.ensure_one()
        if not self.assigned_vehicle_id:
            raise UserError(_("%s has no vehicle currently assigned.") % self.name)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Assigned Vehicle'),
            'res_model': 'transit.vehicle',
            'view_mode': 'form',
            'res_id': self.assigned_vehicle_id.id,
        }

    def action_archive_driver(self):
        """Convenience action wired to a form button: safely take a driver
        out of service instead of deleting them."""
        for driver in self:
            if driver.assigned_vehicle_id:
                driver.assigned_vehicle_id.write({'assigned_driver_id': False})
        self.write({'active': False})
