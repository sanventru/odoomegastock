# -*- coding: utf-8 -*-
{
    'name': 'MEGASTOCK Production Planning',
    'version': '16.0.2.0.0',
    'category': 'Manufacturing',
    'summary': 'Sistema MES completo para MEGASTOCK',
    'description': 'Sistema de Planificacion y Control de Produccion MES para MEGASTOCK',
    'author': 'MEGASTOCK',
    'website': 'https://megastock.com.ec',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mrp',
        'stock',
        'hr',
        'megastock_base',
        'megastock_products_v2',
        'megastock_bom_simple',
    ],
    'data': [
        'security/production_planning_security.xml',
        'security/ir.model.access.csv',
        'data/alert_automation_data.xml',
        'data/cron_jobs_data.xml',
        'views/production_plan_views.xml',
        'views/production_alert_views.xml',
        'views/alert_automation_views.xml',
        'views/dashboard_views.xml',
        'views/production_order_views.xml',
        'views/order_import_wizard_views.xml',
        'views/production_order_menu.xml',
    ],
    # 'assets': {
    #     'web.assets_backend': [
    #         # CSS y JS del módulo (comentado hasta que se creen los archivos)
    #     ],
    # },
    'external_dependencies': {
        'python': ['numpy', 'scipy', 'pandas'],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'sequence': 107,
}