# -*- coding: utf-8 -*-

from odoo import models, fields, api

class MrpRouting(models.Model):
    _inherit = 'mrp.routing'
    
    # Campos específicos MEGASTOCK
    routing_type = fields.Selection([
        ('standard', 'Estándar'),
        ('premium', 'Premium'),
        ('alternative', 'Alternativa'),
        ('special', 'Especial')
    ], string='Tipo de Ruta', default='standard')
    
    product_category_ids = fields.Many2many(
        'product.category',
        'routing_category_rel',
        'routing_id',
        'category_id',
        string='Categorías Aplicables',
        help='Categorías de productos para las que aplica esta ruta'
    )
    
    min_lot_size = fields.Float(
        string='Tamaño Mínimo Lote',
        default=100.0,
        help='Cantidad mínima para usar esta ruta eficientemente'
    )
    
    max_lot_size = fields.Float(
        string='Tamaño Máximo Lote',
        default=10000.0,
        help='Cantidad máxima que puede manejar esta ruta'
    )
    
    estimated_lead_time = fields.Float(
        string='Tiempo Estimado Producción (horas)',
        compute='_compute_estimated_lead_time',
        store=True,
        help='Tiempo total estimado de producción'
    )
    
    total_cost_per_unit = fields.Float(
        string='Costo Total por Unidad',
        compute='_compute_total_cost_per_unit',
        store=True,
        help='Costo total por unidad incluyendo todas las operaciones'
    )
    
    efficiency_rating = fields.Float(
        string='Rating de Eficiencia (%)',
        default=85.0,
        help='Eficiencia promedio de esta ruta'
    )
    
    # Análisis de cuellos de botella
    bottleneck_operation_id = fields.Many2one(
        'mrp.routing.workcenter',
        string='Operación Cuello de Botella',
        compute='_compute_bottleneck_operation',
        store=True,
        help='Operación que limita la capacidad de la ruta'
    )
    
    bottleneck_capacity = fields.Float(
        string='Capacidad Cuello Botella (unidades/hora)',
        compute='_compute_bottleneck_operation',
        store=True
    )
    
    # Configuración de planificación
    auto_schedule_enabled = fields.Boolean(
        string='Planificación Automática Habilitada',
        default=True,
        help='Permite planificación automática basada en capacidades'
    )
    
    priority_level = fields.Selection([
        ('1', 'Muy Baja'),
        ('2', 'Baja'),
        ('3', 'Normal'),
        ('4', 'Alta'),
        ('5', 'Muy Alta')
    ], string='Nivel de Prioridad', default='3')
    
    @api.depends('operation_ids', 'operation_ids.time_cycle', 'operation_ids.workcenter_id.time_efficiency')
    def _compute_estimated_lead_time(self):
        """Calcular tiempo estimado total de producción"""
        for routing in self:
            total_time = 0.0
            for operation in routing.operation_ids:
                # Tiempo ciclo + tiempo setup + tiempo de parada
                operation_time = (
                    operation.time_cycle + 
                    (operation.time_mode_batch or 0) + 
                    (operation.workcenter_id.time_start or 0) + 
                    (operation.workcenter_id.time_stop or 0)
                )
                
                # Ajustar por eficiencia del centro de trabajo
                if operation.workcenter_id.time_efficiency:
                    operation_time = operation_time / (operation.workcenter_id.time_efficiency / 100.0)
                
                total_time += operation_time
            
            routing.estimated_lead_time = total_time / 60.0  # Convertir a horas
    
    @api.depends('operation_ids', 'operation_ids.workcenter_id.costs_hour')
    def _compute_total_cost_per_unit(self):
        """Calcular costo total por unidad"""
        for routing in self:
            total_cost = 0.0
            for operation in routing.operation_ids:
                # Costo por hora del centro de trabajo
                hourly_cost = operation.workcenter_id.costs_hour or 0.0
                
                # Tiempo en horas para esta operación
                operation_time_hours = (operation.time_cycle + (operation.time_mode_batch or 0)) / 60.0
                
                # Costo de esta operación
                operation_cost = hourly_cost * operation_time_hours
                
                # Agregar costo energético si está disponible
                if hasattr(operation.workcenter_id, 'energy_cost_per_hour'):
                    operation_cost += operation.workcenter_id.energy_cost_per_hour * operation_time_hours
                
                total_cost += operation_cost
            
            routing.total_cost_per_unit = total_cost
    
    @api.depends('operation_ids', 'operation_ids.workcenter_id.real_capacity')
    def _compute_bottleneck_operation(self):
        """Identificar operación cuello de botella"""
        for routing in self:
            min_capacity = float('inf')
            bottleneck_op = None
            
            for operation in routing.operation_ids:
                if operation.workcenter_id.real_capacity:
                    capacity = operation.workcenter_id.real_capacity
                    if capacity < min_capacity:
                        min_capacity = capacity
                        bottleneck_op = operation
            
            if bottleneck_op:
                routing.bottleneck_operation_id = bottleneck_op.id
                routing.bottleneck_capacity = min_capacity
            else:
                routing.bottleneck_operation_id = False
                routing.bottleneck_capacity = 0.0
    
    def action_analyze_routing_efficiency(self):
        """Analizar eficiencia de la ruta"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'Análisis de Eficiencia - {self.name}',
            'res_model': 'megastock.routing.efficiency.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_routing_id': self.id,
            }
        }
    
    def action_simulate_production(self):
        """Simular producción con diferentes lotes"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'Simulación de Producción - {self.name}',
            'res_model': 'megastock.production.simulation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_routing_id': self.id,
            }
        }
    
    def calculate_optimal_lot_size(self, target_quantity):
        """Calcular tamaño óptimo de lote para una cantidad objetivo"""
        if not self.bottleneck_capacity:
            return target_quantity
        
        # Algoritmo simple para optimizar lotes basado en setup times
        setup_cost_per_lot = 0.0
        for operation in self.operation_ids:
            setup_time = operation.time_mode_batch or 0
            setup_cost = setup_time * (operation.workcenter_id.costs_hour or 0) / 60.0
            setup_cost_per_lot += setup_cost
        
        if setup_cost_per_lot == 0:
            return min(target_quantity, self.max_lot_size)
        
        # Fórmula EOQ adaptada para manufactura
        # Balancear costo de setup vs costo de inventario
        holding_cost_rate = 0.15  # 15% anual
        unit_cost = self.total_cost_per_unit or 1.0
        annual_demand = target_quantity * 12  # Asumir demanda mensual
        
        optimal_lot = ((2 * annual_demand * setup_cost_per_lot) / (holding_cost_rate * unit_cost)) ** 0.5
        
        # Ajustar a límites de la ruta
        optimal_lot = max(self.min_lot_size, min(optimal_lot, self.max_lot_size))
        
        return round(optimal_lot)
    
    def get_available_capacity(self, date_from, date_to):
        """Obtener capacidad disponible en el período"""
        available_capacity = {}
        
        for operation in self.operation_ids:
            workcenter = operation.workcenter_id
            
            # Capacidad teórica en el período
            period_hours = (date_to - date_from).total_seconds() / 3600.0
            theoretical_capacity = workcenter.real_capacity * period_hours
            
            # Restar capacidad ya comprometida (órdenes de producción existentes)
            # Esto requeriría consulta a órdenes de producción programadas
            committed_capacity = 0.0  # Simplificado por ahora
            
            available_capacity[operation.id] = {
                'operation_name': operation.name,
                'workcenter_name': workcenter.name,
                'theoretical_capacity': theoretical_capacity,
                'committed_capacity': committed_capacity,
                'available_capacity': theoretical_capacity - committed_capacity,
                'capacity_units': workcenter.capacity_unit or 'units'
            }
        
        return available_capacity
    
    @api.model
    def suggest_routing_for_product(self, product_id, quantity):
        """Sugerir mejor ruta para un producto y cantidad"""
        product = self.env['product.product'].browse(product_id)
        
        # Buscar rutas aplicables por categoría de producto
        applicable_routings = self.search([
            ('product_category_ids', 'in', [product.categ_id.id]),
            ('min_lot_size', '<=', quantity),
            ('max_lot_size', '>=', quantity),
            ('active', '=', True)
        ])
        
        if not applicable_routings:
            # Buscar rutas sin restricción de categoría
            applicable_routings = self.search([
                ('min_lot_size', '<=', quantity),
                ('max_lot_size', '>=', quantity),
                ('active', '=', True)
            ])
        
        if not applicable_routings:
            return None
        
        # Ranking por eficiencia y costo
        best_routing = None
        best_score = 0
        
        for routing in applicable_routings:
            # Score basado en eficiencia (peso 60%) y costo (peso 40%)
            efficiency_score = routing.efficiency_rating / 100.0
            cost_score = 1.0 / (routing.total_cost_per_unit + 1.0)  # Inversamente proporcional
            
            total_score = (efficiency_score * 0.6) + (cost_score * 0.4)
            
            if total_score > best_score:
                best_score = total_score
                best_routing = routing
        
        return best_routing
    
    def generate_production_schedule(self, quantity, required_date):
        """Generar cronograma de producción optimizado"""
        if not self.auto_schedule_enabled:
            return None
        
        optimal_lot_size = self.calculate_optimal_lot_size(quantity)
        number_of_lots = int((quantity + optimal_lot_size - 1) / optimal_lot_size)  # Ceiling division
        
        schedule = []
        current_date = required_date
        
        for lot_number in range(number_of_lots):
            lot_quantity = min(optimal_lot_size, quantity - (lot_number * optimal_lot_size))
            
            lot_schedule = {
                'lot_number': lot_number + 1,
                'lot_quantity': lot_quantity,
                'operations': []
            }
            
            # Programar hacia atrás desde fecha requerida
            for operation in reversed(self.operation_ids):
                operation_duration = (operation.time_cycle * lot_quantity + 
                                    (operation.time_mode_batch or 0)) / 60.0  # Horas
                
                operation_end = current_date
                operation_start = current_date - timedelta(hours=operation_duration)
                
                lot_schedule['operations'].insert(0, {
                    'operation_id': operation.id,
                    'operation_name': operation.name,
                    'workcenter_name': operation.workcenter_id.name,
                    'start_date': operation_start,
                    'end_date': operation_end,
                    'duration_hours': operation_duration,
                    'quantity': lot_quantity
                })
                
                current_date = operation_start
            
            schedule.insert(0, lot_schedule)
        
        return {
            'routing_name': self.name,
            'total_quantity': quantity,
            'optimal_lot_size': optimal_lot_size,
            'number_of_lots': number_of_lots,
            'estimated_start_date': current_date,
            'required_date': required_date,
            'total_lead_time_hours': self.estimated_lead_time * number_of_lots,
            'lots': schedule
        }