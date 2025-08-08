# -*- coding: utf-8 -*-
{
    'name': 'MEGASTOCK Intelligent BOM',
    'version': '16.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Listas de Materiales Inteligentes para MEGASTOCK',
    'description': """
BOM Inteligentes y Automáticos para MEGASTOCK

Funcionalidades principales:

* BOM dinámicos que se ajustan automáticamente según especificaciones del producto
* Cálculos automáticos de consumos basados en dimensiones reales y geometría
* Optimización automática de materiales y control inteligente de mermas
* BOM alternativos según disponibilidad de materias primas en tiempo real
* Análisis de costos en tiempo real con alertas por variaciones significativas
* Sistema de sustitución inteligente de materiales equivalentes
* Planificación automática de compras basada en explosión de BOM
* BOM por variantes de producto generados automáticamente
* Control de obsolescencia y vencimiento de materiales
* Reportes inteligentes de optimización y eficiencia de BOM
* Integración completa con inventarios, compras y planificación
* Motor de reglas de negocio configurable para decisiones automáticas
    """,
    'author': 'MEGASTOCK',
    'website': 'https://megastock.com',
    'depends': [
        'base',
        'mrp',
        'stock',
        'purchase',
        'product',
        'sale',
        'megastock_base',
        'megastock_products',
        'megastock_inventory_clean',
        'megastock_machines',
        'megastock_routing_basic',
    ],
    'data': [
        'data/bom_calculation_rules_data.xml',
        'data/material_substitution_rules_data.xml',
        'data/cost_optimization_data.xml',
        'data/purchase_planning_data.xml',
        'views/mrp_bom_intelligent_views.xml',
        'views/product_template_intelligent_views.xml',
        'views/bom_calculation_rule_views.xml',
        'views/material_substitution_views.xml',
        'views/bom_cost_analysis_views.xml',
        'wizard/bom_optimizer_wizard_views.xml',
        'wizard/material_substitution_wizard_views.xml',
        'wizard/purchase_planning_wizard_views.xml',
        'reports/intelligent_bom_report.xml',
        'reports/bom_optimization_report.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}