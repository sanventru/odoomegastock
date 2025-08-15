# -*- coding: utf-8 -*-
{
    'name': 'MEGASTOCK Products v2',
    'version': '16.0.2.0.0',
    'category': 'Manufacturing',
    'summary': 'Gestión completa de productos para MEGASTOCK',
    'description': """
MEGASTOCK Products v2 - Gestión Completa de Productos

Funcionalidades:
* Especificaciones técnicas para productos de cartón
* Códigos automáticos MEGASTOCK
* Atributos especializados
* Variantes inteligentes
""",
    'author': 'MEGASTOCK',
    'website': 'https://megastock.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'product',
        'stock',
        'mrp',
        'megastock_base',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/product_attributes.xml',
        'data/sequence_data.xml',
        'views/product_template_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}