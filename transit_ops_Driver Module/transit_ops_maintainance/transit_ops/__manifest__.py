# -*- coding: utf-8 -*-
{
    'name': 'TransitOps - Smart Transport Operations Platform',
    'version': '18.0.1.0.0',
    'category': 'Operations/Transportation',
    'summary': 'Smart Transport Operations Platform: Fleet, Drivers, Dispatch, Maintenance & Fuel Management',
    'description': """
TransitOps - Smart Transport Operations Platform
==================================================
A complete transport operations management system built on Odoo 18.

Features:
---------
* Real-time Operations Dashboard
* Vehicle Registry with document/compliance tracking
* Driver Management with license tracking
* Trip Dispatch & Scheduling
* Preventive & Corrective Maintenance
* Fuel & Expense Tracking
* Reports (PDF & Excel)
* In-app Notifications
* Role Based Access Control
    """,
    'author': 'TransitOps Team',
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

        # Data / Automation
        'data/transit_maintenance_cron.xml',

        # Views
        'views/transit_maintenance_views.xml',

        # Menus (must load after all actions referenced)
        'views/transit_ops_menus.xml',
    ],
    'assets': {},
    'installable': True,
    'application': True,
    'auto_install': False,
}
