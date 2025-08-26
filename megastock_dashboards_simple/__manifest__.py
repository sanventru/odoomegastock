# -*- coding: utf-8 -*-
{
    'name': 'MEGASTOCK Dashboards Simple',
    'version': '16.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Dashboards web básicos para MEGASTOCK con librerías locales',
    'description': 'Sistema de dashboards web simplificado sin dependencias CDN',
    'author': 'Claude Code Assistant',
    'website': 'https://megastock.com.ec',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mrp',
        'stock',
        'megastock_base',
        'megastock_products_v2',
        'megastock_bom_simple',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/dashboard_views.xml',
        'views/production_kpi_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # Librerías locales (sin dependencias CDN)
            'megastock_dashboards_simple/static/lib/moment.min.js',
            'megastock_dashboards_simple/static/lib/chart.min.js',
            'megastock_dashboards_simple/static/lib/d3.min.js',
            # CSS y JS del módulo
            'megastock_dashboards_simple/static/src/css/dashboard.css',
            'megastock_dashboards_simple/static/src/js/megastock_dashboard.js',
        ],
        'web.assets_qweb': [
            'megastock_dashboards_simple/static/src/xml/dashboard_templates.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'sequence': 108,
}