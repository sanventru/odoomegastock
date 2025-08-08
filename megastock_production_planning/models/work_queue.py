# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class WorkQueue(models.Model):
    _name = 'megastock.work.queue'
    _description = 'Cola de Trabajo MEGASTOCK'
    _order = 'priority desc, sequence, scheduled_start_time'
    
    name = fields.Char(
        string='Nombre de la Cola',
        required=True,
        help='Nombre identificativo de la cola de trabajo'
    )
    
    workcenter_id = fields.Many2one(
        'mrp.workcenter',
        string='Centro de Trabajo',
        required=True,
        help='Centro de trabajo asociado a esta cola'
    )
    
    production_line = fields.Selection([
        ('papel_periodico', 'Papel Periódico'),
        ('cajas', 'Cajas & Planchas'),
        ('lamina_micro', 'Lámina Micro Corrugada'),
        ('all', 'Todas las Líneas')
    ], string='Línea de Producción', related='workcenter_id.production_line_type', store=True)
    
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('active', 'Activa'),
        ('paused', 'Pausada'),
        ('completed', 'Completada')
    ], string='Estado', default='draft', required=True)
    
    # === CONFIGURACIÓN DE LA COLA ===
    queue_type = fields.Selection([
        ('fifo', 'FIFO - Primero en Entrar, Primero en Salir'),
        ('lifo', 'LIFO - Último en Entrar, Primero en Salir'),
        ('spt', 'SPT - Tiempo de Procesamiento Más Corto'),
        ('edd', 'EDD - Fecha de Entrega Más Próxima'),
        ('priority', 'Por Prioridad'),
        ('custom', 'Secuenciación Personalizada')
    ], string='Tipo de Cola', default='priority', required=True)
    
    auto_sequence = fields.Boolean(
        string='Secuenciación Automática',
        default=True,
        help='Reordenar automáticamente al agregar nuevos trabajos'
    )
    
    max_queue_size = fields.Integer(
        string='Tamaño Máximo Cola',
        default=50,
        help='Número máximo de trabajos en cola (0 = ilimitado)'
    )
    
    buffer_time_minutes = fields.Float(
        string='Tiempo Buffer (min)',
        default=30.0,
        help='Tiempo de buffer entre trabajos'
    )
    
    # === LÍNEAS DE LA COLA ===
    queue_item_ids = fields.One2many(
        'megastock.work.queue.item',
        'work_queue_id',
        string='Items en Cola'
    )
    
    # === ESTADÍSTICAS ===
    total_items = fields.Integer(
        string='Total Items',
        compute='_compute_statistics',
        store=True
    )
    
    waiting_items = fields.Integer(
        string='Items Esperando',
        compute='_compute_statistics',
        store=True
    )
    
    in_progress_items = fields.Integer(
        string='Items en Progreso',
        compute='_compute_statistics',
        store=True
    )
    
    completed_items = fields.Integer(
        string='Items Completados',
        compute='_compute_statistics',
        store=True
    )
    
    average_waiting_time = fields.Float(
        string='Tiempo Promedio Espera (min)',
        compute='_compute_performance_metrics',
        help='Tiempo promedio de espera en cola'
    )
    
    throughput_per_hour = fields.Float(
        string='Throughput por Hora',
        compute='_compute_performance_metrics',
        help='Número de trabajos completados por hora'
    )
    
    current_workload_hours = fields.Float(
        string='Carga Actual (horas)',
        compute='_compute_workload',
        help='Horas totales de trabajo pendiente'
    )
    
    estimated_completion_time = fields.Datetime(
        string='Tiempo Estimado Finalización',
        compute='_compute_completion_time',
        help='Tiempo estimado para completar toda la cola'
    )
    
    # === CONFIGURACIÓN DE PRIORIDADES ===
    priority_rules = fields.Text(
        string='Reglas de Prioridad',
        help='Reglas para calcular prioridad automáticamente'
    )
    
    # === MÉTODOS COMPUTADOS ===
    
    @api.depends('queue_item_ids.state')
    def _compute_statistics(self):
        """Calcular estadísticas de la cola"""
        for queue in self:
            items = queue.queue_item_ids
            queue.total_items = len(items)
            queue.waiting_items = len(items.filtered(lambda i: i.state == 'waiting'))
            queue.in_progress_items = len(items.filtered(lambda i: i.state == 'in_progress'))
            queue.completed_items = len(items.filtered(lambda i: i.state == 'completed'))
    
    def _compute_performance_metrics(self):
        """Calcular métricas de performance"""
        for queue in self:
            completed_items = queue.queue_item_ids.filtered(lambda i: i.state == 'completed')
            
            if completed_items:
                # Tiempo promedio de espera
                waiting_times = completed_items.mapped('actual_waiting_time')
                queue.average_waiting_time = sum(waiting_times) / len(waiting_times) if waiting_times else 0.0
                
                # Throughput por hora (últimas 24 horas)
                twenty_four_hours_ago = datetime.now() - timedelta(hours=24)
                recent_completed = completed_items.filtered(
                    lambda i: i.completion_time and i.completion_time >= twenty_four_hours_ago
                )
                queue.throughput_per_hour = len(recent_completed) / 24.0
            else:
                queue.average_waiting_time = 0.0
                queue.throughput_per_hour = 0.0
    
    @api.depends('queue_item_ids.estimated_duration')
    def _compute_workload(self):
        """Calcular carga de trabajo actual"""
        for queue in self:
            pending_items = queue.queue_item_ids.filtered(
                lambda i: i.state in ['waiting', 'in_progress']
            )
            queue.current_workload_hours = sum(pending_items.mapped('estimated_duration'))
    
    @api.depends('current_workload_hours', 'workcenter_id.capacity_per_hour')
    def _compute_completion_time(self):
        """Calcular tiempo estimado de finalización"""
        for queue in self:
            if queue.current_workload_hours > 0 and queue.workcenter_id.capacity_per_hour:
                hours_to_complete = queue.current_workload_hours / (queue.workcenter_id.capacity_per_hour or 1)
                queue.estimated_completion_time = datetime.now() + timedelta(hours=hours_to_complete)
            else:
                queue.estimated_completion_time = datetime.now()
    
    # === MÉTODOS DE GESTIÓN DE COLA ===
    
    def action_activate(self):
        """Activar la cola de trabajo"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError("Solo se pueden activar colas en estado borrador.")
        
        self.state = 'active'
        self._sequence_queue()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Cola Activada',
                'message': f'Cola {self.name} activada con {self.total_items} items.',
                'type': 'success'
            }
        }
    
    def action_pause(self):
        """Pausar procesamiento de la cola"""
        self.ensure_one()
        self.state = 'paused'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Cola Pausada',
                'message': f'Cola {self.name} pausada.',
                'type': 'info'
            }
        }
    
    def action_resume(self):
        """Reanudar procesamiento de la cola"""
        self.ensure_one()
        if self.state == 'paused':
            self.state = 'active'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Cola Reanudada',
                'message': f'Cola {self.name} reanudada.',
                'type': 'success'
            }
        }
    
    def add_production_to_queue(self, production_id, priority=5):
        """Agregar orden de producción a la cola"""
        self.ensure_one()
        
        production = self.env['mrp.production'].browse(production_id)
        
        # Verificar si ya está en cola
        existing_item = self.queue_item_ids.filtered(
            lambda i: i.production_id.id == production_id
        )
        
        if existing_item:
            raise UserError(f"La producción {production.name} ya está en la cola.")
        
        # Crear item de cola
        queue_item = self.env['megastock.work.queue.item'].create({
            'work_queue_id': self.id,
            'production_id': production_id,
            'priority': priority,
            'estimated_duration': self._estimate_production_duration(production),
            'state': 'waiting'
        })
        
        # Reordenar cola si está configurado
        if self.auto_sequence:
            self._sequence_queue()
        
        return queue_item
    
    def _estimate_production_duration(self, production):
        """Estimar duración de una producción"""
        if production.routing_id:
            total_minutes = 0.0
            for operation in production.routing_id.operation_ids:
                op_minutes = (operation.time_cycle * production.product_qty) + (operation.time_mode_batch or 0)
                total_minutes += op_minutes
            return total_minutes / 60.0  # Convertir a horas
        else:
            # Estimación por defecto
            return production.product_qty * 0.1  # 0.1 horas por unidad
    
    def _sequence_queue(self):
        """Reordenar cola según el tipo configurado"""
        self.ensure_one()
        
        items = self.queue_item_ids.filtered(lambda i: i.state == 'waiting')
        
        if self.queue_type == 'fifo':
            items = items.sorted('entry_time')
        elif self.queue_type == 'lifo':
            items = items.sorted('entry_time', reverse=True)
        elif self.queue_type == 'spt':
            items = items.sorted('estimated_duration')
        elif self.queue_type == 'edd':
            items = items.sorted(lambda i: i.production_id.date_planned_finished or datetime.max)
        elif self.queue_type == 'priority':
            items = items.sorted(key=lambda i: (i.priority, i.entry_time), reverse=True)
        elif self.queue_type == 'custom':
            items = self._custom_sequence_logic(items)
        
        # Asignar nuevos números de secuencia
        for index, item in enumerate(items):
            item.sequence = index + 1
            item.scheduled_start_time = self._calculate_scheduled_start_time(index, items)
    
    def _custom_sequence_logic(self, items):
        """Lógica personalizada de secuenciación"""
        # Implementar algoritmo personalizado
        # Por ejemplo: minimizar setup times, balancear tipos de producto, etc.
        
        # Agrupar por tipo de producto para minimizar setups
        grouped_items = {}
        for item in items:
            product_type = item.production_id.product_id.categ_id.name
            if product_type not in grouped_items:
                grouped_items[product_type] = []
            grouped_items[product_type].append(item)
        
        # Ordenar cada grupo por prioridad
        sequenced_items = []
        for product_type, type_items in grouped_items.items():
            type_items = sorted(type_items, key=lambda i: i.priority, reverse=True)
            sequenced_items.extend(type_items)
        
        return sequenced_items
    
    def _calculate_scheduled_start_time(self, index, items):
        """Calcular tiempo programado de inicio"""
        base_time = datetime.now()
        
        # Sumar duración de items anteriores
        for i in range(index):
            if i < len(items):
                duration_hours = items[i].estimated_duration
                buffer_hours = self.buffer_time_minutes / 60.0
                base_time += timedelta(hours=duration_hours + buffer_hours)
        
        return base_time
    
    def get_next_item(self):
        """Obtener siguiente item para procesar"""
        self.ensure_one()
        
        if self.state != 'active':
            return None
        
        next_item = self.queue_item_ids.filtered(
            lambda i: i.state == 'waiting'
        ).sorted('sequence')[:1]
        
        return next_item
    
    def start_next_item(self):
        """Iniciar procesamiento del siguiente item"""
        self.ensure_one()
        
        next_item = self.get_next_item()
        
        if next_item:
            next_item.action_start_processing()
            return next_item
        else:
            return None
    
    def action_resequence(self):
        """Reordenar manualmente la cola"""
        self.ensure_one()
        self._sequence_queue()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Cola Reordenada',
                'message': f'Cola {self.name} reordenada según criterio {self.queue_type}.',
                'type': 'success'
            }
        }
    
    def action_optimize_sequence(self):
        """Optimizar secuencia usando algoritmos avanzados"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Optimización de Secuencia',
            'res_model': 'megastock.queue.optimizer.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_work_queue_id': self.id}
        }
    
    def get_queue_performance_report(self):
        """Generar reporte de performance de la cola"""
        self.ensure_one()
        
        return {
            'queue_name': self.name,
            'workcenter': self.workcenter_id.name,
            'total_items': self.total_items,
            'waiting_items': self.waiting_items,
            'in_progress_items': self.in_progress_items,
            'completed_items': self.completed_items,
            'average_waiting_time': self.average_waiting_time,
            'throughput_per_hour': self.throughput_per_hour,
            'current_workload_hours': self.current_workload_hours,
            'estimated_completion': self.estimated_completion_time,
            'utilization_percentage': (self.completed_items / self.total_items * 100) if self.total_items else 0
        }
    
    @api.model
    def auto_populate_queues(self):
        """Popular colas automáticamente con producciones pendientes"""
        active_queues = self.search([('state', '=', 'active')])
        
        for queue in active_queues:
            # Buscar producciones confirmadas sin cola asignada
            productions = self.env['mrp.production'].search([
                ('state', 'in', ['confirmed', 'planned', 'progress']),
                ('work_queue_id', '=', False),
                ('routing_id.operation_ids.workcenter_id', '=', queue.workcenter_id.id)
            ])
            
            for production in productions:
                try:
                    # Calcular prioridad automática
                    priority = self._calculate_auto_priority(production)
                    queue.add_production_to_queue(production.id, priority)
                except Exception as e:
                    _logger.warning(f"Error agregando producción {production.name} a cola {queue.name}: {str(e)}")
    
    def _calculate_auto_priority(self, production):
        """Calcular prioridad automática para una producción"""
        priority = 5  # Prioridad base
        
        # Incrementar por urgencia de fecha
        if production.date_planned_finished:
            days_until_due = (production.date_planned_finished.date() - datetime.now().date()).days
            if days_until_due <= 1:
                priority += 5  # Muy urgente
            elif days_until_due <= 3:
                priority += 3  # Urgente
            elif days_until_due <= 7:
                priority += 1  # Próximo
        
        # Incrementar por prioridad del cliente
        if hasattr(production, 'sale_order_id') and production.sale_order_id:
            if production.sale_order_id.partner_id.is_company:
                priority += 2  # Cliente corporativo
        
        # Incrementar por cantidad (lotes grandes)
        if production.product_qty > 1000:
            priority += 1
        
        return min(priority, 10)  # Máximo prioridad 10


class WorkQueueItem(models.Model):
    _name = 'megastock.work.queue.item'
    _description = 'Item de Cola de Trabajo'
    _order = 'sequence, priority desc'
    
    work_queue_id = fields.Many2one(
        'megastock.work.queue',
        string='Cola de Trabajo',
        required=True,
        ondelete='cascade'
    )
    
    production_id = fields.Many2one(
        'mrp.production',
        string='Orden de Producción',
        required=True,
        help='Orden de producción en cola'
    )
    
    sequence = fields.Integer(
        string='Secuencia',
        default=1,
        help='Orden en la cola (1 = siguiente)'
    )
    
    priority = fields.Integer(
        string='Prioridad',
        default=5,
        help='Prioridad del item (1-10, mayor = más prioritario)'
    )
    
    state = fields.Selection([
        ('waiting', 'Esperando'),
        ('in_progress', 'En Progreso'),
        ('completed', 'Completado'),
        ('cancelled', 'Cancelado')
    ], string='Estado', default='waiting', required=True)
    
    # === TIEMPOS ===
    entry_time = fields.Datetime(
        string='Hora de Entrada',
        default=fields.Datetime.now,
        help='Momento en que entró a la cola'
    )
    
    scheduled_start_time = fields.Datetime(
        string='Inicio Programado',
        help='Hora programada para iniciar procesamiento'
    )
    
    actual_start_time = fields.Datetime(
        string='Inicio Real',
        help='Hora real de inicio de procesamiento'
    )
    
    estimated_duration = fields.Float(
        string='Duración Estimada (h)',
        help='Tiempo estimado de procesamiento'
    )
    
    actual_duration = fields.Float(
        string='Duración Real (h)',
        compute='_compute_actual_duration',
        store=True,
        help='Tiempo real de procesamiento'
    )
    
    completion_time = fields.Datetime(
        string='Hora de Finalización',
        help='Momento de finalización del procesamiento'
    )
    
    actual_waiting_time = fields.Float(
        string='Tiempo Real Espera (min)',
        compute='_compute_waiting_time',
        store=True,
        help='Tiempo real de espera en cola'
    )
    
    # === INFORMACIÓN ADICIONAL ===
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
    
    customer_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        help='Cliente asociado a la producción'
    )
    
    due_date = fields.Datetime(
        related='production_id.date_planned_finished',
        string='Fecha Límite',
        store=True
    )
    
    setup_required = fields.Boolean(
        string='Requiere Setup',
        default=False,
        help='Indica si requiere tiempo de setup'
    )
    
    setup_time_minutes = fields.Float(
        string='Tiempo Setup (min)',
        default=0.0,
        help='Tiempo requerido para setup'
    )
    
    notes = fields.Text(
        string='Notas',
        help='Observaciones sobre este item'
    )
    
    # === MÉTODOS COMPUTADOS ===
    
    @api.depends('actual_start_time', 'completion_time')
    def _compute_actual_duration(self):
        """Calcular duración real"""
        for item in self:
            if item.actual_start_time and item.completion_time:
                delta = item.completion_time - item.actual_start_time
                item.actual_duration = delta.total_seconds() / 3600.0  # Convertir a horas
            else:
                item.actual_duration = 0.0
    
    @api.depends('entry_time', 'actual_start_time')
    def _compute_waiting_time(self):
        """Calcular tiempo real de espera"""
        for item in self:
            if item.entry_time and item.actual_start_time:
                delta = item.actual_start_time - item.entry_time
                item.actual_waiting_time = delta.total_seconds() / 60.0  # Convertir a minutos
            else:
                item.actual_waiting_time = 0.0
    
    # === MÉTODOS DE ACCIÓN ===
    
    def action_start_processing(self):
        """Iniciar procesamiento del item"""
        self.ensure_one()
        
        if self.state != 'waiting':
            raise UserError("Solo se pueden iniciar items en estado 'Esperando'.")
        
        self.state = 'in_progress'
        self.actual_start_time = fields.Datetime.now()
        
        # Iniciar la orden de producción si no está iniciada
        if self.production_id.state in ['confirmed', 'planned']:
            self.production_id.action_assign()
            if self.production_id.state == 'confirmed':
                self.production_id.button_plan()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Procesamiento Iniciado',
                'message': f'Iniciado procesamiento de {self.production_id.name}',
                'type': 'success'
            }
        }
    
    def action_complete_processing(self):
        """Completar procesamiento del item"""
        self.ensure_one()
        
        if self.state != 'in_progress':
            raise UserError("Solo se pueden completar items en estado 'En Progreso'.")
        
        self.state = 'completed'
        self.completion_time = fields.Datetime.now()
        
        # Iniciar siguiente item en la cola automáticamente
        next_item = self.work_queue_id.get_next_item()
        if next_item:
            next_item.action_start_processing()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Procesamiento Completado',
                'message': f'Completado procesamiento de {self.production_id.name}',
                'type': 'success'
            }
        }
    
    def action_cancel(self):
        """Cancelar item de la cola"""
        self.ensure_one()
        
        self.state = 'cancelled'
        self.completion_time = fields.Datetime.now()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Item Cancelado',
                'message': f'Cancelado item {self.production_id.name}',
                'type': 'info'
            }
        }
    
    def action_move_up(self):
        """Mover item hacia arriba en la cola"""
        self.ensure_one()
        
        if self.sequence > 1:
            # Intercambiar con el item anterior
            previous_item = self.work_queue_id.queue_item_ids.filtered(
                lambda i: i.sequence == self.sequence - 1 and i.state == 'waiting'
            )
            
            if previous_item:
                previous_item.sequence = self.sequence
                self.sequence -= 1
        
        return {'type': 'ir.actions.client', 'tag': 'reload'}
    
    def action_move_down(self):
        """Mover item hacia abajo en la cola"""
        self.ensure_one()
        
        max_sequence = max(self.work_queue_id.queue_item_ids.filtered(
            lambda i: i.state == 'waiting'
        ).mapped('sequence'), default=0)
        
        if self.sequence < max_sequence:
            # Intercambiar con el item siguiente
            next_item = self.work_queue_id.queue_item_ids.filtered(
                lambda i: i.sequence == self.sequence + 1 and i.state == 'waiting'
            )
            
            if next_item:
                next_item.sequence = self.sequence
                self.sequence += 1
        
        return {'type': 'ir.actions.client', 'tag': 'reload'}
    
    def get_item_details(self):
        """Obtener detalles del item para análisis"""
        self.ensure_one()
        
        return {
            'production_name': self.production_id.name,
            'product_name': self.product_id.name,
            'quantity': self.quantity,
            'priority': self.priority,
            'sequence': self.sequence,
            'state': self.state,
            'entry_time': self.entry_time,
            'scheduled_start_time': self.scheduled_start_time,
            'actual_start_time': self.actual_start_time,
            'estimated_duration': self.estimated_duration,
            'actual_duration': self.actual_duration,
            'actual_waiting_time': self.actual_waiting_time,
            'due_date': self.due_date,
            'customer_name': self.customer_id.name if self.customer_id else 'N/A'
        }


# === MÉTODOS ADICIONALES PARA DASHBOARD EN WORK QUEUE ===

class WorkQueue(models.Model):
    _inherit = 'megastock.work.queue'
    
    @api.model
    def get_queue_status_data(self, line_filter='all'):
        """Obtener datos de estado de colas para dashboard"""
        domain = [('state', '=', 'active')]
        
        if line_filter != 'all':
            domain.append(('production_line', '=', line_filter))
        
        queues = self.search(domain)
        
        queue_data = []
        for queue in queues:
            utilization = min(100, (queue.current_items_count / queue.max_capacity * 100)) if queue.max_capacity > 0 else 0
            
            # Calcular tiempo promedio de espera actual
            waiting_items = queue.queue_item_ids.filtered(lambda i: i.state == 'waiting')
            avg_wait_time = 0
            if waiting_items:
                total_wait = sum(item.actual_waiting_time for item in waiting_items if item.actual_waiting_time > 0)
                avg_wait_time = total_wait / len(waiting_items) if len(waiting_items) > 0 else 0
            
            queue_data.append({
                'id': queue.id,
                'name': queue.name,
                'items_count': queue.current_items_count,
                'max_capacity': queue.max_capacity,
                'avg_wait_time': round(avg_wait_time, 1),
                'utilization': round(utilization, 1),
                'status': 'active' if queue.state == 'active' else 'inactive',
                'production_line': queue.production_line,
                'queue_type': queue.queue_type,
                'throughput_last_hour': queue._calculate_hourly_throughput(),
                'efficiency_percentage': queue._calculate_queue_efficiency()
            })
        
        return queue_data
    
    def _calculate_hourly_throughput(self):
        """Calcular throughput de la última hora"""
        one_hour_ago = fields.Datetime.now() - timedelta(hours=1)
        
        completed_items = self.queue_item_ids.filtered(
            lambda i: i.state == 'completed' and 
                     i.completion_time and 
                     i.completion_time >= one_hour_ago
        )
        
        return len(completed_items)
    
    def _calculate_queue_efficiency(self):
        """Calcular eficiencia de la cola"""
        total_items = self.queue_item_ids.filtered(lambda i: i.state == 'completed')
        
        if not total_items:
            return 0.0
        
        # Eficiencia basada en tiempo real vs estimado
        efficiency_sum = 0
        count = 0
        
        for item in total_items:
            if item.estimated_duration > 0 and item.actual_duration > 0:
                item_efficiency = min(100, (item.estimated_duration / item.actual_duration) * 100)
                efficiency_sum += item_efficiency
                count += 1
        
        return round(efficiency_sum / count, 1) if count > 0 else 0.0


class CapacityPlanning(models.Model):
    _inherit = 'megastock.capacity.planning'
    
    @api.model
    def get_capacity_dashboard_data(self, line_filter='all'):
        """Obtener datos de capacidad para dashboard"""
        domain = [('state', '=', 'active')]
        
        if line_filter != 'all':
            domain.append(('production_line_filter', '=', line_filter))
        
        capacity_plans = self.search(domain)
        
        total_capacity = 0
        utilized_capacity = 0
        bottlenecks = []
        workcenters_data = []
        
        for plan in capacity_plans:
            for line in plan.capacity_line_ids:
                total_capacity += line.available_capacity_hours
                utilized_capacity += line.utilized_capacity_hours
                
                workcenters_data.append({
                    'name': line.workcenter_id.name,
                    'utilization_percentage': line.utilization_percentage,
                    'available_capacity': line.available_capacity_hours,
                    'utilized_capacity': line.utilized_capacity_hours,
                    'remaining_capacity': line.available_capacity_hours - line.utilized_capacity_hours
                })
                
                # Identificar cuellos de botella
                if line.utilization_percentage > 90:
                    bottlenecks.append({
                        'workcenter_name': line.workcenter_id.name,
                        'utilization': line.utilization_percentage,
                        'reason': 'Alta utilización',
                        'severity': 'danger' if line.utilization_percentage > 95 else 'warning',
                        'recommended_action': 'Redistribuir carga' if line.utilization_percentage > 95 else 'Monitorear'
                    })
        
        utilization_rate = (utilized_capacity / total_capacity * 100) if total_capacity > 0 else 0
        available_capacity = total_capacity - utilized_capacity
        
        return {
            'total_capacity': round(total_capacity, 1),
            'utilized_capacity': round(utilized_capacity, 1),
            'available_capacity': round(available_capacity, 1),
            'utilization_rate': round(utilization_rate, 1),
            'bottlenecks': bottlenecks,
            'workcenters': workcenters_data,
            'plans_count': len(capacity_plans),
            'critical_workcenters': len([wc for wc in workcenters_data if wc['utilization_percentage'] > 95]),
            'warning_workcenters': len([wc for wc in workcenters_data if 85 < wc['utilization_percentage'] <= 95]),
            'normal_workcenters': len([wc for wc in workcenters_data if wc['utilization_percentage'] <= 85])
        }