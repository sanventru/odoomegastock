# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, timedelta

class ProductionSchedule(models.Model):
    _name = 'megastock.production.schedule'
    _description = 'Cronograma de Producción MEGASTOCK'
    _order = 'start_datetime, sequence'
    
    name = fields.Char(
        string='Nombre',
        compute='_compute_name',
        store=True
    )
    
    # === INFORMACIÓN BÁSICA ===
    production_id = fields.Many2one(
        'mrp.production',
        string='Orden de Producción',
        required=True,
        help='Orden de producción programada'
    )
    
    workcenter_id = fields.Many2one(
        'mrp.workcenter',
        string='Centro de Trabajo',
        required=True,
        help='Centro de trabajo asignado'
    )
    
    sequence = fields.Integer(
        string='Secuencia',
        default=1,
        help='Orden de ejecución'
    )
    
    state = fields.Selection([
        ('scheduled', 'Programado'),
        ('confirmed', 'Confirmado'),
        ('in_progress', 'En Progreso'),
        ('completed', 'Completado'),
        ('cancelled', 'Cancelado')
    ], string='Estado', default='scheduled', required=True)
    
    # === PROGRAMACIÓN TEMPORAL ===
    start_datetime = fields.Datetime(
        string='Inicio Programado',
        required=True,
        help='Fecha y hora de inicio programada'
    )
    
    end_datetime = fields.Datetime(
        string='Fin Programado',
        required=True,
        help='Fecha y hora de fin programada'
    )
    
    duration_hours = fields.Float(
        string='Duración (horas)',
        compute='_compute_duration',
        store=True,
        help='Duración programada en horas'
    )
    
    # === TIEMPOS REALES ===
    actual_start_datetime = fields.Datetime(
        string='Inicio Real',
        help='Fecha y hora de inicio real'
    )
    
    actual_end_datetime = fields.Datetime(
        string='Fin Real',
        help='Fecha y hora de fin real'
    )
    
    actual_duration_hours = fields.Float(
        string='Duración Real (horas)',
        compute='_compute_actual_duration',
        store=True,
        help='Duración real en horas'
    )
    
    # === ANÁLISIS DE PERFORMANCE ===
    schedule_variance_hours = fields.Float(
        string='Variación Cronograma (h)',
        compute='_compute_schedule_variance',
        store=True,
        help='Diferencia entre tiempo programado y real'
    )
    
    schedule_compliance = fields.Float(
        string='Cumplimiento Cronograma (%)',
        compute='_compute_schedule_compliance',
        store=True,
        help='Porcentaje de cumplimiento del cronograma'
    )
    
    delay_hours = fields.Float(
        string='Retraso (horas)',
        compute='_compute_delay',
        store=True,
        help='Horas de retraso respecto a lo programado'
    )
    
    # === CONFIGURACIÓN DE RECURSOS ===
    resource_allocation = fields.Text(
        string='Asignación de Recursos',
        help='Recursos asignados para esta programación'
    )
    
    operator_ids = fields.Many2many(
        'hr.employee',
        'schedule_operator_rel',
        'schedule_id',
        'employee_id',
        string='Operadores Asignados',
        help='Operadores asignados a esta programación'
    )
    
    equipment_ids = fields.Many2many(
        'maintenance.equipment',
        'schedule_equipment_rel',
        'schedule_id',
        'equipment_id',
        string='Equipos Asignados',
        help='Equipos necesarios para esta programación'
    )
    
    # === RESTRICCIONES Y DEPENDENCIAS ===
    predecessor_ids = fields.Many2many(
        'megastock.production.schedule',
        'schedule_dependency_rel',
        'successor_id',
        'predecessor_id',
        string='Predecesores',
        help='Programaciones que deben completarse antes'
    )
    
    successor_ids = fields.Many2many(
        'megastock.production.schedule',
        'schedule_dependency_rel',
        'predecessor_id',
        'successor_id',
        string='Sucesores',
        help='Programaciones que dependen de esta'
    )
    
    setup_required = fields.Boolean(
        string='Requiere Setup',
        default=True,
        help='Indica si requiere tiempo de preparación'
    )
    
    setup_time_minutes = fields.Float(
        string='Tiempo Setup (min)',
        default=30.0,
        help='Tiempo de setup en minutos'
    )
    
    # === CARACTERÍSTICAS ESPECÍFICAS ===
    production_line = fields.Selection([
        ('papel_periodico', 'Papel Periódico'),
        ('cajas', 'Cajas & Planchas'),
        ('lamina_micro', 'Lámina Micro Corrugada')
    ], string='Línea de Producción', related='workcenter_id.production_line_type', store=True)
    
    product_id = fields.Many2one(
        'product.product',
        related='production_id.product_id',
        string='Producto',
        store=True
    )
    
    quantity = fields.Float(
        related='production_id.product_qty',
        string='Cantidad',
        store=True
    )
    
    # === CONTROL Y SEGUIMIENTO ===
    capacity_planning_id = fields.Many2one(
        'megastock.capacity.planning',
        string='Planificación de Capacidad',
        help='Planificación de capacidad asociada'
    )
    
    algorithm_used = fields.Char(
        string='Algoritmo Utilizado',
        help='Algoritmo usado para generar esta programación'
    )
    
    optimization_score = fields.Float(
        string='Score de Optimización',
        help='Score de calidad de la programación'
    )
    
    priority = fields.Integer(
        string='Prioridad',
        default=5,
        help='Prioridad de la programación (1-10)'
    )
    
    # === ALERTAS Y NOTIFICACIONES ===
    alerts = fields.Text(
        string='Alertas',
        compute='_compute_alerts',
        help='Alertas generadas automáticamente'
    )
    
    risk_factors = fields.Text(
        string='Factores de Riesgo',
        compute='_compute_risk_factors',
        help='Factores que pueden afectar la programación'
    )
    
    # === NOTAS Y OBSERVACIONES ===
    notes = fields.Text(
        string='Notas',
        help='Observaciones sobre la programación'
    )
    
    change_log = fields.Text(
        string='Log de Cambios',
        help='Registro de cambios en la programación'
    )
    
    # === MÉTODOS COMPUTADOS ===
    
    @api.depends('production_id', 'workcenter_id', 'start_datetime')
    def _compute_name(self):
        """Generar nombre descriptivo"""
        for schedule in self:
            if schedule.production_id and schedule.workcenter_id:
                date_str = schedule.start_datetime.strftime('%d/%m %H:%M') if schedule.start_datetime else ''
                schedule.name = f"{schedule.production_id.name} - {schedule.workcenter_id.name} - {date_str}"
            else:
                schedule.name = 'Nueva Programación'
    
    @api.depends('start_datetime', 'end_datetime')
    def _compute_duration(self):
        """Calcular duración programada"""
        for schedule in self:
            if schedule.start_datetime and schedule.end_datetime:
                delta = schedule.end_datetime - schedule.start_datetime
                schedule.duration_hours = delta.total_seconds() / 3600.0
            else:
                schedule.duration_hours = 0.0
    
    @api.depends('actual_start_datetime', 'actual_end_datetime')
    def _compute_actual_duration(self):
        """Calcular duración real"""
        for schedule in self:
            if schedule.actual_start_datetime and schedule.actual_end_datetime:
                delta = schedule.actual_end_datetime - schedule.actual_start_datetime
                schedule.actual_duration_hours = delta.total_seconds() / 3600.0
            else:
                schedule.actual_duration_hours = 0.0
    
    @api.depends('duration_hours', 'actual_duration_hours')
    def _compute_schedule_variance(self):
        """Calcular variación de cronograma"""
        for schedule in self:
            schedule.schedule_variance_hours = schedule.actual_duration_hours - schedule.duration_hours
    
    @api.depends('duration_hours', 'actual_duration_hours')
    def _compute_schedule_compliance(self):
        """Calcular cumplimiento de cronograma"""
        for schedule in self:
            if schedule.duration_hours > 0 and schedule.actual_duration_hours > 0:
                schedule.schedule_compliance = min(100.0, 
                    (schedule.duration_hours / schedule.actual_duration_hours) * 100)
            else:
                schedule.schedule_compliance = 0.0
    
    @api.depends('end_datetime', 'actual_end_datetime')
    def _compute_delay(self):
        """Calcular retraso"""
        for schedule in self:
            if schedule.end_datetime and schedule.actual_end_datetime:
                if schedule.actual_end_datetime > schedule.end_datetime:
                    delta = schedule.actual_end_datetime - schedule.end_datetime
                    schedule.delay_hours = delta.total_seconds() / 3600.0
                else:
                    schedule.delay_hours = 0.0
            else:
                schedule.delay_hours = 0.0
    
    def _compute_alerts(self):
        """Generar alertas automáticas"""
        for schedule in self:
            alerts = []
            
            # Alerta por retraso
            if schedule.delay_hours > 0:
                alerts.append(f"🔴 RETRASO: {schedule.delay_hours:.1f} horas")
            
            # Alerta por proximidad a inicio
            if schedule.state == 'scheduled' and schedule.start_datetime:
                hours_to_start = (schedule.start_datetime - datetime.now()).total_seconds() / 3600.0
                if 0 < hours_to_start <= 2:
                    alerts.append(f"🟡 PRÓXIMO INICIO: En {hours_to_start:.1f} horas")
                elif hours_to_start <= 0:
                    alerts.append("🔴 INICIO VENCIDO: Debería haber iniciado")
            
            # Alerta por recursos
            if not schedule.operator_ids and schedule.state in ['scheduled', 'confirmed']:
                alerts.append("🟠 RECURSOS: Sin operadores asignados")
            
            # Alerta por dependencias
            unfinished_predecessors = schedule.predecessor_ids.filtered(
                lambda p: p.state not in ['completed', 'cancelled']
            )
            if unfinished_predecessors:
                alerts.append(f"⚠️ DEPENDENCIAS: {len(unfinished_predecessors)} predecesores pendientes")
            
            schedule.alerts = '\n'.join(alerts) if alerts else 'Sin alertas'
    
    def _compute_risk_factors(self):
        """Identificar factores de riesgo"""
        for schedule in self:
            risks = []
            
            # Riesgo por capacidad
            if schedule.workcenter_id:
                # Buscar otras programaciones en el mismo período
                overlapping = self.search([
                    ('workcenter_id', '=', schedule.workcenter_id.id),
                    ('start_datetime', '<', schedule.end_datetime),
                    ('end_datetime', '>', schedule.start_datetime),
                    ('id', '!=', schedule.id),
                    ('state', 'in', ['scheduled', 'confirmed', 'in_progress'])
                ])
                
                if overlapping:
                    risks.append(f"Conflicto de recursos: {len(overlapping)} programaciones superpuestas")
            
            # Riesgo por materiales
            if schedule.production_id:
                missing_materials = schedule.production_id.move_raw_ids.filtered(
                    lambda m: m.product_uom_qty > m.reserved_availability
                )
                if missing_materials:
                    risks.append(f"Materiales insuficientes: {len(missing_materials)} items")
            
            # Riesgo por setup prolongado
            if schedule.setup_time_minutes > 60:
                risks.append(f"Setup prolongado: {schedule.setup_time_minutes} minutos")
            
            # Riesgo por complejidad del producto
            if schedule.product_id and hasattr(schedule.product_id, 'complexity_level'):
                if schedule.product_id.complexity_level == 'high':
                    risks.append("Producto de alta complejidad")
            
            schedule.risk_factors = '\n'.join(risks) if risks else 'Sin factores de riesgo identificados'
    
    # === MÉTODOS DE GESTIÓN ===
    
    def action_confirm_schedule(self):
        """Confirmar programación"""
        self.ensure_one()
        
        if self.state != 'scheduled':
            raise UserError("Solo se pueden confirmar programaciones en estado 'Programado'.")
        
        # Verificar recursos
        if not self.operator_ids:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Recursos Faltantes',
                    'message': 'Debe asignar operadores antes de confirmar.',
                    'type': 'warning'
                }
            }
        
        self.state = 'confirmed'
        self._log_change('Programación confirmada')
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Programación Confirmada',
                'message': f'Programación {self.name} confirmada.',
                'type': 'success'
            }
        }
    
    def action_start_execution(self):
        """Iniciar ejecución de la programación"""
        self.ensure_one()
        
        if self.state not in ['scheduled', 'confirmed']:
            raise UserError("Solo se pueden iniciar programaciones confirmadas.")
        
        # Verificar dependencias
        unfinished_predecessors = self.predecessor_ids.filtered(
            lambda p: p.state != 'completed'
        )
        
        if unfinished_predecessors:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Dependencias Pendientes',
                    'message': f'{len(unfinished_predecessors)} dependencias deben completarse primero.',
                    'type': 'warning'
                }
            }
        
        self.state = 'in_progress'
        self.actual_start_datetime = fields.Datetime.now()
        self._log_change('Ejecución iniciada')
        
        # Iniciar orden de producción si no está iniciada
        if self.production_id.state in ['confirmed', 'planned']:
            self.production_id.action_assign()
            if self.production_id.state == 'assigned':
                self.production_id.button_plan()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Ejecución Iniciada',
                'message': f'Iniciada ejecución de {self.name}.',
                'type': 'success'
            }
        }
    
    def action_complete_execution(self):
        """Completar ejecución de la programación"""
        self.ensure_one()
        
        if self.state != 'in_progress':
            raise UserError("Solo se pueden completar programaciones en progreso.")
        
        self.state = 'completed'
        self.actual_end_datetime = fields.Datetime.now()
        self._log_change('Ejecución completada')
        
        # Iniciar sucesores automáticamente si están listos
        for successor in self.successor_ids:
            if successor.state == 'confirmed':
                # Verificar si todas sus dependencias están completas
                all_complete = all(
                    pred.state == 'completed' 
                    for pred in successor.predecessor_ids
                )
                
                if all_complete:
                    successor.action_start_execution()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Ejecución Completada',
                'message': f'Completada ejecución de {self.name}.',
                'type': 'success'
            }
        }
    
    def action_reschedule(self):
        """Reprogramar esta programación"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reprogramar',
            'res_model': 'megastock.reschedule.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_schedule_id': self.id}
        }
    
    def action_assign_resources(self):
        """Asignar recursos a la programación"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Asignar Recursos',
            'res_model': 'megastock.resource.assignment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_schedule_id': self.id}
        }
    
    def _log_change(self, change_description):
        """Registrar cambio en el log"""
        timestamp = fields.Datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        user_name = self.env.user.name
        
        new_log_entry = f"{timestamp} - {user_name}: {change_description}"
        
        if self.change_log:
            self.change_log = f"{self.change_log}\n{new_log_entry}"
        else:
            self.change_log = new_log_entry
    
    # === MÉTODOS DE ANÁLISIS ===
    
    def get_schedule_performance_metrics(self):
        """Obtener métricas de performance de la programación"""
        self.ensure_one()
        
        return {
            'name': self.name,
            'production_name': self.production_id.name,
            'workcenter_name': self.workcenter_id.name,
            'product_name': self.product_id.name,
            'planned_duration': self.duration_hours,
            'actual_duration': self.actual_duration_hours,
            'schedule_variance': self.schedule_variance_hours,
            'schedule_compliance': self.schedule_compliance,
            'delay_hours': self.delay_hours,
            'state': self.state,
            'setup_time': self.setup_time_minutes,
            'operators_count': len(self.operator_ids),
            'start_time': self.start_datetime,
            'end_time': self.end_datetime,
            'actual_start': self.actual_start_datetime,
            'actual_end': self.actual_end_datetime
        }
    
    @api.model
    def get_gantt_data(self, date_from, date_to, workcenter_ids=None):
        """Obtener datos para gráfico Gantt"""
        domain = [
            ('start_datetime', '>=', date_from),
            ('end_datetime', '<=', date_to),
            ('state', 'in', ['scheduled', 'confirmed', 'in_progress', 'completed'])
        ]
        
        if workcenter_ids:
            domain.append(('workcenter_id', 'in', workcenter_ids))
        
        schedules = self.search(domain)
        
        gantt_data = []
        
        for schedule in schedules:
            gantt_data.append({
                'id': schedule.id,
                'name': schedule.name,
                'production_name': schedule.production_id.name,
                'workcenter_name': schedule.workcenter_id.name,
                'start': schedule.start_datetime.isoformat(),
                'end': schedule.end_datetime.isoformat(),
                'duration': schedule.duration_hours,
                'state': schedule.state,
                'color': self._get_state_color(schedule.state),
                'product_name': schedule.product_id.name,
                'quantity': schedule.quantity,
                'operators': [op.name for op in schedule.operator_ids],
                'alerts_count': len(schedule.alerts.split('\n')) if schedule.alerts != 'Sin alertas' else 0
            })
        
        return gantt_data
    
    def _get_state_color(self, state):
        """Obtener color según estado"""
        colors = {
            'scheduled': '#3498db',    # Azul
            'confirmed': '#f39c12',    # Naranja
            'in_progress': '#2ecc71',  # Verde
            'completed': '#27ae60',    # Verde oscuro
            'cancelled': '#e74c3c'     # Rojo
        }
        return colors.get(state, '#95a5a6')  # Gris por defecto
    
    @api.model
    def auto_update_schedules(self):
        """Actualizar automáticamente programaciones basadas en progreso real"""
        active_schedules = self.search([
            ('state', 'in', ['scheduled', 'confirmed', 'in_progress'])
        ])
        
        updated_count = 0
        
        for schedule in active_schedules:
            try:
                # Verificar si la programación debería haber iniciado
                if (schedule.state in ['scheduled', 'confirmed'] and 
                    schedule.start_datetime < datetime.now()):
                    
                    # Marcar como retrasada o iniciar automáticamente
                    if schedule.production_id.state in ['assigned', 'progress']:
                        schedule.action_start_execution()
                        updated_count += 1
                
                # Verificar si la programación debería haber terminado
                elif (schedule.state == 'in_progress' and 
                      schedule.production_id.state == 'done'):
                    
                    schedule.action_complete_execution()
                    updated_count += 1
                    
            except Exception as e:
                _logger.error(f"Error actualizando programación {schedule.name}: {str(e)}")
        
        if updated_count > 0:
            _logger.info(f"Actualizadas {updated_count} programaciones automáticamente")
        
        return updated_count
    
    def action_view_gantt(self):
        """Ver en vista Gantt"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Cronograma de Producción',
            'res_model': 'megastock.production.schedule',
            'view_mode': 'gantt,tree,form',
            'domain': [('workcenter_id', '=', self.workcenter_id.id)],
            'context': {
                'group_by': 'workcenter_id',
                'gantt_default_group_by': 'workcenter_id'
            }
        }