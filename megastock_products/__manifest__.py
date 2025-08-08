# -*- coding: utf-8 -*-
{
    'name': 'MEGASTOCK Products & Specifications',
    'version': '16.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Maestros de productos y especificaciones técnicas para MEGASTOCK',
    'description': """
Módulo de Productos y Especificaciones Técnicas para MEGASTOCK

Funcionalidades principales:

* Atributos técnicos personalizados (dimensiones, especificaciones cartón, materiales, colores)
* Sistema de codificación de productos (30170728, 30170062, etc.)
* Plantillas de productos por categoría
* Validaciones automáticas para códigos
* Variantes de productos con combinaciones de atributos
* Estructura para migración de códigos existentes
    """,
    'author': 'MEGASTOCK',
    'website': 'https://megastock.com',
    'depends': [
        'base',
        'product',
        'stock',
        'sale',
        'purchase',
        'mrp',
        'megastock_base',
    ],
    'data': [
        'data/product_attributes.xml',
        'data/product_templates.xml',
        'data/sequence_data.xml',
        'views/product_template_views.xml',
        'views/product_product_views.xml',
        'wizard/product_migration_wizard_views.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}