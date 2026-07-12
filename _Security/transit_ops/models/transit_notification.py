# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class TransitNotification(models.Model):
    _name = 'transit.notification'
    _description = 'Transit Notification'
    _order = 'date desc, id desc'

    title = fields.Char(string='Title', required=True)
    message = fields.Text(string='Message', required=True)

    notification_type = fields.Selection([
        ('document_expiry', 'Vehicle Document Expiry'),
        ('license_expiry', 'Driver License Expiry'),
        ('maintenance_due', 'Maintenance Due'),
        ('trip_alert', 'Trip Alert'),
        ('expense_alert', 'Expense Alert'),
        ('general', 'General'),
    ], string='Type', default='general', required=True)

    severity = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ], string='Severity', default='medium', required=True)

    state = fields.Selection([
        ('unread', 'Unread'),
        ('read', 'Read'),
    ], string='Status', default='unread', required=True)

    date = fields.Datetime(string='Date', default=fields.Datetime.now, required=True)

    vehicle_id = fields.Many2one('transit.vehicle', string='Related Vehicle')
    driver_id = fields.Many2one('transit.driver', string='Related Driver')
    trip_id = fields.Many2one('transit.trip', string='Related Trip')
    expense_id = fields.Many2one('transit.fuel.expense', string='Related Expense')

    user_id = fields.Many2one(
        'res.users', string='Recipient',
        help='Leave empty to broadcast to all users with access to this notification type.')

    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_mark_read(self):
        self.write({'state': 'read'})

    def action_mark_unread(self):
        self.write({'state': 'unread'})
