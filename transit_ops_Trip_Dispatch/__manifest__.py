# -*- coding: utf-8 -*-
{
    'name': 'TransitOps - Smart Transport Operations Platform',
    'version': '18.0.1.0.0',
    'category': 'Operations/Transport',
    'summary': 'Manage fleet, drivers, trips, maintenance, fuel and expenses in one place.',
    'description': """
TransitOps - Smart Transport Operations Platform
=================================================
A complete transport operations management system built on Odoo 18.

Features:
---------
* Operations Dashboard with live KPIs
* Vehicle Registry with document/insurance tracking
* Driver Management with license expiry tracking
* Trip Dispatch & Scheduling
* Preventive & Corrective Maintenance
* Fuel & Expense logging with cost analytics
* Reports (PDF & Excel style views)
* In-app Notifications & Activities
* Role Based Access Control (Dispatcher / Fleet Manager / Administrator)
* Modern dark theme with orange accents
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
        'security/transit_security.xml',
        'security/ir.model.access.csv',

        # Sequences
        'data/trip_sequence.xml',

        # Menus (root) - must load before feature views that attach child menu items
        'views/transit_menus.xml',

        # Views - Vehicle
        'views/vehicle_views.xml',

        # Views - Driver
        'views/driver_views.xml',

        # Views - Trip Dispatch
        'views/trip_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'transit_ops/static/src/scss/transit_theme.scss',
        ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
