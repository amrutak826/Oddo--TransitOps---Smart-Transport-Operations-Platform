# -*- coding: utf-8 -*-
from odoo import api, fields, models


class TransitMaintenance(models.Model):
    _name = 'transit.maintenance'
    _description = 'Transit Vehicle Maintenance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'next_service_date asc'
    _rec_name = 'name'

    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True,
        default=lambda self: 'New'
    )
    vehicle_id = fields.Many2one('transit.vehicle', string='Vehicle', required=True, tracking=True)

    maintenance_type = fields.Selection([
        ('routine', 'Routine Service'),
        ('repair', 'Repair'),
        ('inspection', 'Inspection'),
        ('tire', 'Tire Change'),
        ('other', 'Other'),
    ], string='Type', default='routine', required=True, tracking=True)

    scheduled_date = fields.Date(string='Scheduled Date', tracking=True)
    next_service_date = fields.Date(string='Next Service Due', tracking=True)
    completed_date = fields.Date(string='Completed Date')

    cost = fields.Float(string='Cost', digits='Product Price')
    description = fields.Text(string='Description')

    state = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='scheduled', tracking=True, required=True)

    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company, required=True
    )
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('transit.maintenance') or 'New'
        return super().create(vals_list)

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_complete(self):
        self.write({'state': 'done', 'completed_date': fields.Date.context_today(self)})
