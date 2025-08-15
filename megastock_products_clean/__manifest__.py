# -*- coding: utf-8 -*-
{
    'name': 'MEGASTOCK Products Clean',
    'version': '16.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Gestión de productos MEGASTOCK simplificada',
    'description': """
        Gestión de productos para MEGASTOCK - Versión limpia y funcional
        ===============================================================
        
        Características:
        - Campos básicos para productos
        - Categorías MEGASTOCK
        - Dimensiones y especificaciones
        - Sin funcionalidades complejas
    """,
    'author': 'Claude Code Assistant',
    'depends': ['megastock_base', 'stock'],
    'data': [
        'views/product_template_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}