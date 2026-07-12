# -*- coding: utf-8 -*-
{
    'name': 'TransitOps - Smart Transport Operations Platform',
    'version': '18.0.1.0.0',
    'category': 'Operations/Fleet',
    'summary': 'Smart transport operations: vehicles, drivers, dispatch, maintenance, fuel & notifications.',
    'description': """
TransitOps - Smart Transport Operations Platform
==================================================
This package (Notification System build) includes:

* Vehicle Registry
* Minimal core Driver / Trip / Maintenance / Fuel Log models
  (full versions delivered in dedicated batches; these provide the
  fields required for the notification engine to function end-to-end)
* Notification Engine with 5 automated alert types:
  - Insurance Expiry
  - License Expiry
  - Maintenance Due
  - Trip Delayed
  - Fuel Budget Exceeded
* Scheduled Actions (ir.cron) driving each alert
* Bell icon systray widget with live unread count (OWL)
* Role based security (Driver / Dispatcher / Manager)
    """,
    'author': 'TransitOps Team',
    'website': 'https://www.transitops.example.com',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'web', 'bus'],
    'data': [
        # Security
        'security/transit_ops_security.xml',
        'security/ir.model.access.csv',

        # Data
        'data/ir_sequence_data.xml',
        'data/ir_cron_data.xml',

        # Views
        'views/transit_vehicle_views.xml',
        'views/transit_driver_views.xml',
        'views/transit_trip_views.xml',
        'views/transit_maintenance_views.xml',
        'views/transit_fuel_views.xml',
        'views/transit_notification_views.xml',
        'views/transit_ops_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'transit_ops/static/src/css/notification_systray.css',
            'transit_ops/static/src/js/notification_systray.js',
            'transit_ops/static/src/xml/notification_systray.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
