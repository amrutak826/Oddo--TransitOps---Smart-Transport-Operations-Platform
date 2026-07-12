# -*- coding: utf-8 -*-

from odoo import api, fields, models


class TransitDriver(models.Model):
    """Minimal driver identity record.

    This model is intentionally lean for now — it exists so the Vehicle
    Registry's "Assigned Driver" field has a real, working comodel to point
    at. The Driver Management step will extend this same model (license
    validity, assignment history, performance KPIs, its own views/menu)
    without breaking anything defined here.
    """
    _name = 'transit.driver'
    _description = 'Transit Driver'
    _order = 'name'

    name = fields.Char(string='Driver Name', required=True, tracking=True)
    code = fields.Char(string='Driver Code', copy=False, readonly=True,
                        default=lambda self: self.env['ir.sequence'].next_by_code('transit.driver') or 'New')
    phone = fields.Char(string='Phone')
    license_number = fields.Char(string='License Number')
    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)

    _sql_constraints = [
        ('driver_license_unique', 'unique(license_number)',
         'License Number must be unique! A driver with this license already exists.'),
    ]

    def name_get(self):
        result = []
        for driver in self:
            label = f"{driver.name} [{driver.code}]" if driver.code and driver.code != 'New' else driver.name
            result.append((driver.id, label))
        return result
