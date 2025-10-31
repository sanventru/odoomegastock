# -*- coding: utf-8 -*-
{
    'name': 'MEGASTOCK Orders',
    'version': '16.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Gestión de Pedidos MEGASTOCK desde CSV',
    'description': """
Módulo de Pedidos MEGASTOCK

Funcionalidades:
* Importación de pedidos desde archivos CSV
* Gestión completa de órdenes de producción
* Seguimiento de materiales y especificaciones técnicas
* Dashboard de pedidos y estados
* Integración con productos MEGASTOCK
    """,
    'author': 'MEGASTOCK',
    'website': 'https://megastock.com.ec',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'sale',
        'stock',
        'mrp',
        'mail',
        'megastock_base',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/production_order_views.xml',
        'views/bobina_views.xml',
        'views/paper_recipe_views.xml',
        'views/flauta_views.xml',
        'views/proceso_preprinter_views.xml',
        'views/proceso_microcorrugado_views.xml',
        'views/proceso_dobladora_views.xml',
        'views/proceso_corte_ceja_views.xml',
        'views/proceso_corte_guillotina_views.xml',
        'views/proceso_empaque_views.xml',
        'views/proceso_almacenamiento_views.xml',
        'views/work_order_views.xml',
        'wizards/requiere_doblez_wizard_views.xml',
        'wizards/generar_ordenes_wizard_views.xml',
        'views/order_import_wizard_views.xml',
        'views/planificacion_wizard_views.xml',
        'views/weight_calculator_views.xml',
        'views/menu_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'sequence': 110,
    'post_init_hook': 'post_init_hook',
}
