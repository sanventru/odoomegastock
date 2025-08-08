# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, timedelta

class MrpProductionExtended(models.Model):
    _inherit = 'mrp.production'
    
    # === CAMPOS DE PLANIFICACIÓN AVANZADA ===
    production_plan_id = fields.Many2one(
        'megastock.production.plan',
        string='Plan de Producción',
        help='Plan de producción que generó esta orden'
    )
    
    work_queue_id = fields.Many2one(
        'megastock.work.queue',
        string='Cola de Trabajo',
        help='Cola de trabajo asignada para esta producción'
    )
    
    queue_position = fields.Integer(
        string='Posición en Cola',
        compute='_compute_queue_position',
        help='Posición actual en la cola de trabajo'
    )
    
    # === PROGRAMACIÓN INTELIGENTE ===
    scheduling_algorithm_id = fields.Many2one(
        'megastock.scheduling.algorithm',
        string='Algoritmo de Programación',
        help='Algoritmo usado para programar esta producción'
    )
    
    optimized_sequence = fields.Integer(
        string='Secuencia Optimizada',
        help='Secuencia calculada por algoritmo de optimización'
    )
    
    auto_scheduled = fields.Boolean(
        string='Programado Automáticamente',
        default=False,
        help='Indica si fue programado automáticamente'
    )
    
    suggested_start_date = fields.Datetime(
        string='Inicio Sugerido',
        help='Fecha de inicio sugerida por el sistema de planificación'
    )
    
    # === ANÁLISIS DE CAPACIDAD ===
    capacity_utilization = fields.Float(
        string='Utilización de Capacidad (%)',
        compute='_compute_capacity_metrics',
        help='Porcentaje de utilización de capacidad planificada'
    )
    
    bottleneck_operation_id = fields.Many2one(
        'mrp.routing.workcenter',
        string='Operación Cuello de Botella',
        compute='_compute_bottleneck_operation',
        help='Operación que representa el cuello de botella'
    )
    
    estimated_completion_date = fields.Datetime(
        string='Finalización Estimada',
        compute='_compute_estimated_completion',
        help='Fecha estimada de finalización basada en capacidad'
    )
    
    # === KPIs Y MÉTRICAS ===
    planned_oee = fields.Float(
        string='OEE Planificado (%)',
        default=85.0,
        help='OEE objetivo para esta producción'
    )
    
    actual_oee = fields.Float(
        string='OEE Real (%)',
        compute='_compute_actual_oee',
        help='OEE real alcanzado'
    )
    
    efficiency_variance = fields.Float(
        string='Variación Eficiencia (%)',
        compute='_compute_efficiency_variance',
        help='Diferencia entre eficiencia planificada y real'
    )
    
    # === ALERTAS Y CONTROL ===
    production_alerts = fields.Text(
        string='Alertas de Producción',
        compute='_compute_production_alerts',
        help='Alertas generadas automáticamente'
    )
    
    risk_level = fields.Selection([
        ('low', 'Bajo'),
        ('medium', 'Medio'),
        ('high', 'Alto'),
        ('critical', 'Crítico')
    ], string='Nivel de Riesgo', compute='_compute_risk_level')
    
    delay_probability = fields.Float(
        string='Probabilidad de Retraso (%)',
        compute='_compute_delay_probability',
        help='Probabilidad calculada de retraso'
    )
    
    # === PLANIFICACIÓN DINÁMICA ===
    allow_rescheduling = fields.Boolean(
        string='Permitir Reprogramación',
        default=True,
        help='Permite reprogramación automática'
    )
    
    priority_score = fields.Float(
        string='Score de Prioridad',
        compute='_compute_priority_score',
        help='Score calculado para priorización'
    )
    
    # === INTEGRACIÓN CON BOM INTELIGENTES ===
    uses_intelligent_bom = fields.Boolean(
        string='Usa BOM Inteligente',
        compute='_compute_bom_intelligence',
        help='Indica si usa BOM con cálculos inteligentes'
    )
    
    bom_cost_variance = fields.Float(
        string='Variación Costo BOM (%)',
        compute='_compute_bom_cost_variance',
        help='Variación en costo del BOM vs estándar'
    )
    
    # === CARACTERÍSTICAS ESPECÍFICAS CORRUGADO ===
    corrugated_line_type = fields.Selection([
        ('papel_periodico', 'Papel Periódico'),
        ('cajas', 'Cajas & Planchas'),
        ('lamina_micro', 'Lámina Micro Corrugada')
    ], string='Tipo de Línea', compute='_compute_corrugated_line_type')
    
    setup_time_estimated = fields.Float(
        string='Setup Estimado (min)',
        compute='_compute_setup_time',
        help='Tiempo de setup estimado'
    )
    
    material_waste_estimated = fields.Float(
        string='Merma Estimada (%)',
        compute='_compute_waste_estimate',
        help='Porcentaje de merma estimado'
    )
    
    # === MÉTODOS COMPUTADOS ===
    
    @api.depends('work_queue_id')
    def _compute_queue_position(self):
        """Calcular posición en cola"""
        for production in self:
            if production.work_queue_id:
                queue_item = production.work_queue_id.queue_item_ids.filtered(
                    lambda i: i.production_id == production
                )
                production.queue_position = queue_item.sequence if queue_item else 0
            else:
                production.queue_position = 0
    
    def _compute_capacity_metrics(self):
        """Calcular métricas de capacidad"""
        for production in self:
            if production.routing_id:
                # Calcular utilización basada en tiempo planificado vs disponible
                total_time = sum(
                    (op.time_cycle * production.product_qty) / 60.0
                    for op in production.routing_id.operation_ids
                )
                
                # Simplificado - en implementación real vendría de análisis de capacidad
                production.capacity_utilization = min(100.0, total_time / 8.0 * 100)
            else:
                production.capacity_utilization = 0.0
    
    @api.depends('routing_id')
    def _compute_bottleneck_operation(self):
        """Identificar operación cuello de botella"""
        for production in self:
            if production.routing_id:
                # Encontrar operación con mayor tiempo por unidad
                max_time = 0
                bottleneck = None
                
                for operation in production.routing_id.operation_ids:
                    time_per_unit = operation.time_cycle
                    if time_per_unit > max_time:
                        max_time = time_per_unit
                        bottleneck = operation
                
                production.bottleneck_operation_id = bottleneck
            else:
                production.bottleneck_operation_id = False
    
    def _compute_estimated_completion(self):
        """Calcular fecha estimada de finalización"""
        for production in self:
            if production.date_planned_start and production.routing_id:
                total_minutes = sum(
                    (op.time_cycle * production.product_qty) + (op.time_mode_batch or 0)
                    for op in production.routing_id.operation_ids
                )
                
                production.estimated_completion_date = production.date_planned_start + \
                    timedelta(minutes=total_minutes)
            else:
                production.estimated_completion_date = production.date_planned_finished
    
    def _compute_actual_oee(self):
        """Calcular OEE real"""
        for production in self:
            if production.workorder_ids and production.state == 'done':
                # Calcular componentes del OEE
                availability = production._calculate_availability()
                performance = production._calculate_performance()
                quality = production._calculate_quality()
                
                production.actual_oee = (availability * performance * quality) / 10000.0
            else:
                production.actual_oee = 0.0
    
    def _calculate_availability(self):
        """Calcular disponibilidad para OEE"""
        total_planned = sum(self.workorder_ids.mapped('duration_expected'))
        total_actual = sum(self.workorder_ids.mapped('duration'))
        
        if total_actual > 0:
            return min(100.0, (total_planned / total_actual) * 100)
        return 0.0
    
    def _calculate_performance(self):
        """Calcular performance para OEE"""
        if self.routing_id:
            theoretical_time = sum(
                op.time_cycle * self.product_qty
                for op in self.routing_id.operation_ids
            )
            actual_time = sum(self.workorder_ids.mapped('duration'))
            
            if actual_time > 0:
                return min(100.0, (theoretical_time / actual_time) * 100)
        return 0.0
    
    def _calculate_quality(self):
        """Calcular calidad para OEE"""
        quality_checks = self.env['quality.check'].search([
            ('production_id', '=', self.id)
        ])
        
        if quality_checks:
            passed = quality_checks.filtered(lambda c: c.quality_state == 'pass')
            return (len(passed) / len(quality_checks)) * 100
        
        return 100.0  # Si no hay controles, asumir 100%
    
    @api.depends('planned_efficiency', 'actual_efficiency')
    def _compute_efficiency_variance(self):
        """Calcular variación de eficiencia"""
        for production in self:
            production.efficiency_variance = production.actual_efficiency - production.planned_efficiency
    
    def _compute_production_alerts(self):
        """Generar alertas de producción"""
        for production in self:
            alerts = []
            
            # Alerta por retraso
            if production.date_planned_finished and datetime.now() > production.date_planned_finished:
                days_late = (datetime.now() - production.date_planned_finished).days
                alerts.append(f"🔴 RETRASO: {days_late} días de retraso")
            
            # Alerta por materiales
            missing_materials = production.move_raw_ids.filtered(
                lambda m: m.product_uom_qty > m.reserved_availability
            )
            if missing_materials:
                alerts.append(f"🟡 MATERIALES: {len(missing_materials)} materiales insuficientes")
            
            # Alerta por capacidad
            if production.capacity_utilization > 95:
                alerts.append("🟠 CAPACIDAD: Utilización crítica (>95%)")
            
            # Alerta por calidad
            if production.actual_oee < 70 and production.state == 'done':
                alerts.append(f"🔴 CALIDAD: OEE bajo ({production.actual_oee:.1f}%)")
            
            production.production_alerts = '\n'.join(alerts) if alerts else 'Sin alertas'
    
    @api.depends('date_planned_finished', 'capacity_utilization', 'move_raw_ids.reserved_availability')
    def _compute_risk_level(self):
        """Calcular nivel de riesgo"""
        for production in self:
            risk_factors = 0
            
            # Factor: Proximidad a fecha límite
            if production.date_planned_finished:
                days_remaining = (production.date_planned_finished - datetime.now()).days
                if days_remaining < 1:
                    risk_factors += 3
                elif days_remaining < 3:
                    risk_factors += 2
                elif days_remaining < 7:
                    risk_factors += 1
            
            # Factor: Disponibilidad de materiales
            if production.move_raw_ids:
                materials_available = production.move_raw_ids.filtered(
                    lambda m: m.product_uom_qty <= m.reserved_availability
                )
                availability_rate = len(materials_available) / len(production.move_raw_ids)
                if availability_rate < 0.8:
                    risk_factors += 2
                elif availability_rate < 0.9:
                    risk_factors += 1
            
            # Factor: Utilización de capacidad
            if production.capacity_utilization > 95:
                risk_factors += 2
            elif production.capacity_utilization > 85:
                risk_factors += 1
            
            # Determinar nivel de riesgo
            if risk_factors >= 5:
                production.risk_level = 'critical'
            elif risk_factors >= 3:
                production.risk_level = 'high'
            elif risk_factors >= 1:
                production.risk_level = 'medium'
            else:
                production.risk_level = 'low'
    
    def _compute_delay_probability(self):
        """Calcular probabilidad de retraso usando modelo simplificado"""
        for production in self:
            probability = 0.0
            
            # Basado en nivel de riesgo
            risk_multipliers = {
                'low': 0.1,
                'medium': 0.3,
                'high': 0.6,
                'critical': 0.9
            }
            probability += risk_multipliers.get(production.risk_level, 0.1) * 50
            
            # Basado en disponibilidad de materiales
            if production.move_raw_ids:
                missing_materials = production.move_raw_ids.filtered(
                    lambda m: m.product_uom_qty > m.reserved_availability
                )
                if missing_materials:
                    probability += (len(missing_materials) / len(production.move_raw_ids)) * 30
            
            # Basado en capacidad
            if production.capacity_utilization > 90:
                probability += (production.capacity_utilization - 90) * 2
            
            production.delay_probability = min(100.0, probability)
    
    def _compute_priority_score(self):
        """Calcular score de prioridad dinámico"""
        for production in self:
            score = 5.0  # Base score
            
            # Incrementar por urgencia
            if production.date_planned_finished:
                days_remaining = (production.date_planned_finished - datetime.now()).days
                if days_remaining <= 1:
                    score += 5
                elif days_remaining <= 3:
                    score += 3
                elif days_remaining <= 7:
                    score += 1
            
            # Incrementar por cantidad
            if production.product_qty > 1000:
                score += 2
            
            # Incrementar por cliente VIP (si existe el campo)
            if hasattr(production, 'partner_id') and production.partner_id:
                if production.partner_id.is_company:
                    score += 1
            
            # Incrementar por riesgo
            risk_scores = {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}
            score += risk_scores.get(production.risk_level, 0)
            
            production.priority_score = min(10.0, score)
    
    @api.depends('bom_id')
    def _compute_bom_intelligence(self):
        """Verificar si usa BOM inteligente"""
        for production in self:
            if production.bom_id:
                production.uses_intelligent_bom = getattr(production.bom_id, 'is_intelligent', False)
            else:
                production.uses_intelligent_bom = False
    
    def _compute_bom_cost_variance(self):
        """Calcular variación de costo del BOM"""
        for production in self:
            if production.bom_id and hasattr(production.bom_id, 'cost_variance_percentage'):
                production.bom_cost_variance = production.bom_id.cost_variance_percentage
            else:
                production.bom_cost_variance = 0.0
    
    def _compute_corrugated_line_type(self):
        """Determinar tipo de línea de corrugado"""
        for production in self:
            if production.routing_id and production.routing_id.operation_ids:
                # Buscar el tipo basado en el primer centro de trabajo
                first_workcenter = production.routing_id.operation_ids[0].workcenter_id
                production.corrugated_line_type = getattr(first_workcenter, 'production_line_type', 'cajas')
            else:
                production.corrugated_line_type = 'cajas'  # Default
    
    def _compute_setup_time(self):
        """Calcular tiempo de setup estimado"""
        for production in self:
            total_setup = 0.0
            
            if production.routing_id:
                for operation in production.routing_id.operation_ids:
                    # Setup basado en cambio de producto
                    if hasattr(operation, 'time_mode_batch'):
                        total_setup += operation.time_mode_batch or 0
            
            # Agregar setup adicional por tipo de línea
            line_setup_times = {
                'papel_periodico': 45,  # 45 min cambio bobina
                'cajas': 30,           # 30 min cambio molde
                'lamina_micro': 60     # 60 min calibración
            }
            
            total_setup += line_setup_times.get(production.corrugated_line_type, 30)
            production.setup_time_estimated = total_setup
    
    def _compute_waste_estimate(self):
        """Calcular estimación de merma"""
        for production in self:
            # Merma basada en tipo de línea y cantidad
            base_waste = {
                'papel_periodico': 2.0,  # 2% base
                'cajas': 3.5,           # 3.5% base
                'lamina_micro': 5.0     # 5% base por precisión
            }
            
            waste = base_waste.get(production.corrugated_line_type, 3.0)
            
            # Ajustar por cantidad (lotes pequeños tienen más merma)
            if production.product_qty < 100:
                waste += 2.0
            elif production.product_qty < 500:
                waste += 1.0
            
            production.material_waste_estimated = waste
    
    # === MÉTODOS DE ACCIÓN ===
    
    def action_smart_schedule(self):
        """Programar inteligentemente usando algoritmo óptimo"""
        self.ensure_one()
        
        # Seleccionar algoritmo basado en características
        if self.corrugated_line_type == 'papel_periodico':
            # Para papel periódico, minimizar setup
            algorithm = self.env['megastock.scheduling.algorithm'].search([
                ('algorithm_type', '=', 'custom'),
                ('applicable_lines', 'in', ['papel_periodico', 'all'])
            ], limit=1)
        else:
            # Para otros, usar SPT por defecto
            algorithm = self.env['megastock.scheduling.algorithm'].search([
                ('algorithm_type', '=', 'spt')
            ], limit=1)
        
        if algorithm:
            result = algorithm.execute_algorithm(self)
            
            if result.get('success'):
                self.scheduling_algorithm_id = algorithm.id
                self.auto_scheduled = True
                
                # Aplicar tiempo sugerido
                if result.get('schedule'):
                    schedule_item = result['schedule'][0]  # Primera (única) en este caso
                    self.suggested_start_date = schedule_item['start_time']
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Programación Inteligente',
                        'message': f'Programado con algoritmo {algorithm.name}',
                        'type': 'success'
                    }
                }
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Error de Programación',
                'message': 'No se encontró algoritmo adecuado',
                'type': 'warning'
            }
        }
    
    def action_add_to_queue(self):
        """Agregar a cola de trabajo apropiada"""
        self.ensure_one()
        
        # Buscar cola apropiada
        queue = self.env['megastock.work.queue'].search([
            ('production_line', '=', self.corrugated_line_type),
            ('state', '=', 'active')
        ], limit=1)
        
        if not queue:
            # Buscar cola general
            queue = self.env['megastock.work.queue'].search([
                ('production_line', '=', 'all'),
                ('state', '=', 'active')
            ], limit=1)
        
        if queue:
            queue.add_production_to_queue(self.id, self.priority_score)
            self.work_queue_id = queue.id
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Agregado a Cola',
                    'message': f'Agregado a cola {queue.name}',
                    'type': 'success'
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Sin Cola Disponible',
                    'message': 'No hay colas activas disponibles',
                    'type': 'warning'
                }
            }
    
    def action_analyze_risks(self):
        """Analizar riesgos de la producción"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Análisis de Riesgos',
            'res_model': 'megastock.production.risk.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_production_id': self.id}
        }
    
    def action_calculate_kpis(self):
        """Calcular KPIs para esta producción"""
        if self.state == 'done':
            # Crear registro de KPI
            kpi = self.env['megastock.production.kpi'].create({
                'measurement_date': fields.Date.today(),
                'kpi_category': 'efficiency',
                'workcenter_id': self.workorder_ids[0].workcenter_id.id if self.workorder_ids else False,
                'production_line': self.corrugated_line_type
            })
            
            kpi.calculate_kpis_from_productions(self)
            
            return {
                'type': 'ir.actions.act_window',
                'name': 'KPIs Calculados',
                'res_model': 'megastock.production.kpi',
                'res_id': kpi.id,
                'view_mode': 'form',
                'target': 'current'
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'KPIs No Disponibles',
                    'message': 'Los KPIs solo están disponibles para producciones completadas',
                    'type': 'warning'
                }
            }
    
    @api.model
    def auto_reschedule_delayed_productions(self):
        """Reprogramar automáticamente producciones retrasadas"""
        delayed_productions = self.search([
            ('state', 'in', ['confirmed', 'planned', 'progress']),
            ('date_planned_finished', '<', datetime.now()),
            ('allow_rescheduling', '=', True)
        ])
        
        rescheduled_count = 0
        
        for production in delayed_productions:
            try:
                # Calcular nueva fecha basada en capacidad disponible
                new_start_date = datetime.now() + timedelta(hours=2)  # Buffer de 2 horas
                
                # Ajustar por tiempo de producción
                if production.routing_id:
                    total_hours = sum(
                        (op.time_cycle * production.product_qty) / 60.0
                        for op in production.routing_id.operation_ids
                    )
                    new_finish_date = new_start_date + timedelta(hours=total_hours)
                else:
                    new_finish_date = new_start_date + timedelta(hours=8)  # Default 8 horas
                
                # Actualizar fechas
                production.write({
                    'date_planned_start': new_start_date,
                    'date_planned_finished': new_finish_date,
                    'auto_scheduled': True
                })
                
                rescheduled_count += 1
                
            except Exception as e:
                _logger.error(f"Error reprogramando producción {production.name}: {str(e)}")
        
        if rescheduled_count > 0:
            _logger.info(f"Reprogramadas {rescheduled_count} producciones retrasadas")
        
        return rescheduled_count