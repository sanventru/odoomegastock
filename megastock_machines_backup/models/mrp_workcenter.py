# -*- coding: utf-8 -*-

from odoo import models, fields, api

class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'
    
    # ========== CAMPOS TÉCNICOS MEGASTOCK ==========
    
    # Consumos Energéticos
    power_consumption_kw = fields.Float(
        string='Consumo Energético (kW)',
        help='Potencia eléctrica consumida por hora en kW',
        default=0.0
    )
    
    energy_cost_per_hour = fields.Float(
        string='Costo Energía/Hora (USD)',
        help='Costo de energía eléctrica por hora de operación',
        compute='_compute_energy_cost_per_hour',
        store=True
    )
    
    # Consumos de Materiales Auxiliares
    compressed_air_consumption = fields.Float(
        string='Consumo Aire Comprimido (m³/h)',
        help='Metros cúbicos de aire comprimido por hora',
        default=0.0
    )
    
    hydraulic_oil_consumption = fields.Float(
        string='Consumo Aceite Hidráulico (L/mes)',
        help='Litros de aceite hidráulico consumidos por mes',
        default=0.0
    )
    
    lubricant_consumption = fields.Float(
        string='Consumo Lubricantes (kg/mes)',
        help='Kilogramos de lubricantes consumidos por mes',
        default=0.0
    )
    
    # Dimensiones Técnicas
    max_width_mm = fields.Integer(
        string='Ancho Máximo (mm)',
        help='Ancho máximo de material que puede procesar',
        default=0
    )
    
    max_length_mm = fields.Integer(
        string='Longitud Máxima (mm)',
        help='Longitud máxima de material que puede procesar',
        default=0
    )
    
    max_thickness_mm = fields.Float(
        string='Espesor Máximo (mm)',
        help='Espesor máximo de material que puede procesar',
        default=0.0
    )
    
    # Capacidades de Producción
    theoretical_capacity = fields.Float(
        string='Capacidad Teórica/Hora',
        help='Capacidad teórica máxima por hora',
        default=0.0
    )
    
    real_capacity = fields.Float(
        string='Capacidad Real/Hora',
        help='Capacidad real promedio por hora',
        compute='_compute_real_capacity',
        store=True
    )
    
    capacity_unit = fields.Selection([
        ('meters', 'Metros Lineales'),
        ('pieces', 'Piezas'),
        ('cuts', 'Cortes'),
        ('units', 'Unidades'),
        ('reams', 'Resmas')
    ], string='Unidad de Capacidad', default='pieces')
    
    # Estado de Máquina
    machine_status = fields.Selection([
        ('operational', 'Operativa'),
        ('maintenance', 'En Mantenimiento'),
        ('breakdown', 'Averiada'),
        ('setup', 'En Setup'),
        ('standby', 'En Espera')
    ], string='Estado de Máquina', default='operational')
    
    # Información de Mantenimiento
    last_maintenance_date = fields.Datetime(
        string='Último Mantenimiento',
        help='Fecha del último mantenimiento preventivo'
    )
    
    next_maintenance_date = fields.Datetime(
        string='Próximo Mantenimiento',
        help='Fecha programada para próximo mantenimiento'
    )
    
    maintenance_hours_interval = fields.Integer(
        string='Intervalo Mantenimiento (horas)',
        help='Horas de operación entre mantenimientos preventivos',
        default=200
    )
    
    total_operation_hours = fields.Float(
        string='Horas Totales de Operación',
        help='Total de horas operadas desde última revisión mayor',
        default=0.0
    )
    
    # Eficiencia y Performance
    oee_availability = fields.Float(
        string='Disponibilidad (%)',
        help='Porcentaje de disponibilidad (OEE)',
        compute='_compute_oee_metrics',
        store=True
    )
    
    oee_performance = fields.Float(
        string='Rendimiento (%)',
        help='Porcentaje de rendimiento (OEE)',
        compute='_compute_oee_metrics',
        store=True
    )
    
    oee_quality = fields.Float(
        string='Calidad (%)',
        help='Porcentaje de calidad (OEE)',
        compute='_compute_oee_metrics',
        store=True
    )
    
    oee_overall = fields.Float(
        string='OEE General (%)',
        help='Overall Equipment Effectiveness',
        compute='_compute_oee_metrics',
        store=True
    )
    
    # Operadores Asignados
    operator_ids = fields.Many2many(
        'hr.employee',
        'workcenter_operator_rel',
        'workcenter_id',
        'employee_id',
        string='Operadores Certificados',
        help='Empleados certificados para operar esta máquina'
    )
    
    main_operator_id = fields.Many2one(
        'hr.employee',
        string='Operador Principal',
        help='Operador principal responsable de la máquina'
    )
    
    # Equipos de Mantenimiento Asociados
    maintenance_equipment_ids = fields.One2many(
        'maintenance.equipment',
        'workcenter_id',
        string='Equipos de Mantenimiento'
    )
    
    @api.depends('power_consumption_kw')
    def _compute_energy_cost_per_hour(self):
        """Calcular costo energético por hora basado en tarifa eléctrica Ecuador"""
        # Tarifa industrial Ecuador aproximada: $0.08 USD/kWh
        TARIFF_PER_KWH = 0.08
        for record in self:
            record.energy_cost_per_hour = record.power_consumption_kw * TARIFF_PER_KWH
    
    @api.depends('theoretical_capacity', 'time_efficiency')
    def _compute_real_capacity(self):
        """Calcular capacidad real basada en eficiencia"""
        for record in self:
            if record.theoretical_capacity and record.time_efficiency:
                record.real_capacity = record.theoretical_capacity * (record.time_efficiency / 100.0)
            else:
                record.real_capacity = 0.0
    
    @api.depends('machine_status', 'total_operation_hours', 'maintenance_hours_interval')
    def _compute_oee_metrics(self):
        """Calcular métricas OEE básicas"""
        for record in self:
            # Valores por defecto basados en estado de máquina
            if record.machine_status == 'operational':
                record.oee_availability = 95.0
                record.oee_performance = record.time_efficiency or 85.0
                record.oee_quality = 98.0
            elif record.machine_status == 'maintenance':
                record.oee_availability = 0.0
                record.oee_performance = 0.0
                record.oee_quality = 100.0
            elif record.machine_status == 'breakdown':
                record.oee_availability = 0.0
                record.oee_performance = 0.0
                record.oee_quality = 0.0
            elif record.machine_status == 'setup':
                record.oee_availability = 50.0
                record.oee_performance = 30.0
                record.oee_quality = 95.0
            else:  # standby
                record.oee_availability = 80.0
                record.oee_performance = 0.0
                record.oee_quality = 100.0
            
            # Calcular OEE general
            record.oee_overall = (
                record.oee_availability * 
                record.oee_performance * 
                record.oee_quality
            ) / 10000.0  # Dividir por 10000 porque son porcentajes
    
    def action_start_maintenance(self):
        """Cambiar estado a mantenimiento"""
        self.machine_status = 'maintenance'
        return True
    
    def action_complete_maintenance(self):
        """Completar mantenimiento y actualizar fechas"""
        self.machine_status = 'operational'
        self.last_maintenance_date = fields.Datetime.now()
        # Calcular próximo mantenimiento basado en horas
        if self.maintenance_hours_interval:
            # Asumiendo 8 horas diarias de operación
            days_to_next = self.maintenance_hours_interval / 8
            self.next_maintenance_date = fields.Datetime.now() + fields.Datetime.delta(days=days_to_next)
        return True
    
    def action_report_breakdown(self):
        """Reportar avería y crear solicitud de mantenimiento correctivo"""
        self.machine_status = 'breakdown'
        
        # Crear solicitud de mantenimiento correctivo automática
        maintenance_request = self.env['maintenance.request'].create({
            'name': f'Mantenimiento Correctivo - {self.name}',
            'equipment_id': self.maintenance_equipment_ids[0].id if self.maintenance_equipment_ids else False,
            'maintenance_type': 'corrective',
            'priority': '3',  # Urgente
            'description': f'Falla reportada automáticamente en {self.name}',
            'request_date': fields.Datetime.now(),
        })
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Solicitud de Mantenimiento Correctivo',
            'res_model': 'maintenance.request',
            'res_id': maintenance_request.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def get_machine_efficiency_data(self, date_from, date_to):
        """Obtener datos de eficiencia para dashboard"""
        # Esta función proporcionará datos para el dashboard
        # Se puede implementar con consultas a production orders, downtime records, etc.
        return {
            'availability': self.oee_availability,
            'performance': self.oee_performance,
            'quality': self.oee_quality,
            'oee': self.oee_overall,
            'energy_cost': self.energy_cost_per_hour,
            'maintenance_due': self.next_maintenance_date,
        }