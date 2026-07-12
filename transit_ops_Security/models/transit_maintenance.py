# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class TransitMaintenance(models.Model):
    _name = 'transit.maintenance'
    _description = 'Transit Vehicle Maintenance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'scheduled_date desc, id desc'

    name = fields.Char(
        string='Maintenance Reference', copy=False, readonly=True,
        default=lambda self: _('New'))

    vehicle_id = fields.Many2one(
        'transit.vehicle', string='Vehicle', required=True, tracking=True)

    maintenance_type = fields.Selection([
        ('preventive', 'Preventive'),
        ('corrective', 'Corrective'),
        ('inspection', 'Safety Inspection'),
    ], string='Type', default='preventive', required=True, tracking=True)

    description = fields.Text(string='Description', required=True)

    scheduled_date = fields.Date(string='Scheduled Date', required=True, tracking=True)
    completion_date = fields.Date(string='Completion Date', readonly=True)

    odometer_reading = fields.Float(string='Odometer Reading (km)')
    vendor = fields.Char(string='Service Vendor')
    cost = fields.Float(string='Cost')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)

    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company)

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('cost')
    def _check_cost(self):
        for record in self:
            if record.cost < 0:
                raise ValidationError(_('Cost cannot be negative.'))

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('transit.maintenance') or _('New')
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Actions / State Machine
    # ------------------------------------------------------------------
    def action_schedule(self):
        for record in self:
            if record.state != 'draft':
                raise ValidationError(_('Only draft records can be scheduled.'))
        self.write({'state': 'scheduled'})

    def action_start(self):
        for record in self:
            if record.state != 'scheduled':
                raise ValidationError(_('Only scheduled maintenance can be started.'))
            record.vehicle_id.write({'status': 'maintenance'})
        self.write({'state': 'in_progress'})

    def action_complete(self):
        for record in self:
            if record.state != 'in_progress':
                raise ValidationError(_('Only in-progress maintenance can be completed.'))
            record.vehicle_id.write({'status': 'active'})
        self.write({
            'state': 'completed',
            'completion_date': fields.Date.context_today(self),
        })

    def action_cancel(self):
        for record in self:
            if record.state == 'in_progress':
                record.vehicle_id.write({'status': 'active'})
        self.write({'state': 'cancelled'})
