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
        'megastock_products',
        'megastock_inventory_clean',
        'megastock_machines',
        'megastock_routing_basic',
        'mrp_production_lines'
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
    ],
    'assets': {
        'web.assets_backend': [
            'megastock_production_planning/static/src/css/dashboard.css',
            'megastock_production_planning/static/src/js/production_dashboard.js',
            'megastock_production_planning/static/src/js/kpi_dashboard.js',
            'megastock_production_planning/static/src/js/capacity_dashboard.js',
            'megastock_production_planning/static/src/js/schedule_gantt.js',
            'megastock_production_planning/static/src/js/alert_dashboard.js',
        ],
        'web.assets_qweb': [
            'megastock_production_planning/static/src/xml/dashboard_templates.xml',
        ],
    },
    'external_dependencies': {
        'python': ['numpy', 'scipy', 'pandas'],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'sequence': 107,
}