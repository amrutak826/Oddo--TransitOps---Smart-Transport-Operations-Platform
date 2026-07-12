# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class TransitExpense(models.Model):
    _name = 'transit.expense'
    _description = 'Transport Expense'
    _order = 'date desc'
    _rec_name = 'name'

    name = fields.Char(string='Reference', copy=False, readonly=True,
                        default=lambda self: _('New'))

    vehicle_id = fields.Many2one('transit.vehicle', string='Vehicle')
    driver_id = fields.Many2one('transit.driver', string='Driver', required=True)
    trip_id = fields.Many2one('transit.trip', string='Related Trip')

    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    category = fields.Selection([
        ('toll', 'Toll'),
        ('parking', 'Parking'),
        ('repair', 'Minor Repair'),
        ('permit', 'Permit / Fine'),
        ('food', 'Food / Allowance'),
        ('other', 'Other'),
    ], string='Category', default='other', required=True)

    amount = fields.Monetary(string='Amount', required=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True)

    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    description = fields.Char(string='Description')
    receipt = fields.Binary(string='Receipt Attachment')
    receipt_filename = fields.Char(string='Receipt Filename')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('transit.expense') or _('New')
        return super().create(vals_list)

    def action_submit(self):
        self.write({'state': 'submitted'})

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_reject(self):
        self.write({'state': 'rejected'})
