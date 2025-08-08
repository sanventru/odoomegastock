# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class ProductionKPI(models.Model):
    _name = 'megastock.production.kpi'
    _description = 'KPIs de Producción MEGASTOCK'
    _order = 'measurement_date desc, kpi_category'
    _rec_name = 'display_name'
    
    display_name = fields.Char(
        string='Nombre',
        compute='_compute_display_name',
        store=True
    )
    
    # === INFORMACIÓN BÁSICA ===
    measurement_date = fields.Date(
        string='Fecha de Medición',
        required=True,
        default=fields.Date.today
    )
    
    measurement_period = fields.Selection([
        ('hourly', 'Por Hora'),
        ('shift', 'Por Turno'),
        ('daily', 'Diario'),
        ('weekly', 'Semanal'),
        ('monthly', 'Mensual')
    ], string='Período de Medición', default='daily', required=True)
    
    kpi_category = fields.Selection([
        ('efficiency', 'Eficiencia'),
        ('quality', 'Calidad'), 
        ('capacity', 'Capacidad'),
        ('cost', 'Costos'),
        ('delivery', 'Entregas'),
        ('safety', 'Seguridad'),
        ('maintenance', 'Mantenimiento'),
        ('overall', 'Global')
    ], string='Categoría KPI', required=True)
    
    # === SEGMENTACIÓN ===
    workcenter_id = fields.Many2one(
        'mrp.workcenter',
        string='Centro de Trabajo',
        help='Centro de trabajo específico (opcional)'
    )
    
    production_line = fields.Selection([
        ('papel_periodico', 'Papel Periódico'),
        ('cajas', 'Cajas & Planchas'),
        ('lamina_micro', 'Lámina Micro Corrugada'),
        ('all', 'Todas las Líneas')
    ], string='Línea de Producción', default='all')
    
    product_category_id = fields.Many2one(
        'product.category',
        string='Categoría de Producto',
        help='Categoría específica de producto (opcional)'
    )
    
    shift = fields.Selection([
        ('morning', 'Mañana'),
        ('afternoon', 'Tarde'),
        ('night', 'Noche'),
        ('all', 'Todos')
    ], string='Turno', default='all')
    
    # === KPIs DE EFICIENCIA ===
    oee_percentage = fields.Float(
        string='OEE (%)',
        help='Overall Equipment Effectiveness'
    )
    
    availability_percentage = fields.Float(
        string='Disponibilidad (%)',
        help='Porcentaje de tiempo disponible vs planificado'
    )
    
    performance_percentage = fields.Float(
        string='Performance (%)',
        help='Velocidad real vs velocidad ideal'
    )
    
    quality_percentage = fields.Float(
        string='Calidad (%)',
        help='Productos buenos vs productos totales'
    )
    
    planned_efficiency = fields.Float(
        string='Eficiencia Planificada (%)',
        help='Eficiencia objetivo'
    )
    
    actual_efficiency = fields.Float(
        string='Eficiencia Real (%)',
        help='Eficiencia real alcanzada'
    )
    
    efficiency_variance = fields.Float(
        string='Variación Eficiencia (%)',
        compute='_compute_efficiency_variance',
        store=True
    )
    
    # === KPIs DE PRODUCCIÓN ===
    planned_quantity = fields.Float(
        string='Cantidad Planificada',
        help='Cantidad planificada a producir'
    )
    
    produced_quantity = fields.Float(
        string='Cantidad Producida',
        help='Cantidad realmente producida'
    )
    
    good_quantity = fields.Float(
        string='Cantidad Buena',
        help='Cantidad producida sin defectos'
    )
    
    defective_quantity = fields.Float(
        string='Cantidad Defectuosa',
        help='Cantidad con defectos'
    )
    
    scrap_quantity = fields.Float(
        string='Cantidad Desechada',
        help='Cantidad enviada a desecho'
    )
    
    completion_rate = fields.Float(
        string='% Completado',
        compute='_compute_completion_rate',
        store=True
    )
    
    defect_rate = fields.Float(
        string='Tasa Defectos (%)',
        compute='_compute_defect_rate',
        store=True
    )
    
    scrap_rate = fields.Float(
        string='Tasa Desecho (%)',
        compute='_compute_scrap_rate',
        store=True
    )
    
    # === KPIs DE TIEMPO ===
    planned_time_hours = fields.Float(
        string='Tiempo Planificado (h)',
        help='Horas planificadas de producción'
    )
    
    productive_time_hours = fields.Float(
        string='Tiempo Productivo (h)',
        help='Horas realmente productivas'
    )
    
    downtime_hours = fields.Float(
        string='Tiempo Parado (h)',
        help='Horas de parada no planificada'
    )
    
    setup_time_hours = fields.Float(
        string='Tiempo Setup (h)',
        help='Horas de setup/cambio'
    )
    
    maintenance_time_hours = fields.Float(
        string='Tiempo Mantenimiento (h)',
        help='Horas de mantenimiento planificado'
    )
    
    utilization_rate = fields.Float(
        string='Tasa Utilización (%)',
        compute='_compute_utilization_rate',
        store=True
    )
    
    # === KPIs DE COSTOS ===
    planned_cost = fields.Float(
        string='Costo Planificado',
        help='Costo planificado total'
    )
    
    actual_cost = fields.Float(
        string='Costo Real',
        help='Costo real incurrido'
    )
    
    material_cost = fields.Float(
        string='Costo Materiales',
        help='Costo de materiales consumidos'
    )
    
    labor_cost = fields.Float(
        string='Costo Mano de Obra',
        help='Costo de mano de obra'
    )
    
    overhead_cost = fields.Float(
        string='Costos Indirectos',
        help='Costos indirectos asignados'
    )
    
    cost_variance = fields.Float(
        string='Variación Costo',
        compute='_compute_cost_variance',
        store=True
    )
    
    cost_variance_percentage = fields.Float(
        string='Variación Costo (%)',
        compute='_compute_cost_variance',
        store=True
    )
    
    cost_per_unit = fields.Float(
        string='Costo por Unidad',
        compute='_compute_cost_per_unit',
        store=True
    )
    
    # === KPIs DE ENTREGAS ===
    on_time_deliveries = fields.Integer(
        string='Entregas a Tiempo',
        help='Número de entregas realizadas a tiempo'
    )
    
    late_deliveries = fields.Integer(
        string='Entregas Tardías',
        help='Número de entregas tardías'
    )
    
    total_deliveries = fields.Integer(
        string='Total Entregas',
        compute='_compute_total_deliveries',
        store=True
    )
    
    on_time_delivery_rate = fields.Float(
        string='% Entregas a Tiempo',
        compute='_compute_delivery_rate',
        store=True
    )
    
    average_delay_days = fields.Float(
        string='Retraso Promedio (días)',
        help='Días promedio de retraso en entregas'
    )
    
    # === ALERTAS Y ESTADOS ===
    alert_level = fields.Selection([
        ('green', 'Verde - Normal'),
        ('yellow', 'Amarillo - Advertencia'),
        ('red', 'Rojo - Crítico')
    ], string='Nivel de Alerta', compute='_compute_alert_level', store=True)
    
    performance_trend = fields.Selection([
        ('improving', 'Mejorando'),
        ('stable', 'Estable'),
        ('declining', 'Declinando')
    ], string='Tendencia', compute='_compute_trend')
    
    target_met = fields.Boolean(
        string='Meta Alcanzada',
        compute='_compute_target_achievement',
        store=True
    )
    
    # === METAS Y OBJETIVOS ===
    target_oee = fields.Float(
        string='Meta OEE (%)',
        default=85.0,
        help='Meta de OEE'
    )
    
    target_efficiency = fields.Float(
        string='Meta Eficiencia (%)',
        default=90.0,
        help='Meta de eficiencia'
    )
    
    target_quality = fields.Float(
        string='Meta Calidad (%)',
        default=98.0,
        help='Meta de calidad'
    )
    
    target_delivery_rate = fields.Float(
        string='Meta Entregas (%)',
        default=95.0,
        help='Meta de entregas a tiempo'
    )
    
    # === OBSERVACIONES ===
    notes = fields.Text(
        string='Observaciones',
        help='Notas adicionales sobre las mediciones'
    )
    
    root_cause_analysis = fields.Text(
        string='Análisis Causa Raíz',
        help='Análisis de causas de desviaciones'
    )
    
    improvement_actions = fields.Text(
        string='Acciones de Mejora',
        help='Acciones planificadas para mejorar KPIs'
    )
    
    # === MÉTODOS COMPUTADOS ===
    
    @api.depends('kpi_category', 'measurement_date', 'workcenter_id', 'production_line')
    def _compute_display_name(self):
        """Computar nombre para mostrar"""
        for kpi in self:
            parts = []
            parts.append(dict(self._fields['kpi_category'].selection)[kpi.kpi_category])
            
            if kpi.workcenter_id:
                parts.append(kpi.workcenter_id.name)
            elif kpi.production_line != 'all':
                parts.append(dict(self._fields['production_line'].selection)[kpi.production_line])
            
            if kpi.measurement_date:
                parts.append(kpi.measurement_date.strftime('%d/%m/%Y'))
            
            kpi.display_name = ' - '.join(parts)
    
    @api.depends('planned_efficiency', 'actual_efficiency')
    def _compute_efficiency_variance(self):
        """Calcular variación de eficiencia"""
        for kpi in self:
            kpi.efficiency_variance = kpi.actual_efficiency - kpi.planned_efficiency
    
    @api.depends('planned_quantity', 'produced_quantity')
    def _compute_completion_rate(self):
        """Calcular tasa de completado"""
        for kpi in self:
            if kpi.planned_quantity > 0:
                kpi.completion_rate = (kpi.produced_quantity / kpi.planned_quantity) * 100
            else:
                kpi.completion_rate = 0.0
    
    @api.depends('produced_quantity', 'defective_quantity')
    def _compute_defect_rate(self):
        """Calcular tasa de defectos"""
        for kpi in self:
            if kpi.produced_quantity > 0:
                kpi.defect_rate = (kpi.defective_quantity / kpi.produced_quantity) * 100
            else:
                kpi.defect_rate = 0.0
    
    @api.depends('produced_quantity', 'scrap_quantity')
    def _compute_scrap_rate(self):
        """Calcular tasa de desecho"""
        for kpi in self:
            if kpi.produced_quantity > 0:
                kpi.scrap_rate = (kpi.scrap_quantity / kpi.produced_quantity) * 100
            else:
                kpi.scrap_rate = 0.0
    
    @api.depends('planned_time_hours', 'productive_time_hours')
    def _compute_utilization_rate(self):
        """Calcular tasa de utilización"""
        for kpi in self:
            if kpi.planned_time_hours > 0:
                kpi.utilization_rate = (kpi.productive_time_hours / kpi.planned_time_hours) * 100
            else:
                kpi.utilization_rate = 0.0
    
    @api.depends('planned_cost', 'actual_cost')
    def _compute_cost_variance(self):
        """Calcular variación de costos"""
        for kpi in self:
            kpi.cost_variance = kpi.actual_cost - kpi.planned_cost
            
            if kpi.planned_cost > 0:
                kpi.cost_variance_percentage = (kpi.cost_variance / kpi.planned_cost) * 100
            else:
                kpi.cost_variance_percentage = 0.0
    
    @api.depends('actual_cost', 'produced_quantity')
    def _compute_cost_per_unit(self):
        """Calcular costo por unidad"""
        for kpi in self:
            if kpi.produced_quantity > 0:
                kpi.cost_per_unit = kpi.actual_cost / kpi.produced_quantity
            else:
                kpi.cost_per_unit = 0.0
    
    @api.depends('on_time_deliveries', 'late_deliveries')
    def _compute_total_deliveries(self):
        """Calcular total de entregas"""
        for kpi in self:
            kpi.total_deliveries = kpi.on_time_deliveries + kpi.late_deliveries
    
    @api.depends('on_time_deliveries', 'total_deliveries')
    def _compute_delivery_rate(self):
        """Calcular tasa de entregas a tiempo"""
        for kpi in self:
            if kpi.total_deliveries > 0:
                kpi.on_time_delivery_rate = (kpi.on_time_deliveries / kpi.total_deliveries) * 100
            else:
                kpi.on_time_delivery_rate = 0.0
    
    def _compute_alert_level(self):
        """Determinar nivel de alerta basado en KPIs"""
        for kpi in self:
            critical_issues = 0
            warning_issues = 0
            
            # Verificar OEE
            if kpi.oee_percentage < 60:
                critical_issues += 1
            elif kpi.oee_percentage < 75:
                warning_issues += 1
            
            # Verificar calidad
            if kpi.quality_percentage < 95:
                critical_issues += 1
            elif kpi.quality_percentage < 98:
                warning_issues += 1
            
            # Verificar entregas
            if kpi.on_time_delivery_rate < 90:
                critical_issues += 1
            elif kpi.on_time_delivery_rate < 95:
                warning_issues += 1
            
            # Verificar eficiencia
            if kpi.actual_efficiency < 80:
                critical_issues += 1
            elif kpi.actual_efficiency < 90:
                warning_issues += 1
            
            # Determinar nivel de alerta
            if critical_issues > 0:
                kpi.alert_level = 'red'
            elif warning_issues > 0:
                kpi.alert_level = 'yellow'
            else:
                kpi.alert_level = 'green'
    
    def _compute_trend(self):
        """Calcular tendencia comparando con período anterior"""
        for kpi in self:
            # Buscar KPI del período anterior
            previous_date = kpi.measurement_date - timedelta(days=1)
            if kpi.measurement_period == 'weekly':
                previous_date = kpi.measurement_date - timedelta(days=7)
            elif kpi.measurement_period == 'monthly':
                previous_date = kpi.measurement_date - timedelta(days=30)
            
            previous_kpi = self.search([
                ('measurement_date', '=', previous_date),
                ('kpi_category', '=', kpi.kpi_category),
                ('workcenter_id', '=', kpi.workcenter_id.id),
                ('production_line', '=', kpi.production_line)
            ], limit=1)
            
            if previous_kpi:
                # Comparar KPI principal según categoría
                current_value = 0
                previous_value = 0
                
                if kpi.kpi_category == 'efficiency':
                    current_value = kpi.oee_percentage
                    previous_value = previous_kpi.oee_percentage
                elif kpi.kpi_category == 'quality':
                    current_value = kpi.quality_percentage
                    previous_value = previous_kpi.quality_percentage
                elif kpi.kpi_category == 'delivery':
                    current_value = kpi.on_time_delivery_rate
                    previous_value = previous_kpi.on_time_delivery_rate
                elif kpi.kpi_category == 'cost':
                    current_value = -kpi.cost_variance_percentage  # Negativo porque menos variación es mejor
                    previous_value = -previous_kpi.cost_variance_percentage
                
                if current_value > previous_value + 2:
                    kpi.performance_trend = 'improving'
                elif current_value < previous_value - 2:
                    kpi.performance_trend = 'declining'
                else:
                    kpi.performance_trend = 'stable'
            else:
                kpi.performance_trend = 'stable'
    
    def _compute_target_achievement(self):
        """Verificar si se alcanzaron las metas"""
        for kpi in self:
            targets_met = 0
            total_targets = 0
            
            # Verificar OEE
            if kpi.target_oee > 0:
                total_targets += 1
                if kpi.oee_percentage >= kpi.target_oee:
                    targets_met += 1
            
            # Verificar eficiencia
            if kpi.target_efficiency > 0:
                total_targets += 1
                if kpi.actual_efficiency >= kpi.target_efficiency:
                    targets_met += 1
            
            # Verificar calidad
            if kpi.target_quality > 0:
                total_targets += 1
                if kpi.quality_percentage >= kpi.target_quality:
                    targets_met += 1
            
            # Verificar entregas
            if kpi.target_delivery_rate > 0:
                total_targets += 1
                if kpi.on_time_delivery_rate >= kpi.target_delivery_rate:
                    targets_met += 1
            
            # Meta alcanzada si se cumplen al menos el 75% de los objetivos
            kpi.target_met = (targets_met / total_targets >= 0.75) if total_targets > 0 else False
    
    # === MÉTODOS DE ANÁLISIS ===
    
    @api.model
    def calculate_oee(self, availability, performance, quality):
        """Calcular OEE (Overall Equipment Effectiveness)"""
        return (availability / 100.0) * (performance / 100.0) * (quality / 100.0) * 100.0
    
    def calculate_kpis_from_productions(self, productions):
        """Calcular KPIs desde órdenes de producción"""
        self.ensure_one()
        
        if not productions:
            return
        
        total_planned_qty = sum(productions.mapped('product_qty'))
        total_produced_qty = sum(productions.mapped('qty_produced'))
        total_planned_time = sum(productions.mapped('planned_duration_hours'))
        total_actual_time = sum(productions.mapped('actual_duration_hours'))
        total_planned_cost = sum(productions.mapped('total_planned_cost'))
        total_actual_cost = sum(productions.mapped('total_actual_cost'))
        
        # Calcular calidad (simplificado)
        quality_checks = self.env['quality.check'].search([
            ('production_id', 'in', productions.ids)
        ])
        
        passed_checks = quality_checks.filtered(lambda c: c.quality_state == 'pass')
        quality_rate = (len(passed_checks) / len(quality_checks) * 100) if quality_checks else 100.0
        
        # Actualizar KPIs
        self.write({
            'planned_quantity': total_planned_qty,
            'produced_quantity': total_produced_qty,
            'good_quantity': total_produced_qty * (quality_rate / 100.0),
            'planned_time_hours': total_planned_time,
            'productive_time_hours': total_actual_time,
            'planned_cost': total_planned_cost,
            'actual_cost': total_actual_cost,
            'quality_percentage': quality_rate,
            'availability_percentage': 90.0,  # Simplificado
            'performance_percentage': (total_planned_time / total_actual_time * 100) if total_actual_time > 0 else 0,
        })
        
        # Calcular OEE
        self.oee_percentage = self.calculate_oee(
            self.availability_percentage,
            self.performance_percentage,
            self.quality_percentage
        )
    
    def generate_improvement_suggestions(self):
        """Generar sugerencias de mejora basadas en KPIs"""
        self.ensure_one()
        
        suggestions = []
        
        # Sugerencias por OEE bajo
        if self.oee_percentage < 75:
            if self.availability_percentage < 85:
                suggestions.append("• Reducir tiempos de parada no planificada")
                suggestions.append("• Mejorar programa de mantenimiento preventivo")
            
            if self.performance_percentage < 85:
                suggestions.append("• Optimizar velocidades de operación")
                suggestions.append("• Reducir tiempos de setup y cambio")
            
            if self.quality_percentage < 95:
                suggestions.append("• Implementar controles de calidad en línea")
                suggestions.append("• Capacitar operadores en procedimientos")
        
        # Sugerencias por costos altos
        if self.cost_variance_percentage > 10:
            suggestions.append("• Revisar consumo de materiales")
            suggestions.append("• Analizar eficiencia energética")
            suggestions.append("• Evaluar optimización de procesos")
        
        # Sugerencias por entregas tardías
        if self.on_time_delivery_rate < 95:
            suggestions.append("• Mejorar planificación de producción")
            suggestions.append("• Implementar buffer de seguridad")
            suggestions.append("• Optimizar gestión de inventarios")
        
        return suggestions
    
    def action_create_improvement_plan(self):
        """Crear plan de mejora basado en KPIs"""
        suggestions = self.generate_improvement_suggestions()
        
        if suggestions:
            self.improvement_actions = '\n'.join(suggestions)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Plan de Mejora Generado',
                'message': f'Se generaron {len(suggestions)} sugerencias de mejora.',
                'type': 'success'
            }
        }
    
    @api.model
    def auto_calculate_daily_kpis(self):
        """Calcular KPIs diarios automáticamente"""
        yesterday = fields.Date.today() - timedelta(days=1)
        
        # Obtener producciones completadas ayer
        completed_productions = self.env['mrp.production'].search([
            ('state', '=', 'done'),
            ('date_finished', '>=', yesterday),
            ('date_finished', '<', fields.Date.today())
        ])
        
        if not completed_productions:
            return
        
        # Agrupar por centro de trabajo
        workcenters = completed_productions.mapped('workorder_ids.workcenter_id')
        
        for workcenter in workcenters:
            workcenter_productions = completed_productions.filtered(
                lambda p: workcenter in p.workorder_ids.mapped('workcenter_id')
            )
            
            # Crear KPI para eficiencia
            efficiency_kpi = self.create({
                'measurement_date': yesterday,
                'measurement_period': 'daily',
                'kpi_category': 'efficiency',
                'workcenter_id': workcenter.id,
                'production_line': workcenter.production_line_type or 'all'
            })
            
            efficiency_kpi.calculate_kpis_from_productions(workcenter_productions)
            
            # Crear KPI para calidad
            quality_kpi = self.create({
                'measurement_date': yesterday,
                'measurement_period': 'daily',
                'kpi_category': 'quality',
                'workcenter_id': workcenter.id,
                'production_line': workcenter.production_line_type or 'all'
            })
            
            quality_kpi.calculate_kpis_from_productions(workcenter_productions)
            
            _logger.info(f"KPIs diarios calculados para {workcenter.name}")
    
    def get_kpi_dashboard_data(self):
        """Obtener datos para dashboard de KPIs"""
        self.ensure_one()
        
        return {
            'name': self.display_name,
            'measurement_date': self.measurement_date,
            'category': self.kpi_category,
            'workcenter': self.workcenter_id.name if self.workcenter_id else 'Todas',
            'production_line': dict(self._fields['production_line'].selection)[self.production_line],
            'oee': self.oee_percentage,
            'availability': self.availability_percentage,
            'performance': self.performance_percentage,
            'quality': self.quality_percentage,
            'efficiency': self.actual_efficiency,
            'completion_rate': self.completion_rate,
            'on_time_delivery_rate': self.on_time_delivery_rate,
            'cost_variance_pct': self.cost_variance_percentage,
            'alert_level': self.alert_level,
            'trend': self.performance_trend,
            'target_met': self.target_met,
            'utilization_rate': self.utilization_rate
        }