# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, timedelta

class MrpProduction(models.Model):
    _inherit = 'mrp.production'
    
    # Campos de planificación avanzada MEGASTOCK
    planned_efficiency = fields.Float(
        string='Eficiencia Planificada (%)',
        default=85.0,
        help='Eficiencia esperada para esta orden de producción'
    )
    
    actual_efficiency = fields.Float(
        string='Eficiencia Real (%)',
        compute='_compute_actual_efficiency',
        store=True,
        help='Eficiencia real obtenida'
    )
    
    total_planned_cost = fields.Float(
        string='Costo Total Planificado',
        compute='_compute_planned_cost',
        store=True,
        help='Costo total planificado incluyendo materiales y operaciones'
    )
    
    total_actual_cost = fields.Float(
        string='Costo Total Real',
        compute='_compute_actual_cost',
        store=True,
        help='Costo real incurrido en la producción'
    )
    
    cost_variance = fields.Float(
        string='Variación de Costo',
        compute='_compute_cost_variance',
        store=True,
        help='Diferencia entre costo planificado y real'
    )
    
    cost_variance_percent = fields.Float(
        string='Variación de Costo (%)',
        compute='_compute_cost_variance',
        store=True
    )
    
    # Análisis de tiempo
    planned_duration_hours = fields.Float(
        string='Duración Planificada (horas)',
        compute='_compute_planned_duration',
        store=True
    )
    
    actual_duration_hours = fields.Float(
        string='Duración Real (horas)',
        compute='_compute_actual_duration',
        store=True
    )
    
    schedule_variance_hours = fields.Float(
        string='Variación Cronograma (horas)',
        compute='_compute_schedule_variance',
        store=True
    )
    
    # Clasificación de prioridad
    production_priority = fields.Selection([
        ('low', 'Baja'),
        ('normal', 'Normal'),
        ('high', 'Alta'),
        ('urgent', 'Urgente')
    ], string='Prioridad', default='normal')
    
    customer_priority = fields.Boolean(
        string='Prioridad Cliente',
        default=False,
        help='Marcado como prioritario por el cliente'
    )
    
    # Planificación automática
    auto_scheduled = fields.Boolean(
        string='Programación Automática',
        default=False,
        help='Indica si fue programada automáticamente'
    )
    
    optimal_lot_size = fields.Float(
        string='Tamaño Óptimo de Lote',
        help='Tamaño óptimo calculado para esta producción'
    )
    
    suggested_start_date = fields.Datetime(
        string='Fecha Inicio Sugerida',
        help='Fecha de inicio sugerida por el algoritmo de planificación'
    )
    
    capacity_utilization = fields.Float(
        string='Utilización de Capacidad (%)',
        compute='_compute_capacity_utilization',
        store=True,
        help='Porcentaje de utilización de capacidad planificada'
    )
    
    # Seguimiento de calidad
    quality_checks_passed = fields.Integer(
        string='Controles de Calidad Aprobados',
        compute='_compute_quality_metrics',
        store=True
    )
    
    quality_checks_failed = fields.Integer(
        string='Controles de Calidad Fallidos',
        compute='_compute_quality_metrics',
        store=True
    )
    
    quality_pass_rate = fields.Float(
        string='Tasa de Aprobación Calidad (%)',
        compute='_compute_quality_metrics',
        store=True
    )
    
    @api.depends('workorder_ids', 'workorder_ids.duration_expected', 'workorder_ids.state')
    def _compute_actual_efficiency(self):
        """Calcular eficiencia real basada en workorders"""
        for production in self:
            if production.workorder_ids:
                planned_minutes = sum(production.workorder_ids.mapped('duration_expected'))
                actual_minutes = sum(wo.duration for wo in production.workorder_ids if wo.state == 'done')
                
                if actual_minutes > 0:
                    production.actual_efficiency = (planned_minutes / actual_minutes) * 100
                else:
                    production.actual_efficiency = 0.0
            else:
                production.actual_efficiency = 0.0
    
    @api.depends('bom_id', 'product_qty')
    def _compute_planned_cost(self):
        """Calcular costo planificado total"""
        for production in self:
            material_cost = 0.0
            operation_cost = 0.0
            
            # Costo de materiales
            for move in production.move_raw_ids:
                material_cost += move.product_uom_qty * move.product_id.standard_price
            
            # Costo de operaciones
            if production.routing_id:
                for operation in production.routing_id.operation_ids:
                    op_time_hours = (operation.time_cycle * production.product_qty + 
                                   (operation.time_mode_batch or 0)) / 60.0
                    op_cost = op_time_hours * (operation.workcenter_id.costs_hour or 0)
                    operation_cost += op_cost
            
            production.total_planned_cost = material_cost + operation_cost
    
    @api.depends('workorder_ids', 'workorder_ids.costs_hour')
    def _compute_actual_cost(self):
        """Calcular costo real incurrido"""
        for production in self:
            material_cost = 0.0
            operation_cost = 0.0
            
            # Costo real de materiales (cantidades realmente consumidas)
            for move in production.move_raw_ids.filtered(lambda m: m.state == 'done'):
                material_cost += move.quantity_done * move.product_id.standard_price
            
            # Costo real de operaciones
            for workorder in production.workorder_ids.filtered(lambda w: w.state == 'done'):
                op_cost = (workorder.duration / 60.0) * (workorder.workcenter_id.costs_hour or 0)
                operation_cost += op_cost
            
            production.total_actual_cost = material_cost + operation_cost
    
    @api.depends('total_planned_cost', 'total_actual_cost')
    def _compute_cost_variance(self):
        """Calcular variación de costos"""
        for production in self:
            production.cost_variance = production.total_actual_cost - production.total_planned_cost
            
            if production.total_planned_cost > 0:
                production.cost_variance_percent = (production.cost_variance / production.total_planned_cost) * 100
            else:
                production.cost_variance_percent = 0.0
    
    @api.depends('routing_id', 'product_qty')
    def _compute_planned_duration(self):
        """Calcular duración planificada"""
        for production in self:
            if production.routing_id:
                total_minutes = 0.0
                for operation in production.routing_id.operation_ids:
                    op_minutes = operation.time_cycle * production.product_qty + (operation.time_mode_batch or 0)
                    total_minutes += op_minutes
                
                production.planned_duration_hours = total_minutes / 60.0
            else:
                production.planned_duration_hours = 0.0
    
    @api.depends('date_start', 'date_finished')
    def _compute_actual_duration(self):
        """Calcular duración real"""
        for production in self:
            if production.date_start and production.date_finished:
                delta = production.date_finished - production.date_start
                production.actual_duration_hours = delta.total_seconds() / 3600.0
            else:
                production.actual_duration_hours = 0.0
    
    @api.depends('planned_duration_hours', 'actual_duration_hours')
    def _compute_schedule_variance(self):
        """Calcular variación de cronograma"""
        for production in self:
            production.schedule_variance_hours = production.actual_duration_hours - production.planned_duration_hours
    
    @api.depends('routing_id', 'product_qty')
    def _compute_capacity_utilization(self):
        """Calcular utilización de capacidad"""
        for production in self:
            if production.routing_id and production.routing_id.bottleneck_capacity:
                required_capacity = production.product_qty
                available_capacity = production.routing_id.bottleneck_capacity * production.planned_duration_hours
                
                if available_capacity > 0:
                    production.capacity_utilization = (required_capacity / available_capacity) * 100
                else:
                    production.capacity_utilization = 0.0
            else:
                production.capacity_utilization = 0.0
    
    def _compute_quality_metrics(self):
        """Calcular métricas de calidad"""
        for production in self:
            # Buscar controles de calidad relacionados con esta producción
            quality_checks = self.env['quality.check'].search([
                ('production_id', '=', production.id)
            ])
            
            passed_checks = quality_checks.filtered(lambda c: c.quality_state == 'pass')
            failed_checks = quality_checks.filtered(lambda c: c.quality_state == 'fail')
            
            production.quality_checks_passed = len(passed_checks)
            production.quality_checks_failed = len(failed_checks)
            
            total_checks = len(quality_checks)
            if total_checks > 0:
                production.quality_pass_rate = (len(passed_checks) / total_checks) * 100
            else:
                production.quality_pass_rate = 0.0
    
    def action_schedule_optimally(self):
        """Programar producción de manera óptima"""
        if not self.routing_id:
            raise UserError("No se puede programar sin ruta de producción definida.")
        
        # Calcular tamaño óptimo de lote
        if not self.optimal_lot_size:
            self.optimal_lot_size = self.routing_id.calculate_optimal_lot_size(self.product_qty)
        
        # Generar cronograma optimizado
        schedule = self.routing_id.generate_production_schedule(
            self.product_qty, 
            self.date_planned_start
        )
        
        if schedule:
            self.suggested_start_date = schedule['estimated_start_date']
            self.auto_scheduled = True
            
            # Crear/actualizar workorders basado en el cronograma
            self._update_workorders_from_schedule(schedule)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Programación Completada',
                    'message': f'Producción programada optimalmente. Inicio sugerido: {schedule["estimated_start_date"].strftime("%d/%m/%Y %H:%M")}',
                    'type': 'success',
                }
            }
    
    def _update_workorders_from_schedule(self, schedule):
        """Actualizar workorders basado en cronograma optimizado"""
        # Eliminar workorders existentes si los hay
        self.workorder_ids.unlink()
        
        for lot in schedule['lots']:
            for operation_schedule in lot['operations']:
                # Crear workorder para cada operación
                operation = self.env['mrp.routing.workcenter'].browse(operation_schedule['operation_id'])
                
                workorder = self.env['mrp.workorder'].create({
                    'name': f"{self.name} - {operation.name} - Lote {lot['lot_number']}",
                    'production_id': self.id,
                    'product_id': self.product_id.id,
                    'product_uom_id': self.product_uom_id.id,
                    'workcenter_id': operation.workcenter_id.id,
                    'operation_id': operation.id,
                    'qty_production': lot['lot_quantity'],
                    'date_planned_start': operation_schedule['start_date'],
                    'date_planned_finished': operation_schedule['end_date'],
                    'duration_expected': operation_schedule['duration_hours'] * 60,  # Convertir a minutos
                })
    
    def action_analyze_production_performance(self):
        """Analizar performance de la producción"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'Análisis de Performance - {self.name}',
            'res_model': 'megastock.production.analysis.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_production_id': self.id,
            }
        }
    
    @api.model
    def auto_schedule_productions(self, date_from=None, date_to=None):
        """Programar automáticamente producciones pendientes"""
        if not date_from:
            date_from = fields.Datetime.now()
        if not date_to:
            date_to = date_from + timedelta(days=30)
        
        # Buscar producciones no programadas
        productions = self.search([
            ('state', 'in', ['draft', 'confirmed']),
            ('date_planned_start', '>=', date_from),
            ('date_planned_start', '<=', date_to),
            ('routing_id', '!=', False),
            ('auto_scheduled', '=', False)
        ], order='production_priority desc, date_planned_start asc')
        
        scheduled_count = 0
        for production in productions:
            try:
                production.action_schedule_optimally()
                scheduled_count += 1
            except Exception as e:
                # Log error pero continuar con siguientes producciones
                import logging
                _logger = logging.getLogger(__name__)
                _logger.warning(f"Error programando producción {production.name}: {str(e)}")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Programación Automática Completada',
                'message': f'Se programaron automáticamente {scheduled_count} órdenes de producción.',
                'type': 'success',
            }
        }
    
    def get_production_kpis(self):
        """Obtener KPIs de la producción"""
        return {
            'name': self.name,
            'product_name': self.product_id.name,
            'planned_quantity': self.product_qty,
            'produced_quantity': self.qty_produced,
            'completion_rate': (self.qty_produced / self.product_qty * 100) if self.product_qty else 0,
            'planned_efficiency': self.planned_efficiency,
            'actual_efficiency': self.actual_efficiency,
            'efficiency_variance': self.actual_efficiency - self.planned_efficiency,
            'planned_cost': self.total_planned_cost,
            'actual_cost': self.total_actual_cost,
            'cost_variance': self.cost_variance,
            'cost_variance_percent': self.cost_variance_percent,
            'planned_duration': self.planned_duration_hours,
            'actual_duration': self.actual_duration_hours,
            'schedule_variance': self.schedule_variance_hours,
            'quality_pass_rate': self.quality_pass_rate,
            'capacity_utilization': self.capacity_utilization,
            'priority': self.production_priority,
            'state': self.state,
        }