# -*- coding: utf-8 -*-
{
    'name': 'TransitOps - Smart Transport Operations Platform',
    'version': '18.0.1.0.0',
    'category': 'Operations/Transport',
    'summary': 'Smart Transport Operations Platform - Fleet, Drivers, Trips, Maintenance & Fuel Management',
    'description': """
TransitOps - Smart Transport Operations Platform
==================================================
A complete transport operations management system built on Odoo 18.

Features:
---------
* Vehicle Registry - manage fleet vehicles, documents, and status
* Driver Management - driver profiles, licenses, assignments
* Trip Dispatch - plan, assign and track trips in real time
* Maintenance - preventive & corrective maintenance scheduling
* Fuel & Expense - fuel logs, expense tracking and cost analytics
* Dashboard - real-time KPIs and operational overview
* Reports - PDF reports for trips, maintenance and fuel usage
* Notifications - automated alerts for expiring documents, due maintenance
* Role Based Security - Fleet Manager, Dispatcher, Driver, Viewer access levels
    """,
    'author': 'TransitOps Team',
    'website': 'https://www.transitops.example.com',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'web'],
    'data': [
        # Security
        'security/transit_ops_security.xml',
        'security/ir.model.access.csv',

        # Data
        'data/ir_sequence_data.xml',

        # Views - Vehicle
        'views/transit_vehicle_views.xml',

        # Dashboard
        'views/transit_dashboard_views.xml',

        # Menus (loaded last so all actions exist)
        'views/transit_ops_menus.xml',

        # --- The following will be added as they are built in this project ---
        # 'data/ir_cron_data.xml',
        # 'data/mail_template_data.xml',
        # 'views/transit_driver_views.xml',
        # 'views/transit_trip_views.xml',
        # 'views/transit_maintenance_views.xml',
        # 'views/transit_fuel_log_views.xml',
        # 'views/transit_expense_views.xml',
        # 'views/transit_notification_views.xml',
        # 'reports/transit_report_templates.xml',
        # 'reports/transit_trip_report.xml',
        # 'reports/transit_maintenance_report.xml',
        # 'reports/transit_fuel_report.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.4/chart.umd.min.js',
            'transit_ops/static/src/css/transit_ops.css',
            'transit_ops/static/src/js/dashboard.js',
            'transit_ops/static/src/xml/dashboard.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
