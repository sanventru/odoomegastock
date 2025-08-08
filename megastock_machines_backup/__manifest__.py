# -*- coding: utf-8 -*-
{
    'name': 'MEGASTOCK Machines & Workcenters',
    'version': '16.0.2.0.0',
    'category': 'Manufacturing',
    'summary': 'Gestión avanzada de máquinas y centros de trabajo para MEGASTOCK',
    'description': """
Módulo de Máquinas y Centros de Trabajo para MEGASTOCK

Funcionalidades principales:

* Parámetros técnicos detallados por máquina (capacidades, dimensiones máximas)
* Tiempos específicos: Setup, operación, limpieza por centro de trabajo
* Consumos: Energía, materiales auxiliares por máquina
* Asignación de operadores por turno y máquina
* Sistema de mantenimiento preventivo con calendarios automáticos
* Registro y seguimiento de mantenimiento correctivo
* Inventario especializado de repuestos por máquina
* Alertas de mantenimiento automáticas
* Registro de fallas y paradas no programadas
* Dashboard de eficiencia y disponibilidad de máquinas
    """,
    'author': 'MEGASTOCK',
    'website': 'https://megastock.com',
    'depends': [
        'base',
        'mrp',
        'stock',
        'hr',
        # 'maintenance',  # Comentado - causa errores de usuarios
        # 'project',      # Comentado - puede causar problemas
        'megastock_base',
        'megastock_products',
        'megastock_inventory_clean',
    ],
    'data': [
        'data/machine_parameters_data.xml',
        # 'data/maintenance_types_data.xml',  # Comentado - depende de maintenance
        # 'data/spare_parts_data.xml',        # Comentado - depende de maintenance
        'data/operator_shifts_data.xml',
        'views/mrp_workcenter_views.xml',
        # 'views/maintenance_request_views.xml',    # Comentado - depende de maintenance
        # 'views/maintenance_equipment_views.xml',  # Comentado - depende de maintenance
        'views/machine_operator_views.xml',
        'views/machine_downtime_views.xml',
        # 'wizard/maintenance_schedule_wizard_views.xml', # Comentado - depende de maintenance
        # 'wizard/downtime_analysis_wizard_views.xml',    # Comentado - puede depender de maintenance
        'reports/machine_efficiency_report.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}