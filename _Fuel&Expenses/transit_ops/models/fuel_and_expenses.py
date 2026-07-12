# -*- coding: utf-8 -*-
from datetime import date

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import float_compare, float_is_zero


class TransitExpense(models.Model):
    _name = 'transit.expense'
    _description = 'Fuel & Vehicle Expense'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'
    _rec_name = 'display_name'

    # ------------------------------------------------------------------
    # Core Fields
    # ------------------------------------------------------------------
    vehicle_id = fields.Many2one(
        'transit.vehicle', string='Vehicle', required=True, tracking=True,
        ondelete='restrict', index=True,
    )
    trip_id = fields.Many2one(
        'transit.trip', string='Trip', tracking=True,
        ondelete='set null', index=True,
        help='Optional: link this expense to a specific trip.',
    )
    driver_id = fields.Many2one(
        'transit.driver', string='Driver', tracking=True,
        help='Driver who incurred / logged the expense.',
    )

    expense_type = fields.Selection([
        ('fuel', 'Fuel'),
        ('toll', 'Toll'),
        ('parking', 'Parking'),
        ('permit', 'Permit / Fees'),
        ('repair', 'Minor Repair'),
        ('other', 'Other'),
    ], string='Expense Type', required=True, default='fuel', tracking=True)

    date = fields.Date(
        string='Date', required=True, tracking=True,
        default=fields.Date.context_today,
    )

    # ------------------------------------------------------------------
    # Fuel-Specific Fields
    # ------------------------------------------------------------------
    fuel_quantity = fields.Float(
        string='Fuel Quantity (L)', digits=(10, 2),
        help='Quantity of fuel filled, in liters. Required for Fuel expense type.',
    )
    fuel_cost = fields.Monetary(
        string='Fuel Cost', currency_field='currency_id',
        help='Cost of fuel portion of this expense (auto-included in Expense Amount for Fuel type).',
    )
    odometer_reading = fields.Float(
        string='Odometer at Fill-up (km)', digits=(10, 1),
        help='Optional odometer reading at the time of this expense, for mileage tracking.',
    )

    # ------------------------------------------------------------------
    # Amount
    # ------------------------------------------------------------------
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
    )
    expense_amount = fields.Monetary(
        string='Expense Amount', currency_field='currency_id', required=True, tracking=True,
        help='Total amount of this expense.',
    )

    # ------------------------------------------------------------------
    # Receipt & Remarks
    # ------------------------------------------------------------------
    receipt = fields.Binary(string='Receipt', attachment=True)
    receipt_filename = fields.Char(string='Receipt Filename')
    remarks = fields.Text(string='Remarks')

    # ------------------------------------------------------------------
    # Monthly Aggregation Helpers
    # ------------------------------------------------------------------
    month = fields.Char(string='Month', compute='_compute_month', store=True, index=True)
    year = fields.Char(string='Year', compute='_compute_month', store=True, index=True)

    display_name = fields.Char(string='Reference', compute='_compute_display_name', store=True)

    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company
    )

    # ------------------------------------------------------------------
    # Compute Methods
    # ------------------------------------------------------------------
    @api.depends('date')
    def _compute_month(self):
        for rec in self:
            if rec.date:
                rec.month = rec.date.strftime('%B %Y')
                rec.year = rec.date.strftime('%Y')
            else:
                rec.month = False
                rec.year = False

    @api.depends('vehicle_id', 'expense_type', 'date')
    def _compute_display_name(self):
        type_labels = dict(self._fields['expense_type'].selection)
        for rec in self:
            vehicle_name = rec.vehicle_id.name or _('New')
            type_label = type_labels.get(rec.expense_type, '')
            date_label = rec.date and fields.Date.to_string(rec.date) or ''
            rec.display_name = f"{vehicle_name} - {type_label} ({date_label})".strip()

    # ------------------------------------------------------------------
    # Onchange
    # ------------------------------------------------------------------
    @api.onchange('expense_type')
    def _onchange_expense_type(self):
        if self.expense_type != 'fuel':
            self.fuel_quantity = 0.0
            self.fuel_cost = 0.0

    @api.onchange('trip_id')
    def _onchange_trip_id(self):
        if self.trip_id:
            if self.trip_id.vehicle_id:
                self.vehicle_id = self.trip_id.vehicle_id
            if self.trip_id.driver_id:
                self.driver_id = self.trip_id.driver_id

    # ------------------------------------------------------------------
    # Constraints (Business Rules)
    # ------------------------------------------------------------------
    @api.constrains('expense_amount')
    def _check_expense_amount(self):
        """Rule: Negative values not allowed."""
        for rec in self:
            if float_compare(rec.expense_amount, 0.0, precision_digits=2) < 0:
                raise ValidationError(_('Expense Amount cannot be negative.'))
            if float_is_zero(rec.expense_amount, precision_digits=2):
                raise ValidationError(_('Expense Amount must be greater than zero.'))

    @api.constrains('fuel_quantity', 'fuel_cost')
    def _check_fuel_negative(self):
        """Rule: Negative values not allowed (fuel fields)."""
        for rec in self:
            if float_compare(rec.fuel_quantity, 0.0, precision_digits=2) < 0:
                raise ValidationError(_('Fuel Quantity cannot be negative.'))
            if float_compare(rec.fuel_cost, 0.0, precision_digits=2) < 0:
                raise ValidationError(_('Fuel Cost cannot be negative.'))

    @api.constrains('expense_type', 'fuel_quantity', 'fuel_cost')
    def _check_fuel_quantity_required(self):
        """Rule: Fuel quantity validation - required and sane for Fuel type."""
        for rec in self:
            if rec.expense_type == 'fuel':
                if float_is_zero(rec.fuel_quantity, precision_digits=2):
                    raise ValidationError(
                        _('Fuel Quantity is required and must be greater than zero for Fuel expenses.')
                    )
                if rec.fuel_quantity > 2000:
                    raise ValidationError(
                        _('Fuel Quantity of %.2f L looks unrealistic for a single fill-up. '
                          'Please verify the entry.') % rec.fuel_quantity
                    )
                if float_is_zero(rec.fuel_cost, precision_digits=2):
                    raise ValidationError(
                        _('Fuel Cost is required and must be greater than zero for Fuel expenses.')
                    )
                if float_compare(rec.fuel_cost, rec.expense_amount, precision_digits=2) > 0:
                    raise ValidationError(
                        _('Fuel Cost cannot exceed the total Expense Amount.')
                    )

    @api.constrains('odometer_reading')
    def _check_odometer_reading(self):
        for rec in self:
            if rec.odometer_reading and rec.odometer_reading < 0:
                raise ValidationError(_('Odometer reading cannot be negative.'))

    @api.constrains('date')
    def _check_date_not_future(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.date and rec.date > today:
                raise ValidationError(_('Expense date cannot be in the future.'))

    @api.constrains('trip_id', 'vehicle_id')
    def _check_trip_vehicle_match(self):
        for rec in self:
            if rec.trip_id and rec.trip_id.vehicle_id and rec.vehicle_id:
                if rec.trip_id.vehicle_id != rec.vehicle_id:
                    raise ValidationError(
                        _('The selected Trip belongs to vehicle "%(trip_vehicle)s", '
                          'which does not match the selected Vehicle "%(vehicle)s".') % {
                            'trip_vehicle': rec.trip_id.vehicle_id.name,
                            'vehicle': rec.vehicle_id.name,
                        }
                    )

    # ------------------------------------------------------------------
    # Odometer Sync (best-effort convenience, non-blocking)
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_vehicle_odometer()
        return records

    def write(self, vals):
        result = super().write(vals)
        if 'odometer_reading' in vals:
            self._sync_vehicle_odometer()
        return result

    def _sync_vehicle_odometer(self):
        for rec in self:
            if rec.odometer_reading and rec.vehicle_id:
                if rec.odometer_reading > rec.vehicle_id.odometer:
                    rec.vehicle_id.odometer = rec.odometer_reading

    # ------------------------------------------------------------------
    # Monthly Totals
    # ------------------------------------------------------------------
    @api.model
    def get_monthly_totals(self, vehicle_id=False, year=None):
        """Return monthly aggregated totals (expense amount, fuel cost,
        fuel quantity) optionally filtered by vehicle and year.
        Used by the Dashboard and available for reports.
        """
        domain = []
        if vehicle_id:
            domain.append(('vehicle_id', '=', vehicle_id))
        if year:
            domain.append(('year', '=', str(year)))

        records = self.search(domain)
        totals = {}
        for rec in records:
            key = rec.month or _('Unknown')
            if key not in totals:
                totals[key] = {
                    'month': key,
                    'total_expense': 0.0,
                    'total_fuel_cost': 0.0,
                    'total_fuel_quantity': 0.0,
                    'count': 0,
                }
            totals[key]['total_expense'] += rec.expense_amount
            totals[key]['total_fuel_cost'] += rec.fuel_cost
            totals[key]['total_fuel_quantity'] += rec.fuel_quantity
            totals[key]['count'] += 1

        return sorted(totals.values(), key=lambda r: r['month'])

    def action_view_monthly_summary(self):
        """Open a pivot view grouped by month for quick monthly total review."""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Monthly Expense Summary'),
            'res_model': 'transit.expense',
            'view_mode': 'pivot,graph,list',
            'domain': [('vehicle_id', '=', self.vehicle_id.id)] if self else [],
            'context': {
                'search_default_group_month': 1,
                'pivot_measures': ['expense_amount', 'fuel_cost', 'fuel_quantity'],
            },
        }
