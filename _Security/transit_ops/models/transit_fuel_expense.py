# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class TransitFuelExpense(models.Model):
    _name = 'transit.fuel.expense'
    _description = 'Transit Fuel & Expense Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(
        string='Expense Reference', copy=False, readonly=True,
        default=lambda self: _('New'))

    vehicle_id = fields.Many2one('transit.vehicle', string='Vehicle', required=True, tracking=True)
    driver_id = fields.Many2one('transit.driver', string='Driver', tracking=True)

    date = fields.Date(string='Date', required=True, default=fields.Date.context_today, tracking=True)

    expense_type = fields.Selection([
        ('fuel', 'Fuel'),
        ('toll', 'Toll'),
        ('parking', 'Parking'),
        ('repair', 'Repair'),
        ('fine', 'Fine'),
        ('other', 'Other'),
    ], string='Expense Type', default='fuel', required=True, tracking=True)

    quantity_liters = fields.Float(string='Quantity (Liters)')
    unit_price = fields.Float(string='Unit Price')
    amount = fields.Float(string='Amount', required=True, tracking=True)
    odometer_reading = fields.Float(string='Odometer Reading (km)')

    receipt = fields.Binary(string='Receipt Attachment')
    receipt_filename = fields.Char(string='Receipt Filename')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', required=True, tracking=True)

    approved_by_id = fields.Many2one('res.users', string='Approved/Rejected By', readonly=True)
    rejection_reason = fields.Text(string='Rejection Reason')

    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        'res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    # ------------------------------------------------------------------
    # Onchange
    # ------------------------------------------------------------------
    @api.onchange('quantity_liters', 'unit_price', 'expense_type')
    def _onchange_fuel_amount(self):
        if self.expense_type == 'fuel' and self.quantity_liters and self.unit_price:
            self.amount = self.quantity_liters * self.unit_price

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('amount')
    def _check_amount(self):
        for record in self:
            if record.amount < 0:
                raise ValidationError(_('Amount cannot be negative.'))

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('transit.fuel.expense') or _('New')
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Actions / Approval Workflow
    # ------------------------------------------------------------------
    def action_submit(self):
        for record in self:
            if record.state != 'draft':
                raise ValidationError(_('Only draft records can be submitted.'))
        self.write({'state': 'submitted'})

    def action_approve(self):
        for record in self:
            if record.state != 'submitted':
                raise ValidationError(_('Only submitted records can be approved.'))
        self.write({
            'state': 'approved',
            'approved_by_id': self.env.user.id,
            'rejection_reason': False,
        })

    def action_reject(self):
        for record in self:
            if record.state != 'submitted':
                raise ValidationError(_('Only submitted records can be rejected.'))
        self.write({
            'state': 'rejected',
            'approved_by_id': self.env.user.id,
        })

    def action_reset_to_draft(self):
        self.write({'state': 'draft', 'approved_by_id': False, 'rejection_reason': False})
