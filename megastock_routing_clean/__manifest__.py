# -*- coding: utf-8 -*-
{
    'name': 'MEGASTOCK Routing & BOM Clean',
    'version': '16.0.2.0.0',
    'category': 'Manufacturing',
    'summary': 'Rutas de producción y BOM especializados para MEGASTOCK',
    'description': """
Módulo de Rutas y BOM para MEGASTOCK

Funcionalidades principales:

* Rutas de manufactura por tipo de producto corrugado
* BOM (Bill of Materials) detallados con consumos reales
* Operaciones de ruta con tiempos específicos por centro de trabajo
* Consumos automáticos de materias primas por producto
* Rutas alternativas para diferentes tipos de cajas y láminas
* Cálculo automático de costos de producción
* Templates de BOM para productos estándar FEFCO
* Control de calidad integrado en puntos críticos
* Planificación automática basada en capacidades reales
* Reportes de eficiencia de rutas de producción
* Integración completa con sistema de inventarios y máquinas
    """,
    'author': 'MEGASTOCK',
    'website': 'https://megastock.com',
    'depends': [
        'base',
        'mrp',
        'stock',
        'product',
        'megastock_base',
        'megastock_products',
        'megastock_inventory_clean',
    ],
    'data': [
        # Todos los archivos comentados - modelos mrp.routing no existen
        # 'data/routing_templates_data.xml',
        # 'data/bom_templates_data.xml',
        # 'data/quality_points_data.xml',
        # 'data/cost_structure_data.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}