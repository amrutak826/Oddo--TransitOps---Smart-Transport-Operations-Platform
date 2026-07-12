# -*- coding: utf-8 -*-
from datetime import timedelta
from collections import OrderedDict

from odoo import api, fields, models


class TransitDashboard(models.AbstractModel):
    _name = 'transit.dashboard'
    _description = 'TransitOps Dashboard Data Provider'

    @api.model
    def get_dashboard_data(self):
        """Aggregate all KPI and chart data needed by the TransitOps dashboard.
        Values are scoped to the current user's company automatically via
        the ORM's implicit company/record rules.
        """
        Vehicle = self.env['transit.vehicle']
        Driver = self.env['transit.driver']
        Trip = self.env['transit.trip']
        Maintenance = self.env['transit.maintenance']
        FuelLog = self.env['transit.fuel.log']
        Expense = self.env['transit.expense']

        today = fields.Date.context_today(self)
        month_start = today.replace(day=1)
        week_ago = today - timedelta(days=6)

        # ================= KPI Cards =================
        total_vehicles = Vehicle.search_count([])
        available_vehicles = Vehicle.search_count([('state', '=', 'available')])
        total_drivers = Driver.search_count([('active', '=', True)])

        trips_today = Trip.search_count([
            ('scheduled_start', '>=', f'{today} 00:00:00'),
            ('scheduled_start', '<=', f'{today} 23:59:59'),
        ])

        fuel_logs_month = FuelLog.search([('date', '>=', month_start), ('date', '<=', today)])
        fuel_cost_month = sum(fuel_logs_month.mapped('total_cost'))

        maintenance_due = Maintenance.search_count([('state', 'in', ('due', 'in_progress'))])

        expenses_month = Expense.search([('date', '>=', month_start), ('date', '<=', today)])
        monthly_expense = sum(expenses_month.mapped('amount')) + fuel_cost_month

        currency = self.env.company.currency_id
        currency_symbol = currency.symbol or ''
        currency_position = currency.position or 'before'

        # ================= Chart: Vehicle Status Breakdown =================
        vehicle_status_labels = OrderedDict([
            ('available', 'Available'),
            ('on_trip', 'On Trip'),
            ('maintenance', 'Maintenance'),
            ('inactive', 'Inactive'),
        ])
        vehicle_status_data = []
        for key, label in vehicle_status_labels.items():
            vehicle_status_data.append(Vehicle.search_count([('state', '=', key)]))

        # ================= Chart: Trips over last 7 days =================
        trip_labels = []
        trip_data = []
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            count = Trip.search_count([
                ('scheduled_start', '>=', f'{day} 00:00:00'),
                ('scheduled_start', '<=', f'{day} 23:59:59'),
            ])
            trip_labels.append(day.strftime('%d %b'))
            trip_data.append(count)

        # ================= Chart: Fuel usage last 7 days (cost) =================
        fuel_labels = []
        fuel_data = []
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            logs = FuelLog.search([('date', '=', day)])
            fuel_labels.append(day.strftime('%d %b'))
            fuel_data.append(round(sum(logs.mapped('total_cost')), 2))

        # ================= Chart: Expenses by category (this month) =================
        expense_category_labels = OrderedDict([
            ('toll', 'Toll'),
            ('parking', 'Parking'),
            ('repair', 'Minor Repair'),
            ('permit', 'Permit / Fine'),
            ('food', 'Food / Allowance'),
            ('other', 'Other'),
        ])
        expense_category_data = []
        for key, label in expense_category_labels.items():
            cat_expenses = expenses_month.filtered(lambda e, k=key: e.category == k)
            expense_category_data.append(round(sum(cat_expenses.mapped('amount')), 2))

        return {
            'kpis': {
                'total_vehicles': total_vehicles,
                'available_vehicles': available_vehicles,
                'total_drivers': total_drivers,
                'trips_today': trips_today,
                'fuel_cost_month': round(fuel_cost_month, 2),
                'maintenance_due': maintenance_due,
                'monthly_expense': round(monthly_expense, 2),
                'currency_symbol': currency_symbol,
                'currency_position': currency_position,
            },
            'charts': {
                'vehicle_status': {
                    'labels': list(vehicle_status_labels.values()),
                    'data': vehicle_status_data,
                },
                'trips': {
                    'labels': trip_labels,
                    'data': trip_data,
                },
                'fuel_usage': {
                    'labels': fuel_labels,
                    'data': fuel_data,
                },
                'expenses': {
                    'labels': list(expense_category_labels.values()),
                    'data': expense_category_data,
                },
            },
        }
