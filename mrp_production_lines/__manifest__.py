# -*- coding: utf-8 -*-
{
    'name': 'MRP Production Lines',
    'version': '16.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Gestión personalizada de líneas de producción',
    'description': """
        Módulo para gestión de líneas de producción específicas:
        - Línea Papel Periódico
        - Línea Cajas & Planchas  
        - Línea Lámina Micro Corrugada
    """,
    'author': 'Odoo Customization',
    'website': '',
    'depends': ['mrp'],
    'data': [
        'security/ir.model.access.csv',
        'views/mrp_workcenter_simple_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}