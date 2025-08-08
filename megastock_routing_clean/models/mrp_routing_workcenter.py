# -*- coding: utf-8 -*-

from odoo import models, fields, api

class MrpRoutingWorkcenter(models.Model):
    _inherit = 'mrp.routing.workcenter'
    
    # Configuración de calidad específica por operación
    quality_control_required = fields.Boolean(
        string='Control de Calidad Requerido',
        default=False,
        help='Indica si esta operación requiere control de calidad'
    )
    
    quality_sample_size = fields.Integer(
        string='Tamaño de Muestra QC',
        default=1,
        help='Número de piezas a inspeccionar por lote'
    )
    
    # Tiempos detallados
    setup_time = fields.Float(
        string='Tiempo Setup (min)',
        help='Tiempo específico de setup para esta operación',
        related='time_mode_batch',
        readonly=False
    )
    
    teardown_time = fields.Float(
        string='Tiempo Desmontaje (min)',
        default=0.0,
        help='Tiempo requerido para limpiar/desmontar después de la operación'
    )
    
    # Configuración de lotes
    min_batch_size = fields.Float(
        string='Tamaño Mínimo Lote',
        default=1.0,
        help='Cantidad mínima para procesar eficientemente'
    )
    
    max_batch_size = fields.Float(
        string='Tamaño Máximo Lote',
        default=10000.0,
        help='Cantidad máxima que puede procesar por lote'
    )
    
    optimal_batch_size = fields.Float(
        string='Tamaño Óptimo Lote',
        compute='_compute_optimal_batch_size',
        store=True,
        help='Tamaño óptimo calculado considerando setup y capacidad'
    )
    
    # Análisis de capacidad
    capacity_utilization_target = fields.Float(
        string='Utilización Objetivo (%)',
        default=85.0,
        help='Porcentaje objetivo de utilización de capacidad'
    )
    
    bottleneck_risk = fields.Selection([
        ('low', 'Bajo'),
        ('medium', 'Medio'),
        ('high', 'Alto'),
        ('critical', 'Crítico')
    ], string='Riesgo Cuello Botella', 
       compute='_compute_bottleneck_risk',
       store=True)
    
    # Costos específicos de operación
    material_cost_per_unit = fields.Float(
        string='Costo Material/Unidad',
        default=0.0,
        help='Costo de materiales específicos de esta operación'
    )
    
    tool_cost_per_unit = fields.Float(
        string='Costo Herramientas/Unidad',
        default=0.0,
        help='Costo de herramientas y matrices por unidad'
    )
    
    total_cost_per_unit = fields.Float(
        string='Costo Total/Unidad',
        compute='_compute_total_cost_per_unit',
        store=True,
        help='Costo total por unidad incluyendo todos los factores'
    )
    
    # Configuración de paralelización
    parallel_operations = fields.Integer(
        string='Operaciones en Paralelo',
        default=1,
        help='Número de operaciones que pueden ejecutarse simultáneamente'
    )
    
    can_overlap = fields.Boolean(
        string='Permite Solapamiento',
        default=False,
        help='Permite solapamiento con la siguiente operación'
    )
    
    overlap_percentage = fields.Float(
        string='Porcentaje Solapamiento (%)',
        default=0.0,
        help='Porcentaje de solapamiento permitido con siguiente operación'
    )
    
    # Configuración de alternativas
    alternative_workcenter_ids = fields.Many2many(
        'mrp.workcenter',
        'routing_workcenter_alternative_rel',
        'routing_workcenter_id',
        'alternative_workcenter_id',
        string='Centros de Trabajo Alternativos',
        help='Centros alternativos que pueden ejecutar esta operación'
    )
    
    skill_level_required = fields.Selection([
        ('basic', 'Básico'),
        ('intermediate', 'Intermedio'),
        ('advanced', 'Avanzado'),
        ('expert', 'Experto')
    ], string='Nivel Habilidad Requerido', default='intermediate')
    
    @api.depends('time_mode_batch', 'time_cycle', 'workcenter_id.real_capacity')
    def _compute_optimal_batch_size(self):
        """Calcular tamaño óptimo de lote"""
        for operation in self:
            if operation.time_mode_batch and operation.time_cycle:
                # Algoritmo simplificado: equilibrar tiempo setup vs tiempo ciclo
                setup_minutes = operation.time_mode_batch
                cycle_minutes = operation.time_cycle
                
                if cycle_minutes > 0:
                    # Punto donde el costo de setup representa 10% del tiempo total
                    optimal_size = setup_minutes / (cycle_minutes * 0.1)
                    
                    # Ajustar a límites mín/máx
                    optimal_size = max(operation.min_batch_size, 
                                     min(optimal_size, operation.max_batch_size))
                    
                    operation.optimal_batch_size = round(optimal_size)
                else:
                    operation.optimal_batch_size = operation.min_batch_size
            else:
                operation.optimal_batch_size = operation.min_batch_size
    
    @api.depends('workcenter_id.real_capacity', 'workcenter_id.oee_overall', 'time_cycle')
    def _compute_bottleneck_risk(self):
        """Evaluar riesgo de cuello de botella"""
        for operation in self:
            risk = 'low'
            
            # Factores de riesgo
            if operation.workcenter_id:
                # Factor 1: Baja capacidad relativa
                if operation.workcenter_id.real_capacity < 50:
                    risk = 'medium'
                
                # Factor 2: Baja eficiencia OEE
                if operation.workcenter_id.oee_overall < 70:
                    risk = 'high'
                
                # Factor 3: Tiempo de ciclo alto
                if operation.time_cycle > 5.0:  # Más de 5 minutos por unidad
                    if risk == 'medium':
                        risk = 'high'
                    elif risk == 'high':
                        risk = 'critical'
                
                # Factor 4: Alto tiempo de setup
                if operation.time_mode_batch > 30:  # Más de 30 minutos setup
                    if risk == 'low':
                        risk = 'medium'
                    elif risk == 'medium':
                        risk = 'high'
            
            operation.bottleneck_risk = risk
    
    @api.depends('workcenter_id.costs_hour', 'time_cycle', 'material_cost_per_unit', 'tool_cost_per_unit')
    def _compute_total_cost_per_unit(self):
        """Calcular costo total por unidad"""
        for operation in self:
            # Costo de mano de obra
            labor_cost = 0.0
            if operation.workcenter_id.costs_hour and operation.time_cycle:
                labor_cost = (operation.workcenter_id.costs_hour * operation.time_cycle) / 60.0
            
            # Costo energético
            energy_cost = 0.0
            if hasattr(operation.workcenter_id, 'energy_cost_per_hour') and operation.time_cycle:
                energy_cost = (operation.workcenter_id.energy_cost_per_hour * operation.time_cycle) / 60.0
            
            # Costo total
            operation.total_cost_per_unit = (
                labor_cost + 
                energy_cost + 
                operation.material_cost_per_unit + 
                operation.tool_cost_per_unit
            )
    
    def get_available_capacity(self, date_from, date_to):
        """Obtener capacidad disponible en período específico"""
        if not self.workcenter_id:
            return 0.0
        
        # Horas disponibles en el período
        period_hours = (date_to - date_from).total_seconds() / 3600.0
        
        # Capacidad teórica ajustada por eficiencia
        theoretical_capacity = self.workcenter_id.real_capacity * period_hours
        
        # Descontar capacidad ya comprometida
        # (Esto requeriría consulta a workorders existentes)
        committed_capacity = 0.0  # Simplificado
        
        available_capacity = max(0.0, theoretical_capacity - committed_capacity)
        
        return available_capacity
    
    def calculate_operation_time(self, quantity):
        """Calcular tiempo total para producir una cantidad"""
        if quantity <= 0:
            return 0.0
        
        # Tiempo de setup (una vez por lote)
        setup_time = self.time_mode_batch or 0.0
        
        # Tiempo de procesamiento
        cycle_time = self.time_cycle * quantity
        
        # Tiempo de desmontaje
        teardown_time = self.teardown_time or 0.0
        
        # Ajustar por eficiencia del centro de trabajo
        total_time = setup_time + cycle_time + teardown_time
        
        if self.workcenter_id.time_efficiency:
            total_time = total_time / (self.workcenter_id.time_efficiency / 100.0)
        
        return total_time
    
    def suggest_alternative_workcenter(self, required_date, quantity):
        """Sugerir centro de trabajo alternativo si el principal no está disponible"""
        if not self.alternative_workcenter_ids:
            return None
        
        operation_time_hours = self.calculate_operation_time(quantity) / 60.0
        
        best_alternative = None
        earliest_available = None
        
        for alt_workcenter in self.alternative_workcenter_ids:
            # Verificar disponibilidad
            available_capacity = alt_workcenter.real_capacity * operation_time_hours
            
            if available_capacity >= quantity:
                # Verificar calendario de trabajo
                # (simplificado - en implementación real verificar calendar)
                available_from = required_date
                
                if not earliest_available or available_from < earliest_available:
                    earliest_available = available_from
                    best_alternative = alt_workcenter
        
        return {
            'workcenter': best_alternative,
            'available_from': earliest_available,
            'estimated_duration': operation_time_hours
        } if best_alternative else None
    
    def optimize_for_quantity(self, target_quantity):
        """Optimizar configuración para una cantidad específica"""
        # Determinar número óptimo de lotes
        optimal_lots = max(1, int(target_quantity / self.optimal_batch_size))
        actual_lot_size = target_quantity / optimal_lots
        
        # Calcular tiempos y costos
        total_setup_time = (self.time_mode_batch or 0) * optimal_lots
        total_cycle_time = self.time_cycle * target_quantity
        total_teardown_time = (self.teardown_time or 0) * optimal_lots
        
        total_time_minutes = total_setup_time + total_cycle_time + total_teardown_time
        total_cost = self.total_cost_per_unit * target_quantity
        
        return {
            'operation_name': self.name,
            'workcenter_name': self.workcenter_id.name,
            'target_quantity': target_quantity,
            'optimal_lots': optimal_lots,
            'lot_size': actual_lot_size,
            'total_time_minutes': total_time_minutes,
            'total_time_hours': total_time_minutes / 60.0,
            'total_cost': total_cost,
            'cost_per_unit': self.total_cost_per_unit,
            'bottleneck_risk': self.bottleneck_risk,
            'quality_control_points': self.quality_sample_size if self.quality_control_required else 0
        }
    
    def action_analyze_operation_efficiency(self):
        """Analizar eficiencia de la operación"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'Análisis Eficiencia - {self.name}',
            'res_model': 'megastock.operation.analysis.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_operation_id': self.id,
            }
        }
    
    @api.model
    def identify_bottlenecks(self, routing_ids=None):
        """Identificar operaciones que son cuellos de botella"""
        domain = [('bottleneck_risk', 'in', ['high', 'critical'])]
        
        if routing_ids:
            domain.append(('routing_id', 'in', routing_ids))
        
        bottleneck_operations = self.search(domain, order='bottleneck_risk desc, time_cycle desc')
        
        bottlenecks = []
        for operation in bottleneck_operations:
            bottlenecks.append({
                'operation_id': operation.id,
                'operation_name': operation.name,
                'routing_name': operation.routing_id.name,
                'workcenter_name': operation.workcenter_id.name,
                'bottleneck_risk': operation.bottleneck_risk,
                'time_cycle': operation.time_cycle,
                'capacity': operation.workcenter_id.real_capacity,
                'oee': operation.workcenter_id.oee_overall,
                'cost_per_unit': operation.total_cost_per_unit,
                'suggestions': operation._get_improvement_suggestions()
            })
        
        return bottlenecks
    
    def _get_improvement_suggestions(self):
        """Obtener sugerencias de mejora para la operación"""
        suggestions = []
        
        # Sugerencias basadas en riesgo de cuello de botella
        if self.bottleneck_risk in ['high', 'critical']:
            if self.time_mode_batch > 20:
                suggestions.append("Reducir tiempo de setup con mejores herramientas o SMED")
            
            if self.workcenter_id.oee_overall < 80:
                suggestions.append("Implementar mejoras TPM para aumentar OEE")
            
            if not self.alternative_workcenter_ids:
                suggestions.append("Considerar centros de trabajo alternativos")
            
            if self.parallel_operations == 1:
                suggestions.append("Evaluar paralelización de operaciones")
        
        # Sugerencias basadas en costos
        if self.total_cost_per_unit > 1.0:  # Umbral configurable
            suggestions.append("Analizar oportunidades de reducción de costos")
        
        return suggestions