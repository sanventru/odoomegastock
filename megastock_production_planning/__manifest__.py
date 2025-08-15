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
        'megastock_products_simple',
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
    ],
    'assets': {
        'web.assets_backend': [
            # Librerías locales (sin dependencias CDN)
            'megastock_production_planning/static/lib/moment.min.js',
            'megastock_production_planning/static/lib/chart.min.js',
            'megastock_production_planning/static/lib/d3.min.js',
            # CSS y JS del módulo
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