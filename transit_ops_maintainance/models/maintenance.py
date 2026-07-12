# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class TransitMaintenance(models.Model):
    _name = 'transit.maintenance'
    _description = 'Vehicle Maintenance Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'scheduled_date desc, id desc'
    _rec_name = 'display_name'

    # ------------------------------------------------------------------
    # Core Fields
    # ------------------------------------------------------------------
    vehicle_id = fields.Many2one(
        'transit.vehicle', string='Vehicle', required=True, tracking=True,
        ondelete='restrict', index=True,
    )
    maintenance_type = fields.Selection([
        ('preventive', 'Preventive'),
        ('corrective', 'Corrective / Repair'),
        ('inspection', 'Inspection'),
        ('tire_service', 'Tire Service'),
        ('oil_change', 'Oil Change'),
        ('other', 'Other'),
    ], string='Maintenance Type', required=True, default='preventive', tracking=True)

    description = fields.Text(string='Description')

    scheduled_date = fields.Date(
        string='Scheduled Date', required=True, tracking=True,
        default=fields.Date.context_today,
    )
    completed_date = fields.Date(string='Completed Date', tracking=True)

    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
    )
    estimated_cost = fields.Monetary(string='Estimated Cost', currency_field='currency_id')
    actual_cost = fields.Monetary(string='Actual Cost', currency_field='currency_id')

    mechanic_id = fields.Many2one(
        'res.partner', string='Mechanic / Workshop', tracking=True,
        help='External mechanic, garage, or workshop performing the service.'
    )

    status = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True, copy=False)

    # ------------------------------------------------------------------
    # Overdue Detection / Reminder Support
    # ------------------------------------------------------------------
    is_overdue = fields.Boolean(
        string='Overdue', compute='_compute_is_overdue',
        search='_search_is_overdue', store=False,
    )
    days_until_due = fields.Integer(
        string='Days Until Due', compute='_compute_days_until_due', store=False,
    )
    reminder_sent = fields.Boolean(string='Upcoming Reminder Sent', default=False, copy=False)
    overdue_notified = fields.Boolean(string='Overdue Notice Sent', default=False, copy=False)

    display_name = fields.Char(string='Reference', compute='_compute_display_name', store=True)

    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company
    )

    # ------------------------------------------------------------------
    # Compute Methods
    # ------------------------------------------------------------------
    @api.depends('vehicle_id', 'maintenance_type', 'scheduled_date')
    def _compute_display_name(self):
        type_labels = dict(self._fields['maintenance_type'].selection)
        for rec in self:
            vehicle_name = rec.vehicle_id.name or _('New')
            type_label = type_labels.get(rec.maintenance_type, '')
            date_label = rec.scheduled_date and fields.Date.to_string(rec.scheduled_date) or ''
            rec.display_name = f"{vehicle_name} - {type_label} ({date_label})".strip()

    @api.depends('scheduled_date', 'status')
    def _compute_is_overdue(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.is_overdue = bool(
                rec.scheduled_date
                and rec.scheduled_date < today
                and rec.status in ('draft', 'scheduled', 'in_progress')
            )

    def _search_is_overdue(self, operator, value):
        today = fields.Date.context_today(self)
        open_states = ('draft', 'scheduled', 'in_progress')
        want_overdue = (operator == '=' and value) or (operator == '!=' and not value)
        if want_overdue:
            return [('scheduled_date', '<', today), ('status', 'in', open_states)]
        return ['|', ('scheduled_date', '>=', today), ('status', 'not in', open_states)]

    @api.depends('scheduled_date', 'status')
    def _compute_days_until_due(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.scheduled_date and rec.status in ('draft', 'scheduled', 'in_progress'):
                rec.days_until_due = (rec.scheduled_date - today).days
            else:
                rec.days_until_due = 0

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('scheduled_date', 'completed_date')
    def _check_dates(self):
        for rec in self:
            if rec.completed_date and rec.scheduled_date and rec.completed_date < rec.scheduled_date:
                raise ValidationError(
                    _('Completed date cannot be earlier than the scheduled date.')
                )

    @api.constrains('estimated_cost', 'actual_cost')
    def _check_costs(self):
        for rec in self:
            if rec.estimated_cost < 0 or rec.actual_cost < 0:
                raise ValidationError(_('Cost fields cannot be negative.'))

    # ------------------------------------------------------------------
    # Vehicle Availability Sync (Business Rule: vehicle unavailable during maintenance)
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            rec._sync_vehicle_status()
        return records

    def write(self, vals):
        result = super().write(vals)
        if 'status' in vals:
            self._sync_vehicle_status()
        return result

    def _sync_vehicle_status(self):
        """Lock the vehicle while maintenance is in progress; release it
        once maintenance is completed or cancelled (unless another
        maintenance job is still actively in progress on the same vehicle).
        """
        for rec in self:
            vehicle = rec.vehicle_id
            if not vehicle:
                continue
            if rec.status == 'in_progress':
                if vehicle.status != 'maintenance':
                    vehicle.status = 'maintenance'
            elif rec.status in ('completed', 'cancelled'):
                other_active = self.search_count([
                    ('vehicle_id', '=', vehicle.id),
                    ('status', '=', 'in_progress'),
                    ('id', '!=', rec.id),
                ])
                if not other_active and vehicle.status == 'maintenance':
                    vehicle.status = 'available'

    # ------------------------------------------------------------------
    # Actions (Status Transitions)
    # ------------------------------------------------------------------
    def action_schedule(self):
        for rec in self:
            if rec.status != 'draft':
                raise ValidationError(_('Only draft records can be scheduled.'))
            rec.status = 'scheduled'

    def action_start(self):
        for rec in self:
            if rec.status not in ('draft', 'scheduled'):
                raise ValidationError(_('Maintenance can only be started from Draft or Scheduled.'))
            rec.status = 'in_progress'

    def action_complete(self):
        for rec in self:
            if rec.status != 'in_progress':
                raise ValidationError(_('Only maintenance In Progress can be marked Completed.'))
            if not rec.completed_date:
                rec.completed_date = fields.Date.context_today(rec)
            rec.status = 'completed'

    def action_cancel(self):
        for rec in self:
            if rec.status == 'completed':
                raise ValidationError(_('A completed maintenance record cannot be cancelled.'))
            rec.status = 'cancelled'

    def action_reset_to_draft(self):
        for rec in self:
            rec.status = 'draft'
            rec.reminder_sent = False
            rec.overdue_notified = False

    # ------------------------------------------------------------------
    # Reminder / Overdue Notification Logic
    # ------------------------------------------------------------------
    def _get_notification_users(self):
        """Fleet Managers + Administrators receive maintenance notifications."""
        manager_group = self.env.ref('transit_ops.group_transit_manager', raise_if_not_found=False)
        return manager_group.users if manager_group else self.env['res.users']

    def _send_reminder_notification(self):
        self.ensure_one()
        users = self._get_notification_users()
        body = _(
            'Reminder: Maintenance for vehicle <b>%(vehicle)s</b> (%(type)s) '
            'is scheduled on <b>%(date)s</b>.'
        ) % {
            'vehicle': self.vehicle_id.name,
            'type': dict(self._fields['maintenance_type'].selection).get(self.maintenance_type),
            'date': self.scheduled_date,
        }
        self.message_post(body=body, message_type='notification', subtype_xmlid='mail.mt_note')
        for user in users:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=_('Upcoming Maintenance Reminder'),
                note=body,
                user_id=user.id,
                date_deadline=self.scheduled_date,
            )

    def _send_overdue_notification(self):
        self.ensure_one()
        users = self._get_notification_users()
        body = _(
            'Overdue: Maintenance for vehicle <b>%(vehicle)s</b> (%(type)s) was '
            'scheduled on <b>%(date)s</b> and has not been completed.'
        ) % {
            'vehicle': self.vehicle_id.name,
            'type': dict(self._fields['maintenance_type'].selection).get(self.maintenance_type),
            'date': self.scheduled_date,
        }
        self.message_post(body=body, message_type='notification', subtype_xmlid='mail.mt_note')
        for user in users:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=_('Overdue Maintenance'),
                note=body,
                user_id=user.id,
                date_deadline=fields.Date.context_today(self),
            )

    # ------------------------------------------------------------------
    # Cron Entry Point
    # ------------------------------------------------------------------
    @api.model
    def _cron_maintenance_daily_check(self):
        """Scheduled daily: (1) sends upcoming reminders 3 days before the
        scheduled date, (2) detects and notifies overdue maintenance.
        """
        today = fields.Date.context_today(self)
        reminder_window = today + timedelta(days=3)

        upcoming = self.search([
            ('status', 'in', ('draft', 'scheduled')),
            ('scheduled_date', '>=', today),
            ('scheduled_date', '<=', reminder_window),
            ('reminder_sent', '=', False),
        ])
        for rec in upcoming:
            rec._send_reminder_notification()
            rec.reminder_sent = True

        overdue = self.search([
            ('status', 'in', ('draft', 'scheduled', 'in_progress')),
            ('scheduled_date', '<', today),
            ('overdue_notified', '=', False),
        ])
        for rec in overdue:
            rec._send_overdue_notification()
            rec.overdue_notified = True

        return True
