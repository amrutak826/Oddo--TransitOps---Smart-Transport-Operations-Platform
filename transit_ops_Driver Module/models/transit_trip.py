# -*- coding: utf-8 -*-

from odoo import api, fields, models


class TransitTrip(models.Model):
    """Minimal trip record.

    Lean for now — it exists so the Vehicle Registry's "Assigned Trip"
    field and "Trips" smart button have a real, working comodel. The Trip
    Dispatch step will extend this same model (scheduling, route, live
    status workflow, its own views/menu) without breaking anything
    defined here.
    """
    _name = 'transit.trip'
    _description = 'Transit Trip'
    _order = 'create_date desc'

    name = fields.Char(string='Trip Reference', copy=False, readonly=True,
                        default=lambda self: self.env['ir.sequence'].next_by_code('transit.trip') or 'New')
    vehicle_id = fields.Many2one('transit.vehicle', string='Vehicle', ondelete='restrict')
    driver_id = fields.Many2one('transit.driver', string='Driver', ondelete='restrict')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)

    def name_get(self):
        result = []
        for trip in self:
            result.append((trip.id, trip.name or 'New'))
        return result
