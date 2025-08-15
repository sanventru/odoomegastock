# -*- coding: utf-8 -*-
{
    'name': 'MEGASTOCK BOM Simple',
    'version': '16.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'BOM Inteligente básico para MEGASTOCK',
    'description': """BOM Inteligente Simplificado para MEGASTOCK - Extensión de BOM con campos inteligentes""",
    'author': 'Claude Code Assistant',
    'depends': [
        'base',
        'mrp',
        'megastock_base',
        'megastock_products_backup',
    ],
    'data': [
        'views/mrp_bom_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}