# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class TransitMaintenance(models.Model):
    _name = 'transit.maintenance'
    _description = 'Transit Vehicle Maintenance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_scheduled desc, id desc'
    _rec_name = 'name'

    name = fields.Char(string='Reference', required=True, copy=False,
                        readonly=True, default=lambda self: _('New'))
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company, required=True,
    )
    active = fields.Boolean(default=True)

    vehicle_id = fields.Many2one('transit.vehicle', string='Vehicle', required=True, tracking=True)
    maintenance_type = fields.Selection([
        ('scheduled', 'Scheduled Service'),
        ('breakdown', 'Breakdown Repair'),
        ('inspection', 'Inspection'),
        ('other', 'Other'),
    ], string='Type', required=True, default='scheduled', tracking=True)

    description = fields.Text(string='Description')
    vendor = fields.Char(string='Service Vendor / Garage')

    date_scheduled = fields.Date(string='Scheduled Date', required=True, tracking=True)
    date_completed = fields.Date(string='Completion Date', copy=False)
    odometer_at_service = fields.Float(string='Odometer at Service (km)')

    cost = fields.Monetary(string='Cost')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True, copy=False)

    notes = fields.Html(string='Internal Notes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('transit.maintenance') or _('New')
        return super().create(vals_list)

    @api.constrains('cost')
    def _check_cost(self):
        for record in self:
            if record.cost < 0:
                raise ValidationError(_('Cost cannot be negative.'))

    @api.constrains('odometer_at_service')
    def _check_odometer(self):
        for record in self:
            if record.odometer_at_service < 0:
                raise ValidationError(_('Odometer reading cannot be negative.'))

    def action_schedule(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(_('Only draft records can be scheduled.'))
            record.state = 'scheduled'

    def action_start(self):
        for record in self:
            if record.state != 'scheduled':
                raise UserError(_('Only scheduled records can be started.'))
            record.state = 'in_progress'
            record.vehicle_id.write({'state': 'maintenance'})

    def action_complete(self):
        for record in self:
            if record.state != 'in_progress':
                raise UserError(_('Only records in progress can be completed.'))
            record.write({
                'state': 'done',
                'date_completed': fields.Date.context_today(record),
            })
            if record.odometer_at_service and record.odometer_at_service > record.vehicle_id.odometer:
                record.vehicle_id.write({'odometer': record.odometer_at_service})
            record.vehicle_id.write({'state': 'active'})

    def action_cancel(self):
        for record in self:
            if record.state == 'done':
                raise UserError(_('A completed maintenance record cannot be cancelled.'))
            if record.state == 'in_progress':
                record.vehicle_id.write({'state': 'active'})
            record.state = 'cancelled'
