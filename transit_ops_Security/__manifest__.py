# -*- coding: utf-8 -*-
{
    'name': 'TransitOps - Smart Transport Operations Platform',
    'version': '18.0.1.0.0',
    'category': 'Operations/Fleet',
    'summary': 'Smart Transport Operations Platform - Vehicles, Drivers, Trips, Maintenance, Fuel & Reports',
    'description': """
TransitOps - Smart Transport Operations Platform
==================================================
A complete transport operations management system built on Odoo 18.

Features
--------
* Real-time Operations Dashboard
* Vehicle Registry with document expiry tracking
* Driver Management with license tracking
* Trip Dispatch & Scheduling
* Preventive & Corrective Maintenance
* Fuel Logging & Expense Management
* Operational Reports (PDF)
* Automated Notifications & Alerts
* Role Based Security (Admin / Manager / Dispatcher / Driver)
* Modern Dark Theme with Orange Accents

Build Note
----------
This module is being delivered in incremental batches. This manifest lists
only the files that exist so far; it is extended batch by batch as new
features (Trip Dispatch, Maintenance, Fuel & Expense, Notifications,
Reports, Dashboard) are added, so the module stays installable at every
stage of the build.
    """,
    'author': 'TransitOps Hackathon Team',
    'website': 'https://www.transitops.example.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'web',
    ],
    'data': [
        # Security
        'security/transit_ops_security.xml',
        'security/ir.model.access.csv',

        # Data
        'data/transit_sequence_data.xml',

        # Views - Vehicle
        'views/transit_vehicle_views.xml',
        # Views - Driver
        'views/transit_driver_views.xml',
        # Views - Trip
        'views/transit_trip_views.xml',
        # Views - Maintenance
        'views/transit_maintenance_views.xml',
        # Views - Fuel & Expense
        'views/transit_fuel_expense_views.xml',
        # Views - Notifications
        'views/transit_notification_views.xml',

        # Menus (loaded last so all actions exist)
        'views/transit_ops_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'transit_ops/static/src/css/transit_theme.css',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
