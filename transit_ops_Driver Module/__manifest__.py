# -*- coding: utf-8 -*-
{
    'name': 'TransitOps - Smart Transport Operations Platform',
    'version': '18.0.1.0.0',
    'category': 'Operations/Fleet',
    'summary': 'End-to-end transport operations: vehicles, drivers, dispatch, '
                'maintenance, fuel & expenses, reporting and alerts.',
    'description': """
TransitOps - Smart Transport Operations Platform
=================================================
A unified operations platform for transport & logistics companies built on Odoo 18.

Key Features
------------
* Real-time Operations Dashboard (fleet health, trips, alerts, KPIs)
* Vehicle Registry (documents, insurance/RC/permit expiry tracking)
* Driver Management (license validity, assignments, performance)
* Trip Dispatch (scheduling, live status, vehicle/driver allocation)
* Maintenance Management (preventive & breakdown, service history, cost tracking)
* Fuel & Expense Tracking (mileage analytics, cost centers)
* Reports (PDF/XLSX operational and financial reports)
* Notifications & Alerts (document expiry, maintenance due, trip status)
* Role Based Security (Manager, Dispatcher, Driver, Mechanic)
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
        # security
        'security/transit_ops_security.xml',
        'security/ir.model.access.csv',
        'security/transit_driver_security.xml',

        # data
        'data/transit_ops_sequence_data.xml',

        # views / menus
        'views/transit_ops_menus.xml',
        'views/transit_vehicle_views.xml',
        'views/transit_driver_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'transit_ops/static/src/scss/transit_ops_theme.scss',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'sequence': 1,
    'icon': '/transit_ops/static/description/icon.png',
}
