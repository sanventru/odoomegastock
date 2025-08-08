# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class ProductionPlan(models.Model):
    _name = 'megastock.production.plan'
    _description = 'Plan Maestro de Producción MEGASTOCK'
    _order = 'planning_date desc, priority desc'
    _rec_name = 'display_name'
    
    # === INFORMACIÓN BÁSICA ===
    name = fields.Char(
        string='Nombre del Plan',
        required=True,
        copy=False,
        default=lambda self: self._get_default_name()
    )
    
    display_name = fields.Char(
        string='Nombre Completo',
        compute='_compute_display_name',
        store=True
    )
    
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmado'), 
        ('in_progress', 'En Progreso'),
        ('completed', 'Completado'),
        ('cancelled', 'Cancelado')
    ], string='Estado', default='draft', required=True, tracking=True)
    
    planning_date = fields.Date(
        string='Fecha de Planificación',
        required=True,
        default=fields.Date.today
    )
    
    horizon_days = fields.Integer(
        string='Horizonte de Planificación (días)',
        default=30,
        help='Número de días a planificar hacia adelante'
    )
    
    date_from = fields.Date(
        string='Desde',
        required=True,
        default=fields.Date.today
    )
    
    date_to = fields.Date(
        string='Hasta',
        compute='_compute_date_to',
        store=True
    )
    
    # === PARÁMETROS DE PLANIFICACIÓN ===
    planning_type = fields.Selection([
        ('mrp', 'MRP - Planificación por Demanda'),
        ('capacity', 'Planificación por Capacidad'),
        ('mixed', 'Planificación Mixta'),
        ('manual', 'Planificación Manual')
    ], string='Tipo de Planificación', default='mrp', required=True)
    
    planning_method = fields.Selection([
        ('forward', 'Planificación Hacia Adelante'),
        ('backward', 'Planificación Hacia Atrás'), 
        ('bottleneck', 'Planificación por Cuello de Botella')
    ], string='Método de Planificación', default='forward', required=True)
    
    priority = fields.Selection([
        ('low', 'Baja'),
        ('medium', 'Media'),
        ('high', 'Alta'),
        ('urgent', 'Urgente')
    ], string='Prioridad', default='medium', required=True)
    
    auto_reschedule = fields.Boolean(
        string='Reprogramación Automática',
        default=True,
        help='Permite reprogramación automática ante cambios'
    )
    
    consider_capacity_constraints = fields.Boolean(
        string='Considerar Restricciones de Capacidad',
        default=True,
        help='Planificar considerando capacidad finita'
    )
    
    # === DEMANDA Y PRONÓSTICOS ===
    demand_source = fields.Selection([
        ('sales_orders', 'Órdenes de Venta'),
        ('forecast', 'Pronóstico de Demanda'),
        ('stock_min', 'Punto de Reorden'),
        ('mixed', 'Fuentes Mixtas')
    ], string='Fuente de Demanda', default='mixed', required=True)
    
    include_forecast = fields.Boolean(
        string='Incluir Pronósticos',
        default=True,
        help='Incluir demanda pronosticada'
    )
    
    forecast_accuracy = fields.Float(
        string='Precisión de Pronóstico (%)',
        default=85.0,
        help='Precisión histórica del pronóstico'
    )
    
    safety_stock_days = fields.Integer(
        string='Stock de Seguridad (días)',
        default=7,
        help='Días de stock de seguridad a mantener'
    )
    
    # === LÍNEAS DEL PLAN ===
    plan_line_ids = fields.One2many(
        'megastock.production.plan.line',
        'plan_id',
        string='Líneas del Plan',
        help='Productos incluidos en la planificación'
    )
    
    # === RESTRICCIONES Y RECURSOS ===
    workcenter_ids = fields.Many2many(
        'mrp.workcenter',
        'production_plan_workcenter_rel',
        'plan_id',
        'workcenter_id',
        string='Centros de Trabajo',
        help='Centros de trabajo a considerar en la planificación'
    )
    
    production_line_filter = fields.Selection([
        ('all', 'Todas las Líneas'),
        ('papel_periodico', 'Papel Periódico'),
        ('cajas', 'Cajas & Planchas'),
        ('lamina_micro', 'Lámina Micro Corrugada')
    ], string='Filtro por Línea', default='all')
    
    max_overtime_hours = fields.Float(
        string='Máximo Horas Extra',
        default=0.0,
        help='Máximo de horas extra permitidas'
    )
    
    # === RESULTADOS Y MÉTRICAS ===
    total_products = fields.Integer(
        string='Total Productos',
        compute='_compute_plan_metrics',
        store=True
    )
    
    total_quantity = fields.Float(
        string='Cantidad Total',
        compute='_compute_plan_metrics',
        store=True
    )
    
    total_estimated_cost = fields.Float(
        string='Costo Total Estimado',
        compute='_compute_plan_metrics',
        store=True
    )
    
    planned_efficiency = fields.Float(
        string='Eficiencia Planificada (%)',
        default=85.0,
        help='Eficiencia objetivo del plan'
    )
    
    capacity_utilization = fields.Float(
        string='Utilización de Capacidad (%)',
        compute='_compute_capacity_utilization',
        store=True
    )
    
    bottleneck_workcenter_id = fields.Many2one(
        'mrp.workcenter',
        string='Cuello de Botella',
        compute='_compute_bottleneck',
        store=True
    )
    
    # === PRODUCCIONES GENERADAS ===
    production_ids = fields.One2many(
        'mrp.production',
        'production_plan_id',
        string='Órdenes de Producción',
        help='Órdenes de producción generadas desde este plan'
    )
    
    production_count = fields.Integer(
        string='Órdenes Generadas',
        compute='_compute_production_count'
    )
    
    # === ANÁLISIS Y SEGUIMIENTO ===
    last_calculation_date = fields.Datetime(
        string='Última Actualización',
        readonly=True
    )
    
    calculation_time = fields.Float(
        string='Tiempo de Cálculo (s)',
        readonly=True,
        help='Tiempo tomado para calcular el plan'
    )
    
    optimization_log = fields.Text(
        string='Log de Optimización',
        readonly=True,
        help='Registro detallado del proceso de optimización'
    )
    
    notes = fields.Text(
        string='Notas',
        help='Observaciones adicionales sobre el plan'
    )
    
    # === CAMPOS COMPUTADOS ===
    
    @api.depends('name', 'planning_date')
    def _compute_display_name(self):
        """Computar nombre completo para mostrar"""
        for plan in self:
            plan.display_name = f"{plan.name} - {plan.planning_date.strftime('%d/%m/%Y') if plan.planning_date else ''}"
    
    @api.depends('date_from', 'horizon_days')
    def _compute_date_to(self):
        """Calcular fecha final del plan"""
        for plan in self:
            if plan.date_from and plan.horizon_days:
                plan.date_to = plan.date_from + timedelta(days=plan.horizon_days)
            else:
                plan.date_to = plan.date_from
    
    @api.depends('plan_line_ids')
    def _compute_plan_metrics(self):
        """Calcular métricas del plan"""
        for plan in self:
            plan.total_products = len(plan.plan_line_ids)
            plan.total_quantity = sum(plan.plan_line_ids.mapped('planned_quantity'))
            plan.total_estimated_cost = sum(plan.plan_line_ids.mapped('estimated_cost'))
    
    @api.depends('production_ids')
    def _compute_production_count(self):
        """Contar órdenes de producción generadas"""
        for plan in self:
            plan.production_count = len(plan.production_ids)
    
    @api.depends('plan_line_ids', 'workcenter_ids')
    def _compute_capacity_utilization(self):
        """Calcular utilización de capacidad"""
        for plan in self:
            if plan.workcenter_ids and plan.plan_line_ids:
                total_required_hours = sum(
                    line.estimated_hours for line in plan.plan_line_ids
                )
                
                # Capacidad disponible en el horizonte
                available_hours = 0.0
                for workcenter in plan.workcenter_ids:
                    daily_capacity = workcenter.time_efficiency * 24  # Asumiendo 24h teóricas
                    available_hours += daily_capacity * plan.horizon_days
                
                if available_hours > 0:
                    plan.capacity_utilization = (total_required_hours / available_hours) * 100
                else:
                    plan.capacity_utilization = 0.0
            else:
                plan.capacity_utilization = 0.0
    
    @api.depends('plan_line_ids', 'workcenter_ids')
    def _compute_bottleneck(self):
        """Identificar cuello de botella"""
        for plan in self:
            if plan.workcenter_ids and plan.plan_line_ids:
                workcenter_loads = {}
                
                for line in plan.plan_line_ids:
                    # Distribuir carga entre centros de trabajo (simplificado)
                    for workcenter in plan.workcenter_ids:
                        if workcenter.id not in workcenter_loads:
                            workcenter_loads[workcenter.id] = 0.0
                        workcenter_loads[workcenter.id] += line.estimated_hours / len(plan.workcenter_ids)
                
                # Encontrar el centro con mayor carga
                if workcenter_loads:
                    bottleneck_id = max(workcenter_loads, key=workcenter_loads.get)
                    plan.bottleneck_workcenter_id = bottleneck_id
                else:
                    plan.bottleneck_workcenter_id = False
            else:
                plan.bottleneck_workcenter_id = False
    
    # === MÉTODOS DE UTILIDAD ===
    
    def _get_default_name(self):
        """Generar nombre por defecto"""
        return f"Plan {datetime.now().strftime('%Y%m%d-%H%M')}"
    
    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        """Validar fechas del plan"""
        for plan in self:
            if plan.date_from and plan.date_to and plan.date_from > plan.date_to:
                raise ValidationError("La fecha de inicio no puede ser posterior a la fecha final.")
    
    @api.constrains('horizon_days')
    def _check_horizon(self):
        """Validar horizonte de planificación"""
        for plan in self:
            if plan.horizon_days <= 0:
                raise ValidationError("El horizonte de planificación debe ser mayor a cero.")
            if plan.horizon_days > 365:
                raise ValidationError("El horizonte de planificación no puede exceder 365 días.")
    
    # === MÉTODOS DE ACCIÓN ===
    
    def action_confirm(self):
        """Confirmar el plan de producción"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError("Solo se pueden confirmar planes en estado borrador.")
        
        if not self.plan_line_ids:
            raise UserError("No se puede confirmar un plan sin líneas de productos.")
        
        self.state = 'confirmed'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Plan Confirmado',
                'message': f'Plan {self.name} confirmado exitosamente.',
                'type': 'success',
            }
        }
    
    def action_calculate_plan(self):
        """Ejecutar cálculo del plan de producción"""
        self.ensure_one()
        
        start_time = datetime.now()
        
        try:
            # Limpiar líneas existentes
            self.plan_line_ids.unlink()
            
            # Ejecutar algoritmo MRP
            if self.planning_type == 'mrp':
                self._execute_mrp_planning()
            elif self.planning_type == 'capacity':
                self._execute_capacity_planning()
            elif self.planning_type == 'mixed':
                self._execute_mixed_planning()
            else:
                # Planificación manual - no hacer nada automático
                pass
            
            # Optimizar secuencia si es necesario
            if self.auto_reschedule:
                self._optimize_sequence()
            
            # Registrar tiempo de cálculo
            end_time = datetime.now()
            self.calculation_time = (end_time - start_time).total_seconds()
            self.last_calculation_date = end_time
            
            # Cambiar estado si estaba en borrador
            if self.state == 'draft':
                self.state = 'confirmed'
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Cálculo Completado',
                    'message': f'Plan calculado en {self.calculation_time:.2f} segundos. '
                              f'Se generaron {len(self.plan_line_ids)} líneas de planificación.',
                    'type': 'success',
                }
            }
            
        except Exception as e:
            _logger.error(f"Error calculando plan {self.name}: {str(e)}")
            
            self.optimization_log = f"ERROR: {str(e)}\n{self.optimization_log or ''}"
            
            raise UserError(f"Error en el cálculo del plan: {str(e)}")
    
    def _execute_mrp_planning(self):
        """Ejecutar planificación MRP"""
        log_entries = []
        log_entries.append("=== INICIANDO PLANIFICACIÓN MRP ===")
        
        # 1. Obtener demanda
        demand_data = self._get_demand_requirements()
        log_entries.append(f"Demanda obtenida: {len(demand_data)} productos")
        
        # 2. Explotar BOM y calcular necesidades
        material_requirements = self._explode_bom_requirements(demand_data)
        log_entries.append(f"Explosión BOM: {len(material_requirements)} materiales")
        
        # 3. Verificar disponibilidad
        availability_data = self._check_material_availability(material_requirements)
        log_entries.append("Disponibilidad verificada")
        
        # 4. Generar plan de producción
        production_items = self._generate_production_items(availability_data)
        log_entries.append(f"Items de producción: {len(production_items)}")
        
        # 5. Crear líneas del plan
        for item in production_items:
            self._create_plan_line(item)
        
        log_entries.append("=== PLANIFICACIÓN MRP COMPLETADA ===")
        self.optimization_log = '\n'.join(log_entries)
    
    def _get_demand_requirements(self):
        """Obtener requerimientos de demanda"""
        demand_data = {}
        
        # Demanda de órdenes de venta
        if self.demand_source in ['sales_orders', 'mixed']:
            sales_demand = self._get_sales_demand()
            for product_id, qty in sales_demand.items():
                if product_id not in demand_data:
                    demand_data[product_id] = 0.0
                demand_data[product_id] += qty
        
        # Demanda de pronósticos
        if self.demand_source in ['forecast', 'mixed'] and self.include_forecast:
            forecast_demand = self._get_forecast_demand()
            for product_id, qty in forecast_demand.items():
                if product_id not in demand_data:
                    demand_data[product_id] = 0.0
                demand_data[product_id] += qty
        
        # Demanda por punto de reorden
        if self.demand_source in ['stock_min', 'mixed']:
            reorder_demand = self._get_reorder_demand()
            for product_id, qty in reorder_demand.items():
                if product_id not in demand_data:
                    demand_data[product_id] = 0.0
                demand_data[product_id] += qty
        
        return demand_data
    
    def _get_sales_demand(self):
        """Obtener demanda de órdenes de venta"""
        sales_lines = self.env['sale.order.line'].search([
            ('order_id.state', 'in', ['sale', 'done']),
            ('order_id.commitment_date', '>=', self.date_from),
            ('order_id.commitment_date', '<=', self.date_to),
            ('product_id.type', '=', 'product')
        ])
        
        demand = {}
        for line in sales_lines:
            remaining_qty = line.product_uom_qty - line.qty_delivered
            if remaining_qty > 0:
                if line.product_id.id not in demand:
                    demand[line.product_id.id] = 0.0
                demand[line.product_id.id] += remaining_qty
        
        return demand
    
    def _get_forecast_demand(self):
        """Obtener demanda pronosticada"""
        # Implementación simplificada - en producción esto vendría de un módulo de pronósticos
        products = self.env['product.product'].search([
            ('type', '=', 'product'),
            ('categ_id', 'in', self.env.ref('megastock_products.category_cajas').ids)
        ])
        
        forecast = {}
        for product in products:
            # Pronóstico basado en ventas históricas (simplificado)
            historical_avg = self._get_historical_average_sales(product)
            adjusted_forecast = historical_avg * (self.forecast_accuracy / 100.0)
            
            if adjusted_forecast > 0:
                forecast[product.id] = adjusted_forecast
        
        return forecast
    
    def _get_historical_average_sales(self, product):
        """Obtener promedio histórico de ventas"""
        # Buscar ventas de los últimos 90 días
        ninety_days_ago = self.date_from - timedelta(days=90)
        
        sales_lines = self.env['sale.order.line'].search([
            ('product_id', '=', product.id),
            ('order_id.state', 'in', ['sale', 'done']),
            ('order_id.date_order', '>=', ninety_days_ago),
            ('order_id.date_order', '<', self.date_from)
        ])
        
        total_sold = sum(sales_lines.mapped('qty_delivered'))
        daily_avg = total_sold / 90 if total_sold > 0 else 0
        
        # Proyectar para el horizonte de planificación
        return daily_avg * self.horizon_days
    
    def _get_reorder_demand(self):
        """Obtener demanda por punto de reorden"""
        reorder_demand = {}
        
        # Buscar productos con stock bajo el punto de reorden
        products = self.env['product.product'].search([
            ('type', '=', 'product'),
            ('active', '=', True)
        ])
        
        for product in products:
            current_stock = product.qty_available
            min_stock = getattr(product, 'reordering_min_qty', 0) or 0
            
            if current_stock < min_stock:
                # Calcular cantidad para reponer hasta el máximo
                max_stock = getattr(product, 'reordering_max_qty', 0) or min_stock * 2
                reorder_qty = max_stock - current_stock
                
                if reorder_qty > 0:
                    reorder_demand[product.id] = reorder_qty
        
        return reorder_demand
    
    def _explode_bom_requirements(self, demand_data):
        """Explotar BOM para obtener requerimientos de materiales"""
        requirements = {}
        
        for product_id, quantity in demand_data.items():
            product = self.env['product.product'].browse(product_id)
            
            # Buscar BOM para el producto
            bom = self.env['mrp.bom']._bom_find(product=product)
            
            if bom:
                # Explotar BOM
                bom_data = bom.explode(product, quantity)
                
                for line_data in bom_data[0]:  # line_data es (bom_line, dict)
                    bom_line, line_info = line_data
                    material_id = bom_line.product_id.id
                    required_qty = line_info['qty']
                    
                    if material_id not in requirements:
                        requirements[material_id] = {
                            'total_required': 0.0,
                            'bom_lines': []
                        }
                    
                    requirements[material_id]['total_required'] += required_qty
                    requirements[material_id]['bom_lines'].append({
                        'product_id': product_id,
                        'bom_line': bom_line,
                        'qty': required_qty
                    })
            else:
                # Si no hay BOM, el producto se produce directamente
                if product_id not in requirements:
                    requirements[product_id] = {
                        'total_required': 0.0,
                        'bom_lines': []
                    }
                requirements[product_id]['total_required'] += quantity
        
        return requirements
    
    def _check_material_availability(self, requirements):
        """Verificar disponibilidad de materiales"""
        availability_data = {}
        
        for material_id, req_data in requirements.items():
            material = self.env['product.product'].browse(material_id)
            current_stock = material.qty_available
            required_qty = req_data['total_required']
            
            availability_data[material_id] = {
                'material': material,
                'required_qty': required_qty,
                'current_stock': current_stock,
                'shortage': max(0, required_qty - current_stock),
                'available_for_production': min(current_stock, required_qty),
                'bom_lines': req_data['bom_lines']
            }
        
        return availability_data
    
    def _generate_production_items(self, availability_data):
        """Generar items de producción"""
        production_items = []
        
        # Lista de productos finales (que tienen demanda directa)
        final_products = set()
        for material_id, data in availability_data.items():
            for bom_line in data['bom_lines']:
                final_products.add(bom_line['product_id'])
        
        for product_id in final_products:
            product = self.env['product.product'].browse(product_id)
            
            # Calcular cantidad total demandada para este producto
            total_demand = 0.0
            for material_id, data in availability_data.items():
                for bom_line in data['bom_lines']:
                    if bom_line['product_id'] == product_id:
                        # Esto es simplificado, en realidad debería considerar la disponibilidad
                        total_demand += bom_line['qty']
            
            if total_demand > 0:
                production_items.append({
                    'product': product,
                    'quantity': total_demand,
                    'priority': self._calculate_item_priority(product),
                    'estimated_cost': self._estimate_production_cost(product, total_demand),
                    'estimated_hours': self._estimate_production_time(product, total_demand)
                })
        
        # Ordenar por prioridad
        production_items.sort(key=lambda x: x['priority'], reverse=True)
        
        return production_items
    
    def _calculate_item_priority(self, product):
        """Calcular prioridad del item"""
        priority_score = 0
        
        # Prioridad por categoría
        if product.categ_id.name == 'Cajas Urgentes':
            priority_score += 100
        elif 'urgente' in product.name.lower():
            priority_score += 50
        
        # Prioridad por stock
        if product.qty_available <= 0:
            priority_score += 30
        
        # Prioridad por órdenes de venta pendientes
        pending_sales = self.env['sale.order.line'].search_count([
            ('product_id', '=', product.id),
            ('order_id.state', '=', 'sale'),
            ('qty_delivered', '<', 'product_uom_qty')
        ])
        priority_score += pending_sales * 10
        
        return priority_score
    
    def _estimate_production_cost(self, product, quantity):
        """Estimar costo de producción"""
        # Buscar BOM para calcular costo
        bom = self.env['mrp.bom']._bom_find(product=product)
        
        if bom:
            material_cost = 0.0
            for line in bom.bom_line_ids:
                line_qty = (quantity / bom.product_qty) * line.product_qty
                material_cost += line_qty * line.product_id.standard_price
            
            # Agregar costo de operaciones (simplificado)
            operation_cost = 0.0
            if bom.routing_id:
                for operation in bom.routing_id.operation_ids:
                    op_time = (operation.time_cycle * quantity) / 60.0  # Convertir a horas
                    op_cost = op_time * (operation.workcenter_id.costs_hour or 0)
                    operation_cost += op_cost
            
            return material_cost + operation_cost
        else:
            # Si no hay BOM, usar precio estándar
            return quantity * product.standard_price
    
    def _estimate_production_time(self, product, quantity):
        """Estimar tiempo de producción en horas"""
        bom = self.env['mrp.bom']._bom_find(product=product)
        
        if bom and bom.routing_id:
            total_minutes = 0.0
            for operation in bom.routing_id.operation_ids:
                op_minutes = (operation.time_cycle * quantity) + (operation.time_mode_batch or 0)
                total_minutes += op_minutes
            
            return total_minutes / 60.0  # Convertir a horas
        else:
            # Tiempo estimado por defecto
            return quantity * 0.1  # 0.1 horas por unidad
    
    def _create_plan_line(self, item_data):
        """Crear línea del plan de producción"""
        return self.env['megastock.production.plan.line'].create({
            'plan_id': self.id,
            'product_id': item_data['product'].id,
            'planned_quantity': item_data['quantity'],
            'priority_score': item_data['priority'],
            'estimated_cost': item_data['estimated_cost'],
            'estimated_hours': item_data['estimated_hours'],
            'suggested_start_date': self.date_from,
            'state': 'planned'
        })
    
    def _execute_capacity_planning(self):
        """Ejecutar planificación por capacidad"""
        # Implementación simplificada de planificación por capacidad
        pass
    
    def _execute_mixed_planning(self):
        """Ejecutar planificación mixta"""
        # Combinar MRP con restricciones de capacidad
        self._execute_mrp_planning()
        
        if self.consider_capacity_constraints:
            self._apply_capacity_constraints()
    
    def _apply_capacity_constraints(self):
        """Aplicar restricciones de capacidad"""
        # Verificar si las líneas del plan exceden la capacidad disponible
        # y ajustar fechas o cantidades según sea necesario
        pass
    
    def _optimize_sequence(self):
        """Optimizar secuencia de producción"""
        # Aplicar algoritmos de optimización de secuencia
        # como minimizar setup times, balancear cargas, etc.
        pass
    
    def action_generate_productions(self):
        """Generar órdenes de producción desde el plan"""
        self.ensure_one()
        
        if self.state not in ['confirmed', 'in_progress']:
            raise UserError("Solo se pueden generar producciones desde planes confirmados.")
        
        if not self.plan_line_ids:
            raise UserError("No hay líneas en el plan para generar producciones.")
        
        productions_created = 0
        
        for line in self.plan_line_ids.filtered(lambda l: l.state == 'planned'):
            # Buscar BOM para el producto
            bom = self.env['mrp.bom']._bom_find(product=line.product_id)
            
            if bom:
                # Crear orden de producción
                production = self.env['mrp.production'].create({
                    'name': self.env['ir.sequence'].next_by_code('mrp.production') or 'New',
                    'product_id': line.product_id.id,
                    'product_qty': line.planned_quantity,
                    'product_uom_id': line.product_id.uom_id.id,
                    'bom_id': bom.id,
                    'routing_id': bom.routing_id.id if bom.routing_id else False,
                    'date_planned_start': line.suggested_start_date,
                    'date_planned_finished': line.suggested_end_date,
                    'production_plan_id': self.id,
                    'origin': f"Plan: {self.name}",
                    'priority': line.priority_score,
                })
                
                # Marcar línea como generada
                line.state = 'in_production'
                line.production_id = production.id
                
                productions_created += 1
            else:
                _logger.warning(f"No se encontró BOM para producto {line.product_id.name}")
        
        if productions_created > 0:
            self.state = 'in_progress'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Producciones Generadas',
                'message': f'Se generaron {productions_created} órdenes de producción.',
                'type': 'success',
            }
        }
    
    def action_view_productions(self):
        """Ver órdenes de producción generadas"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Órdenes de Producción',
            'res_model': 'mrp.production',
            'view_mode': 'tree,form',
            'domain': [('production_plan_id', '=', self.id)],
            'context': {'default_production_plan_id': self.id}
        }
    
    def action_reschedule(self):
        """Lanzar wizard de reprogramación"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reprogramar Plan',
            'res_model': 'megastock.rescheduling.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_plan_id': self.id}
        }
    
    @api.model
    def auto_generate_daily_plan(self):
        """Generar plan automático diario"""
        # Verificar si ya existe un plan para hoy
        today = fields.Date.today()
        existing_plan = self.search([
            ('planning_date', '=', today),
            ('state', 'in', ['confirmed', 'in_progress'])
        ], limit=1)
        
        if existing_plan:
            _logger.info(f"Ya existe plan para {today}: {existing_plan.name}")
            return existing_plan
        
        # Crear nuevo plan automático
        plan = self.create({
            'name': f'Plan Automático {today.strftime("%d/%m/%Y")}',
            'planning_date': today,
            'date_from': today,
            'horizon_days': 7,  # Plan semanal
            'planning_type': 'mixed',
            'demand_source': 'mixed',
            'auto_reschedule': True,
            'consider_capacity_constraints': True,
        })
        
        # Calcular plan automáticamente
        plan.action_calculate_plan()
        
        _logger.info(f"Plan automático generado: {plan.name}")
        return plan

    # === MÉTODOS PARA DASHBOARD ===
    
    @api.model
    def get_dashboard_data(self, line_filter='all', **kwargs):
        """Obtener datos agregados para dashboard"""
        domain = [('state', 'in', ['confirmed', 'in_progress'])]
        
        if line_filter != 'all':
            domain.append(('production_line_filter', '=', line_filter))
        
        plans = self.search(domain)
        
        # Calcular estadísticas agregadas
        total_productions = sum(plans.mapped('total_productions_count'))
        completed_productions = sum(plans.mapped('completed_productions'))
        in_progress_productions = sum(plans.mapped('in_progress_productions'))
        
        # Calcular OEE promedio ponderado
        oee_values = []
        for plan in plans:
            if plan.average_oee > 0:
                oee_values.append(plan.average_oee)
        
        avg_oee = sum(oee_values) / len(oee_values) if oee_values else 0
        
        # Calcular eficiencia de entregas
        on_time_count = sum(plans.mapped('on_time_deliveries'))
        total_deliveries = sum(plans.mapped('total_deliveries'))
        delivery_rate = (on_time_count / total_deliveries * 100) if total_deliveries > 0 else 0
        
        return {
            'summary': {
                'total_productions': total_productions,
                'completed_productions': completed_productions,
                'in_progress_productions': in_progress_productions,
                'completion_rate': (completed_productions / total_productions * 100) if total_productions > 0 else 0,
                'average_oee': round(avg_oee, 1),
                'delivery_rate': round(delivery_rate, 1)
            },
            'plans': plans.mapped('name'),
            'active_plans_count': len(plans),
            'last_update': fields.Datetime.now()
        }
    
    @api.model
    def get_active_alerts(self, line_filter='all'):
        """Obtener alertas críticas para dashboard"""
        alerts = []
        
        # Alertas de planes atrasados
        overdue_plans = self.search([
            ('state', 'in', ['confirmed', 'in_progress']),
            ('date_to', '<', fields.Date.today())
        ])
        
        for plan in overdue_plans:
            alerts.append({
                'id': f'plan_{plan.id}',
                'type': 'plan_overdue',
                'title': 'Plan Vencido',
                'message': f'Plan {plan.name} vencido',
                'severity': 'high',
                'timestamp': plan.date_to,
                'action_url': f'/web#id={plan.id}&model=megastock.production.plan&view_type=form'
            })
        
        # Alertas de baja eficiencia
        low_efficiency_plans = self.search([
            ('state', 'in', ['in_progress']),
            ('average_efficiency', '<', 75)
        ])
        
        for plan in low_efficiency_plans:
            alerts.append({
                'id': f'efficiency_{plan.id}',
                'type': 'low_efficiency',
                'title': 'Eficiencia Baja',
                'message': f'Plan {plan.name} - Eficiencia {plan.average_efficiency:.1f}%',
                'severity': 'medium',
                'timestamp': fields.Datetime.now(),
                'action_url': f'/web#id={plan.id}&model=megastock.production.plan&view_type=form'
            })
        
        # Alertas de materiales faltantes
        material_shortage_plans = self.search([
            ('state', '=', 'confirmed'),
            ('material_availability_rate', '<', 90)
        ])
        
        for plan in material_shortage_plans:
            alerts.append({
                'id': f'materials_{plan.id}',
                'type': 'material_shortage',
                'title': 'Materiales Insuficientes',
                'message': f'Plan {plan.name} - {plan.material_availability_rate:.1f}% disponible',
                'severity': 'high',
                'timestamp': fields.Datetime.now(),
                'action_url': f'/web#id={plan.id}&model=megastock.production.plan&view_type=form'
            })
        
        return sorted(alerts, key=lambda x: {'high': 3, 'medium': 2, 'low': 1}[x['severity']], reverse=True)
    
    def get_planning_performance_metrics(self):
        """Obtener métricas de performance del plan"""
        self.ensure_one()
        
        return {
            'plan_name': self.name,
            'state': self.state,
            'completion_percentage': self.completion_percentage,
            'average_oee': self.average_oee,
            'average_efficiency': self.average_efficiency,
            'material_availability_rate': self.material_availability_rate,
            'on_time_delivery_rate': (self.on_time_deliveries / self.total_deliveries * 100) if self.total_deliveries > 0 else 0,
            'total_productions': self.total_productions_count,
            'completed_productions': self.completed_productions,
            'in_progress_productions': self.in_progress_productions,
            'planned_cost': self.total_planned_cost,
            'actual_cost': self.total_actual_cost,
            'cost_variance': ((self.total_actual_cost - self.total_planned_cost) / self.total_planned_cost * 100) if self.total_planned_cost > 0 else 0,
            'planning_date': self.planning_date,
            'horizon_days': self.horizon_days
        }


class ProductionPlanLine(models.Model):
    _name = 'megastock.production.plan.line'
    _description = 'Línea del Plan de Producción'
    _order = 'priority_score desc, suggested_start_date'
    
    plan_id = fields.Many2one(
        'megastock.production.plan',
        string='Plan de Producción',
        required=True,
        ondelete='cascade'
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Producto',
        required=True,
        help='Producto a producir'
    )
    
    planned_quantity = fields.Float(
        string='Cantidad Planificada',
        required=True,
        help='Cantidad a producir'
    )
    
    state = fields.Selection([
        ('planned', 'Planificado'),
        ('in_production', 'En Producción'),
        ('completed', 'Completado'),
        ('cancelled', 'Cancelado')
    ], string='Estado', default='planned', required=True)
    
    priority_score = fields.Float(
        string='Score de Prioridad',
        help='Score calculado para priorización'
    )
    
    estimated_cost = fields.Float(
        string='Costo Estimado',
        help='Costo estimado de producir esta cantidad'
    )
    
    estimated_hours = fields.Float(
        string='Horas Estimadas',
        help='Tiempo estimado de producción en horas'
    )
    
    suggested_start_date = fields.Datetime(
        string='Inicio Sugerido',
        help='Fecha y hora sugerida para iniciar producción'
    )
    
    suggested_end_date = fields.Datetime(
        string='Fin Sugerido',
        compute='_compute_suggested_end_date',
        store=True,
        help='Fecha estimada de finalización'
    )
    
    production_id = fields.Many2one(
        'mrp.production',
        string='Orden de Producción',
        help='Orden de producción generada'
    )
    
    workcenter_id = fields.Many2one(
        'mrp.workcenter', 
        string='Centro de Trabajo Asignado',
        help='Centro de trabajo donde se producirá'
    )
    
    notes = fields.Text(
        string='Notas',
        help='Observaciones sobre esta línea del plan'
    )
    
    @api.depends('suggested_start_date', 'estimated_hours')
    def _compute_suggested_end_date(self):
        """Calcular fecha estimada de finalización"""
        for line in self:
            if line.suggested_start_date and line.estimated_hours:
                line.suggested_end_date = line.suggested_start_date + timedelta(hours=line.estimated_hours)
            else:
                line.suggested_end_date = line.suggested_start_date