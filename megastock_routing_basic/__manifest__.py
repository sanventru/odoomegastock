# -*- coding: utf-8 -*-
{
    'name': 'MEGASTOCK Routing Basic',
    'version': '16.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Módulo básico de routing para MEGASTOCK',
    'description': """
Módulo básico de routing para MEGASTOCK

Este es un módulo mínimo que sirve como placeholder.
    """,
    'author': 'MEGASTOCK',
    'website': 'https://megastock.com',
    'depends': [
        'base',
        'mrp',
        'stock',
        'product',
        'megastock_base',
        'megastock_products',
        'megastock_inventory_clean',
    ],
    'data': [
        'data/basic_routing_data.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}