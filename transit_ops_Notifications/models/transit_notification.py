# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import timedelta


class TransitVehicleBudgetField(models.Model):
    """Extends the Vehicle model (defined in transit_vehicle.py) with the
    monthly fuel budget threshold used by the Fuel Budget Exceeded alert."""
    _inherit = 'transit.vehicle'

    monthly_fuel_budget = fields.Monetary(
        string='Monthly Fuel Budget', currency_field='currency_id', default=0.0,
        help='If total fuel cost for the current calendar month exceeds this '
             'amount, a Fuel Budget Exceeded notification is triggered.'
    )


class TransitNotification(models.Model):
    _name = 'transit.notification'
    _description = 'TransitOps Notification'
    _order = 'date desc, id desc'
    _rec_name = 'name'

    name = fields.Char(string='Title', required=True)
    message = fields.Text(string='Message', required=True)

    notification_type = fields.Selection([
        ('insurance_expiry', 'Insurance Expiry'),
        ('license_expiry', 'License Expiry'),
        ('maintenance_due', 'Maintenance Due'),
        ('trip_delayed', 'Trip Delayed'),
        ('fuel_budget_exceeded', 'Fuel Budget Exceeded'),
        ('general', 'General'),
    ], string='Alert Type', required=True, default='general', index=True)

    severity = fields.Selection([
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('danger', 'Critical'),
    ], string='Severity', default='warning', required=True)

    user_id = fields.Many2one(
        'res.users', string='Recipient', required=True, index=True, ondelete='cascade'
    )

    date = fields.Datetime(string='Date', default=fields.Datetime.now, required=True, index=True)
    is_read = fields.Boolean(string='Read', default=False, index=True)
    read_date = fields.Datetime(string='Read On')

    res_model = fields.Char(string='Related Model')
    res_id = fields.Integer(string='Related Record ID')

    vehicle_id = fields.Many2one('transit.vehicle', string='Vehicle')
    driver_id = fields.Many2one('transit.driver', string='Driver')
    trip_id = fields.Many2one('transit.trip', string='Trip')

    active = fields.Boolean(default=True)

    # ------------------------------------------------------------------
    # CRUD / bus push
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        notifications = super().create(vals_list)
        for notif in notifications:
            partner = notif.user_id.partner_id
            if partner:
                self.env['bus.bus']._sendone(
                    partner,
                    'transit_ops_notification',
                    notif._systray_payload(),
                )
        return notifications

    def _systray_payload(self):
        self.ensure_one()
        return {
            'id': self.id,
            'name': self.name,
            'message': self.message,
            'notification_type': self.notification_type,
            'severity': self.severity,
            'res_model': self.res_model,
            'res_id': self.res_id,
            'is_read': self.is_read,
            'date_display': self.date.strftime('%d %b %Y, %H:%M') if self.date else '',
        }

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_mark_read(self):
        self.write({'is_read': True, 'read_date': fields.Datetime.now()})
        return True

    @api.model
    def action_mark_all_read(self):
        unread = self.search([('user_id', '=', self.env.uid), ('is_read', '=', False)])
        unread.write({'is_read': True, 'read_date': fields.Datetime.now()})
        return True

    def action_open_related(self):
        self.ensure_one()
        if not self.is_read:
            self.action_mark_read()
        if not (self.res_model and self.res_id):
            return False
        return {
            'type': 'ir.actions.act_window',
            'res_model': self.res_model,
            'res_id': self.res_id,
            'views': [(False, 'form')],
            'target': 'current',
        }

    # ------------------------------------------------------------------
    # Systray API (called from the bell icon widget)
    # ------------------------------------------------------------------
    @api.model
    def get_systray_notifications(self, limit=10):
        notifications = self.search([('user_id', '=', self.env.uid)], limit=limit)
        unread_count = self.search_count([
            ('user_id', '=', self.env.uid), ('is_read', '=', False)
        ])
        return {
            'notifications': [n._systray_payload() for n in notifications],
            'unread_count': unread_count,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _get_ops_users(self):
        """Dispatchers and Managers (managers imply the dispatcher group)."""
        dispatcher_group = self.env.ref('transit_ops.group_transit_dispatcher', raise_if_not_found=False)
        if not dispatcher_group:
            return self.env['res.users']
        return self.env['res.users'].search([('groups_id', 'in', dispatcher_group.ids)])

    def _notify_user(self, user, notification_type, title, message, severity='warning',
                      res_model=False, res_id=False, vehicle_id=False, driver_id=False,
                      trip_id=False, dedup_hours=24):
        """Create a notification for `user` unless an equivalent one was already
        raised for the same record within the `dedup_hours` window (prevents
        the same cron run, or successive daily runs, from spamming users)."""
        if not user:
            return self.browse()

        cutoff = fields.Datetime.now() - timedelta(hours=dedup_hours)
        domain = [
            ('user_id', '=', user.id),
            ('notification_type', '=', notification_type),
            ('date', '>=', cutoff),
        ]
        if res_model and res_id:
            domain += [('res_model', '=', res_model), ('res_id', '=', res_id)]

        existing = self.search(domain, limit=1)
        if existing:
            return existing

        return self.create({
            'name': title,
            'message': message,
            'notification_type': notification_type,
            'severity': severity,
            'user_id': user.id,
            'res_model': res_model,
            'res_id': res_id,
            'vehicle_id': vehicle_id,
            'driver_id': driver_id,
            'trip_id': trip_id,
        })

    # ------------------------------------------------------------------
    # Scheduled Action targets — one method per alert type
    # ------------------------------------------------------------------
    def _cron_check_insurance_expiry(self):
        today = fields.Date.context_today(self)
        threshold = today + timedelta(days=30)
        vehicles = self.env['transit.vehicle'].search([
            ('insurance_expiry', '!=', False),
            ('insurance_expiry', '<=', threshold),
            ('active', '=', True),
        ])
        recipients = self._get_ops_users()
        for vehicle in vehicles:
            days_left = (vehicle.insurance_expiry - today).days
            if days_left < 0:
                severity = 'danger'
                title = f"Insurance Expired: {vehicle.name}"
                message = f"Insurance for vehicle {vehicle.name} expired {abs(days_left)} day(s) ago."
            else:
                severity = 'danger' if days_left <= 7 else 'warning'
                title = f"Insurance Expiring Soon: {vehicle.name}"
                message = f"Insurance for vehicle {vehicle.name} expires in {days_left} day(s)."
            for user in recipients:
                self._notify_user(
                    user=user, notification_type='insurance_expiry', title=title,
                    message=message, severity=severity,
                    res_model='transit.vehicle', res_id=vehicle.id,
                    vehicle_id=vehicle.id, dedup_hours=20,
                )

    def _cron_check_license_expiry(self):
        today = fields.Date.context_today(self)
        threshold = today + timedelta(days=30)
        drivers = self.env['transit.driver'].search([
            ('license_expiry_date', '!=', False),
            ('license_expiry_date', '<=', threshold),
            ('active', '=', True),
        ])
        ops_users = self._get_ops_users()
        for driver in drivers:
            days_left = (driver.license_expiry_date - today).days
            if days_left < 0:
                severity = 'danger'
                title = f"License Expired: {driver.name}"
                message = f"Driving license for {driver.name} expired {abs(days_left)} day(s) ago."
            else:
                severity = 'danger' if days_left <= 7 else 'warning'
                title = f"License Expiring Soon: {driver.name}"
                message = f"Driving license for {driver.name} expires in {days_left} day(s)."

            recipients = ops_users
            if driver.user_id:
                recipients |= driver.user_id

            for user in recipients:
                self._notify_user(
                    user=user, notification_type='license_expiry', title=title,
                    message=message, severity=severity,
                    res_model='transit.driver', res_id=driver.id,
                    driver_id=driver.id, dedup_hours=20,
                )

    def _cron_check_maintenance_due(self):
        today = fields.Date.context_today(self)
        threshold = today + timedelta(days=7)
        records = self.env['transit.maintenance'].search([
            ('state', 'in', ['scheduled', 'in_progress']),
            ('next_service_date', '!=', False),
            ('next_service_date', '<=', threshold),
        ])
        recipients = self._get_ops_users()
        for rec in records:
            days_left = (rec.next_service_date - today).days
            if days_left < 0:
                severity = 'danger'
                title = f"Maintenance Overdue: {rec.vehicle_id.name}"
                message = f"Maintenance is overdue by {abs(days_left)} day(s) for vehicle {rec.vehicle_id.name}."
            else:
                severity = 'danger' if days_left <= 3 else 'info'
                title = f"Maintenance Due Soon: {rec.vehicle_id.name}"
                message = f"Maintenance is due in {days_left} day(s) for vehicle {rec.vehicle_id.name}."
            for user in recipients:
                self._notify_user(
                    user=user, notification_type='maintenance_due', title=title,
                    message=message, severity=severity,
                    res_model='transit.maintenance', res_id=rec.id,
                    vehicle_id=rec.vehicle_id.id, dedup_hours=20,
                )

    def _cron_check_trip_delayed(self):
        now = fields.Datetime.now()
        trips = self.env['transit.trip'].search([
            ('state', 'in', ['scheduled', 'ongoing']),
            ('scheduled_arrival', '!=', False),
            ('scheduled_arrival', '<', now),
            ('actual_arrival', '=', False),
        ])
        ops_users = self._get_ops_users()
        for trip in trips:
            delay_minutes = int((now - trip.scheduled_arrival).total_seconds() / 60)
            if delay_minutes < 15:
                continue

            if trip.state != 'delayed':
                trip.write({'state': 'delayed'})

            severity = 'danger' if delay_minutes > 60 else 'warning'
            title = f"Trip Delayed: {trip.name}"
            route = f"{trip.origin or '?'} \u2192 {trip.destination or '?'}"
            message = f"Trip {trip.name} ({route}) is delayed by {delay_minutes} minute(s)."

            recipients = ops_users
            if trip.driver_id.user_id:
                recipients |= trip.driver_id.user_id

            for user in recipients:
                self._notify_user(
                    user=user, notification_type='trip_delayed', title=title,
                    message=message, severity=severity,
                    res_model='transit.trip', res_id=trip.id,
                    vehicle_id=trip.vehicle_id.id, driver_id=trip.driver_id.id,
                    trip_id=trip.id, dedup_hours=1,
                )

    def _cron_check_fuel_budget(self):
        today = fields.Date.context_today(self)
        month_start = today.replace(day=1)
        vehicles = self.env['transit.vehicle'].search([('monthly_fuel_budget', '>', 0)])
        recipients = self._get_ops_users()
        for vehicle in vehicles:
            logs = self.env['transit.fuel.log'].search([
                ('vehicle_id', '=', vehicle.id),
                ('date', '>=', month_start),
                ('date', '<=', today),
            ])
            total = sum(logs.mapped('total_cost'))
            if total <= vehicle.monthly_fuel_budget:
                continue

            over_amount = total - vehicle.monthly_fuel_budget
            title = f"Fuel Budget Exceeded: {vehicle.name}"
            message = (
                f"Vehicle {vehicle.name} has spent {total:.2f} on fuel this month, "
                f"exceeding its budget of {vehicle.monthly_fuel_budget:.2f} by {over_amount:.2f}."
            )
            for user in recipients:
                self._notify_user(
                    user=user, notification_type='fuel_budget_exceeded', title=title,
                    message=message, severity='danger',
                    res_model='transit.vehicle', res_id=vehicle.id,
                    vehicle_id=vehicle.id, dedup_hours=20,
                )
