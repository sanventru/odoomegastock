# -*- coding: utf-8 -*-
{
    'name': 'MEGASTOCK Machines & Workcenters',
    'version': '16.0.2.0.0',
    'category': 'Manufacturing',
    'summary': 'Gestión avanzada de máquinas, operadores y turnos para MEGASTOCK',
    'description': """
Módulo de Máquinas y Centros de Trabajo para MEGASTOCK - FASE 2

Funcionalidades incluidas:

FASE 1 - Máquinas:
* Parámetros técnicos básicos por máquina (consumos energéticos)
* Dimensiones máximas de procesamiento
* Capacidades de producción teóricas y reales
* Estado operacional de máquinas
* Métricas OEE básicas
* Información básica de mantenimiento (fechas e intervalos)

FASE 2 - Operadores y Turnos:
* Gestión completa de operadores certificados
* Certificaciones por centro de trabajo
* Niveles de certificación (aprendiz a instructor)
* Calificaciones de performance (eficiencia, calidad, seguridad)
* Gestión de turnos y horarios de trabajo
* Estados de disponibilidad en tiempo real
* Capacidades de mantenimiento básico

NOTA: Implementación sin dependencias del módulo 'maintenance' de Odoo
    """,
    'author': 'MEGASTOCK',
    'website': 'https://megastock.com',
    'depends': [
        'base',
        'mrp',
        'hr',
        'megastock_base',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/machine_basic_data.xml',
        # 'data/test_data.xml',  # Comentado para versión simple
        'views/mrp_workcenter_simple_views.xml',  # Solo vista simple
        'views/machine_downtime_views.xml',  # Vista de paradas
        # 'views/mrp_workcenter_views.xml',  # Comentado temporalmente
        # 'views/machine_operator_views.xml',  # Comentado temporalmente
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}