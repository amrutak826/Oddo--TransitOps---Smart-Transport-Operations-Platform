# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class TransitMaintenance(models.Model):
    _name = 'transit.maintenance'
    _description = 'Vehicle Maintenance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'scheduled_date desc'
    _rec_name = 'name'

    name = fields.Char(string='Reference', copy=False, readonly=True,
                        default=lambda self: _('New'))

    vehicle_id = fields.Many2one('transit.vehicle', string='Vehicle', required=True, tracking=True)

    maintenance_type = fields.Selection([
        ('preventive', 'Preventive'),
        ('corrective', 'Corrective'),
        ('inspection', 'Inspection'),
    ], string='Type', default='preventive', tracking=True)

    description = fields.Char(string='Description', required=True)
    scheduled_date = fields.Date(string='Scheduled Date', required=True, tracking=True,
                                  default=fields.Date.context_today)
    completed_date = fields.Date(string='Completed Date')

    odometer_reading = fields.Float(string='Odometer at Service (km)')
    vendor = fields.Char(string='Service Vendor')
    cost = fields.Monetary(string='Cost')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    state = fields.Selection([
        ('due', 'Due'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='due', tracking=True, index=True)

    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    notes = fields.Text(string='Notes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('transit.maintenance') or _('New')
        return super().create(vals_list)

    def action_start(self):
        for rec in self:
            rec.state = 'in_progress'
            rec.vehicle_id.state = 'maintenance'

    def action_complete(self):
        for rec in self:
            rec.write({'state': 'completed', 'completed_date': fields.Date.context_today(rec)})
            rec.vehicle_id.state = 'available'
            if rec.odometer_reading and rec.odometer_reading > rec.vehicle_id.odometer:
                rec.vehicle_id.odometer = rec.odometer_reading

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'
            if rec.vehicle_id.state == 'maintenance':
                rec.vehicle_id.state = 'available'
