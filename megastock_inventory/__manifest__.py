# -*- coding: utf-8 -*-
{
    'name': 'MEGASTOCK Inventory (DEPRECATED STUB)',
    'version': '16.0.0.0.1',
    'category': 'Hidden',
    'summary': 'DEPRECATED - Use megastock_inventory_clean instead',
    'description': '''
This is a STUB module that exists ONLY to satisfy legacy dependencies.

*** THIS MODULE DOES ABSOLUTELY NOTHING ***

All actual functionality has been moved to:
- megastock_inventory_clean

This module will be removed in future versions.
''',
    'author': 'MEGASTOCK - STUB',
    'website': 'https://megastock.com',
    'depends': [
        'base',
        'megastock_inventory_clean',  # Redirect everything to the real module
    ],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}