# -*- coding: utf-8 -*-
{
    'name': 'MEGASTOCK - Planificación y Control de Producción',
    'version': '16.0.2.0.0',
    'category': 'Manufacturing',
    'summary': 'Sistema MES completo de planificación y control de producción para MEGASTOCK',
    'description': '''
Sistema de Planificación y Control de Producción (MES) para MEGASTOCK

Sistema integral de Manufacturing Execution System (MES) diseñado específicamente 
para la industria de cartón corrugado, que incluye:

Planificación Inteligente:
• Algoritmo MRP avanzado con optimización por restricciones
    • Planificación automática basada en demanda y capacidad
    • Cálculo de lotes óptimos y balanceamiento de líneas
    • Motor de reglas configurable por prioridades
    
Control de Capacidad:
• Gestión dinámica de capacidad finita e infinita  
    • Análisis de cuellos de botella en tiempo real
    • Optimización de recursos y asignación de operadores
    • Manejo de turnos y horas extra automático
    
Colas y Secuenciación:
• Administrador de colas dinámicas por línea de producción
    • Algoritmos avanzados de scheduling (FIFO, SPT, EDD, GA)
    • Rebalanceo automático por contingencias
    • Buffer management e inventarios en proceso
    
Monitoreo Tiempo Real:
• Dashboard de control con KPIs en vivo (OEE, eficiencia)
    • Sistema de alertas predictivas y escalación
    • Gantt charts dinámicos y mapas de calor
    • Comparativo plan vs real continuo
    
Características Específicas Corrugado:
• Papel periódico: Optimización cambios bobina y mermas
    • Cajas/Planchas: Secuenciación por flauta y setup moldes  
    • Microcorrugado: Control de tolerancias y calidad especial
    
Análisis y Reportes:
• Análisis de performance y tendencias
    • Benchmarking interno entre líneas/turnos
    • Predictive analytics y pronósticos
    • Reportes gerenciales automatizados
    ''',
    'author': 'MEGASTOCK - Claude AI Assistant',
    'website': 'https://megastock.com.ec',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mrp',
        'stock',
        # 'quality_control',  # Comentado - no existe en esta instalación
        'hr',
        'megastock_base',
        'megastock_products',
        'megastock_inventory_clean', 
        'megastock_machines',
        'megastock_routing_basic',
        # 'megastock_intelligent_bom',  # Comentado temporalmente - se instalará después
        'mrp_production_lines'
    ],
    'data': [
        # Security
        'security/production_planning_security.xml',
        'security/ir.model.access.csv',
        
        # Data - Solo archivos que existen
        # 'data/planning_rules_data.xml',          # NO EXISTE
        # 'data/sequence_data.xml',                # NO EXISTE
        # 'data/scheduling_algorithms_data.xml',   # NO EXISTE  
        # 'data/kpi_definitions_data.xml',         # NO EXISTE
        'data/alert_automation_data.xml',           # EXISTE
        'data/cron_jobs_data.xml',                  # EXISTE
        
        # Views - Solo las que existen
        # 'views/production_plan_views.xml',        # NO EXISTE
        # 'views/capacity_planning_views.xml',      # NO EXISTE
        # 'views/production_schedule_views.xml',    # NO EXISTE
        # 'views/work_queue_views.xml',             # NO EXISTE
        # 'views/production_kpi_views.xml',         # NO EXISTE
        
        # Views - Analysis & Reports
        # 'views/production_analysis_views.xml',    # NO EXISTE
        # 'views/capacity_analysis_views.xml',      # NO EXISTE
        # 'views/schedule_compliance_views.xml',    # NO EXISTE
        
        # Views - Alerts (ESTAS SÍ EXISTEN)
        'views/production_alert_views.xml',         # EXISTE
        'views/alert_automation_views.xml',         # EXISTE
        'views/dashboard_views.xml',                # EXISTE
        
        # Wizards - COMENTADOS: NO EXISTEN
        # 'wizard/production_planning_wizard_views.xml',     # NO EXISTE
        # 'wizard/capacity_analysis_wizard_views.xml',       # NO EXISTE
        # 'wizard/rescheduling_wizard_views.xml',            # NO EXISTE
        
        # Reports - COMENTADOS: NO EXISTEN
        # 'reports/production_performance_report.xml',       # NO EXISTE
        # 'reports/capacity_utilization_report.xml',         # NO EXISTE
        # 'reports/schedule_compliance_report.xml',          # NO EXISTE
        
        # Menu - COMENTADO: NO EXISTE
        # 'views/menu_views.xml',                            # NO EXISTE
        
        # Dashboard - YA INCLUIDO ARRIBA
        # 'views/dashboard_views.xml',                       # DUPLICADO
        
        # Cron Jobs - YA INCLUIDO ARRIBA  
        # 'data/cron_jobs_data.xml',                         # DUPLICADO
    ],
    'demo': [
        # 'demo/production_planning_demo.xml',    # NO EXISTE
    ],
    'assets': {
        'web.assets_backend': [
            # CSS
            'megastock_production_planning/static/src/css/dashboard.css',
            
            # JavaScript Libraries (CDN fallback via external dependencies)
            ('include', 'web._assets_helpers'),
            
            # Dashboard JavaScript
            'megastock_production_planning/static/src/js/production_dashboard.js',
            'megastock_production_planning/static/src/js/kpi_dashboard.js',
            'megastock_production_planning/static/src/js/capacity_dashboard.js',
            'megastock_production_planning/static/src/js/schedule_gantt.js',
            'megastock_production_planning/static/src/js/alert_dashboard.js',
        ],
        'web.assets_qweb': [
            'megastock_production_planning/static/src/xml/dashboard_templates.xml',
        ],
        'web.assets_frontend': [
            # Para vistas públicas de dashboard si es necesario
            'megastock_production_planning/static/src/css/dashboard.css',
        ],
    },
    'external_dependencies': {
        'python': ['numpy', 'scipy', 'pandas'],  # Para algoritmos de optimización
        'bin': [],
    },
    
    # Dependencias externas JavaScript (se cargan desde CDN)
    'external_js_dependencies': [
        'https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js',
        'https://cdn.jsdelivr.net/npm/moment@2.29.4/moment.min.js',
        'https://code.jquery.com/ui/1.13.2/jquery-ui.min.js',
        'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.2.0/js/all.min.js'
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'sequence': 107,
}