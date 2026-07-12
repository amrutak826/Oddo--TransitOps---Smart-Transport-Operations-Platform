# -*- coding: utf-8 -*-
{
    'name': 'TransitOps - Smart Transport Operations Platform',
    'version': '18.0.1.0.0',
    'category': 'Operations/Fleet',
    'summary': 'Smart Transport Operations Platform - Vehicles, Drivers, Trips, Maintenance, Fuel & Expenses',
    'description': """
TransitOps - Smart Transport Operations Platform
==================================================
A complete transport operations management system built for Odoo 18 Community.

Features:
---------
* Real-time Operations Dashboard with KPIs
* Vehicle Registry with document & insurance tracking
* Driver Management with license expiry tracking
* Trip Dispatch with full lifecycle state machine
* Maintenance scheduling & service history
* Fuel logging & expense management
* PDF Reports (Trip Sheet, Maintenance History, Fuel Summary)
* In-app notifications for expiries and dispatch events
* Role based security (Manager, Dispatcher, Driver, Viewer)
* Modern dark theme with orange accents
    """,
    'author': 'TransitOps Hackathon Team',
    'website': 'https://www.transitops.example',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'web',
    ],
    'data': [
        # Security
        'security/transit_security.xml',
        'security/ir.model.access.csv',

        # Data
        'data/ir_sequence_data.xml',
        'data/transit_cron_data.xml',
        'data/mail_template_data.xml',

        # Views - Vehicle
        'views/transit_vehicle_views.xml',

        # Views - Driver
        'views/transit_driver_views.xml',

        # Views - Trip
        'views/transit_trip_views.xml',

        # Views - Maintenance
        'views/transit_maintenance_views.xml',

        # Views - Fuel Log
        'views/transit_fuel_log_views.xml',

        # Dashboard
        'views/transit_dashboard_views.xml',

        # ------------------------------------------------------------
        # NOTE FOR NEXT BUILD PARTS: append new view/report entries here
        # in this order as they are created -
        #   views/transit_expense_views.xml
        #   views/transit_notification_views.xml
        #   reports/transit_report_templates.xml
        #   reports/transit_trip_sheet_report.xml
        #   reports/transit_maintenance_report.xml
        #   reports/transit_fuel_summary_report.xml
        # 'views/transit_menus.xml' must always stay LAST since it
        # references actions defined in every file above it.
        # ------------------------------------------------------------

        # Menus (loaded last so all actions exist)
        'views/transit_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'transit_ops/static/src/scss/transit_theme.scss',
            'transit_ops/static/src/scss/transit_dashboard.scss',
            'transit_ops/static/src/js/transit_dashboard.js',
            'transit_ops/static/src/xml/transit_dashboard_templates.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
