# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class PurchasePlanning(models.Model):
    _name = 'megastock.purchase.planning'
    _description = 'Planificación Automática de Compras BOM'
    _order = 'planned_date desc, priority desc'
    
    name = fields.Char(
        string='Nombre',
        required=True,
        default=lambda self: self._get_default_name(),
        help='Nombre de la planificación'
    )
    
    bom_id = fields.Many2one(
        'mrp.bom',
        string='BOM Base',
        required=True,
        help='BOM que genera esta planificación'
    )
    
    product_tmpl_id = fields.Many2one(
        'product.template',
        related='bom_id.product_tmpl_id',
        string='Producto',
        store=True
    )
    
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('calculated', 'Calculado'),
        ('approved', 'Aprobado'),
        ('purchased', 'Comprado'),
        ('cancelled', 'Cancelado')
    ], string='Estado', default='draft', required=True)
    
    planning_type = fields.Selection([
        ('manual', 'Manual'),
        ('automatic', 'Automático'),
        ('forecast_based', 'Basado en Pronóstico'),
        ('reorder_point', 'Punto de Reorden'),
        ('production_plan', 'Plan de Producción')
    ], string='Tipo Planificación', default='automatic', required=True)
    
    # Parámetros de planificación
    production_quantity = fields.Float(
        string='Cantidad a Producir',
        required=True,
        help='Cantidad de producto final planificada'
    )
    
    planned_date = fields.Date(
        string='Fecha Planificada',
        default=fields.Date.today,
        required=True,
        help='Fecha objetivo para tener materiales disponibles'
    )
    
    lead_time_days = fields.Integer(
        string='Días Lead Time',
        default=15,
        help='Días de anticipación para compras'
    )
    
    safety_stock_days = fields.Integer(
        string='Días Stock Seguridad',
        default=7,
        help='Días adicionales de stock de seguridad'
    )
    
    priority = fields.Selection([
        ('low', 'Baja'),
        ('medium', 'Media'),
        ('high', 'Alta'),
        ('urgent', 'Urgente')
    ], string='Prioridad', default='medium')
    
    # Análisis de necesidades
    total_estimated_cost = fields.Float(
        string='Costo Total Estimado',
        compute='_compute_total_cost',
        store=True,
        help='Costo total de materiales necesarios'
    )
    
    materials_needed_count = fields.Integer(
        string='Materiales Requeridos',
        compute='_compute_materials_count',
        help='Número de materiales diferentes necesarios'
    )
    
    urgent_materials_count = fields.Integer(
        string='Materiales Urgentes',
        compute='_compute_urgent_count',
        help='Materiales con stock insuficiente'
    )
    
    # Líneas de planificación
    planning_line_ids = fields.One2many(
        'megastock.purchase.planning.line',
        'planning_id',
        string='Líneas de Planificación',
        help='Detalle de materiales y cantidades necesarias'
    )
    
    # Órdenes de compra generadas
    purchase_order_ids = fields.One2many(
        'purchase.order',
        'planning_id',
        string='Órdenes de Compra',
        help='Órdenes de compra generadas desde esta planificación'
    )
    
    # Configuración automática
    auto_generate_po = fields.Boolean(
        string='Generar OC Automáticamente',
        default=False,
        help='Generar órdenes de compra automáticamente'
    )
    
    consolidate_suppliers = fields.Boolean(
        string='Consolidar por Proveedor',
        default=True,
        help='Agrupar materiales por proveedor en OC'
    )
    
    # Campos de análisis
    completion_percentage = fields.Float(
        string='% Completado',
        compute='_compute_completion',
        help='Porcentaje de materiales ya comprados'
    )
    
    total_savings = fields.Float(
        string='Ahorros Totales',
        compute='_compute_savings',
        help='Ahorros obtenidos por optimizaciones'
    )
    
    last_calculation_date = fields.Datetime(
        string='Última Actualización',
        readonly=True
    )
    
    notes = fields.Text(
        string='Notas',
        help='Observaciones sobre la planificación'
    )
    
    def _get_default_name(self):
        """Generar nombre por defecto"""
        return f"Plan Compras {datetime.now().strftime('%Y%m%d-%H%M')}"
    
    @api.depends('planning_line_ids', 'planning_line_ids.total_cost')
    def _compute_total_cost(self):
        """Calcular costo total estimado"""
        for planning in self:
            planning.total_estimated_cost = sum(
                planning.planning_line_ids.mapped('total_cost')
            )
    
    @api.depends('planning_line_ids')
    def _compute_materials_count(self):
        """Contar materiales diferentes"""
        for planning in self:
            planning.materials_needed_count = len(planning.planning_line_ids)
    
    @api.depends('planning_line_ids', 'planning_line_ids.is_urgent')
    def _compute_urgent_count(self):
        """Contar materiales urgentes"""
        for planning in self:
            planning.urgent_materials_count = len(
                planning.planning_line_ids.filtered('is_urgent')
            )
    
    @api.depends('planning_line_ids', 'planning_line_ids.purchased_qty', 'planning_line_ids.required_qty')
    def _compute_completion(self):
        """Calcular porcentaje de completado"""
        for planning in self:
            total_required = sum(planning.planning_line_ids.mapped('required_qty'))
            total_purchased = sum(planning.planning_line_ids.mapped('purchased_qty'))
            
            if total_required > 0:
                planning.completion_percentage = (total_purchased / total_required) * 100
            else:
                planning.completion_percentage = 0.0
    
    @api.depends('planning_line_ids', 'planning_line_ids.savings_amount')
    def _compute_savings(self):
        """Calcular ahorros totales"""
        for planning in self:
            planning.total_savings = sum(
                planning.planning_line_ids.mapped('savings_amount')
            )
    
    def action_calculate_requirements(self):
        """Calcular requerimientos de materiales"""
        self.ensure_one()
        
        # Limpiar líneas existentes
        self.planning_line_ids.unlink()
        
        # Calcular necesidades basadas en BOM
        requirements = self._calculate_material_requirements()
        
        # Crear líneas de planificación
        for material_id, requirement in requirements.items():
            self.env['megastock.purchase.planning.line'].create({
                'planning_id': self.id,
                'product_id': material_id,
                'required_qty': requirement['quantity'],
                'current_stock': requirement['current_stock'],
                'unit_cost': requirement['unit_cost'],
                'preferred_supplier_id': requirement['supplier_id'],
                'minimum_qty': requirement.get('minimum_qty', 0),
                'lead_time_days': requirement.get('lead_time', self.lead_time_days),
            })
        
        self.state = 'calculated'
        self.last_calculation_date = fields.Datetime.now()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Requerimientos Calculados',
                'message': f'Se calcularon {len(requirements)} materiales necesarios.',
                'type': 'success',
            }
        }
    
    def _calculate_material_requirements(self):
        """Calcular requerimientos de materiales desde BOM"""
        requirements = {}
        
        # Recorrer líneas del BOM
        for bom_line in self.bom_id.bom_line_ids:
            material = bom_line.product_id
            
            # Calcular cantidad necesaria
            base_qty = bom_line.product_qty
            production_factor = self.production_quantity / self.bom_id.product_qty
            required_qty = base_qty * production_factor
            
            # Agregar stock de seguridad
            if self.safety_stock_days > 0:
                daily_consumption = self._calculate_daily_consumption(material)
                safety_qty = daily_consumption * self.safety_stock_days
                required_qty += safety_qty
            
            # Obtener stock actual
            current_stock = material.qty_available
            
            # Calcular cantidad a comprar
            qty_to_purchase = max(0, required_qty - current_stock)
            
            if qty_to_purchase > 0:
                # Obtener proveedor preferido
                supplier = material.seller_ids.filtered('is_company')[:1]
                
                requirements[material.id] = {
                    'quantity': qty_to_purchase,
                    'current_stock': current_stock,
                    'unit_cost': material.standard_price,
                    'supplier_id': supplier.id if supplier else False,
                    'minimum_qty': supplier.min_qty if supplier else 0,
                    'lead_time': supplier.delay if supplier else self.lead_time_days,
                }
        
        return requirements
    
    def _calculate_daily_consumption(self, material):
        """Calcular consumo diario promedio del material"""
        # Buscar movimientos de los últimos 60 días
        sixty_days_ago = datetime.now() - timedelta(days=60)
        
        stock_moves = self.env['stock.move'].search([
            ('product_id', '=', material.id),
            ('state', '=', 'done'),
            ('date', '>=', sixty_days_ago),
            ('location_id.usage', '=', 'internal'),
            ('location_dest_id.usage', '!=', 'internal')
        ])
        
        total_consumed = sum(stock_moves.mapped('product_uom_qty'))
        return total_consumed / 60 if total_consumed > 0 else 0
    
    def action_optimize_purchases(self):
        """Optimizar compras usando algoritmos inteligentes"""
        self.ensure_one()
        
        optimizations_applied = 0
        
        for line in self.planning_line_ids:
            # Optimizar cantidad por lotes económicos
            optimized_qty = self._calculate_economic_order_quantity(line)
            if optimized_qty != line.required_qty:
                line.required_qty = optimized_qty
                optimizations_applied += 1
            
            # Buscar descuentos por volumen
            volume_discount = self._check_volume_discounts(line)
            if volume_discount:
                line.savings_amount = volume_discount['savings']
                line.notes = f"Descuento por volumen: {volume_discount['percentage']}%"
                optimizations_applied += 1
            
            # Evaluar proveedores alternativos
            alternative_supplier = self._find_better_supplier(line)
            if alternative_supplier:
                line.preferred_supplier_id = alternative_supplier['supplier_id']
                line.unit_cost = alternative_supplier['unit_cost']
                line.savings_amount += alternative_supplier['savings']
                optimizations_applied += 1
        
        _logger.info(f"Planificación {self.name}: {optimizations_applied} optimizaciones aplicadas")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Optimización Completada',
                'message': f'Se aplicaron {optimizations_applied} optimizaciones.',
                'type': 'success',
            }
        }
    
    def _calculate_economic_order_quantity(self, line):
        """Calcular cantidad económica de pedido (EOQ)"""
        # Fórmula EOQ simplificada
        annual_demand = line.required_qty * 12  # Aproximación anual
        ordering_cost = 50.0  # Costo fijo por pedido
        holding_cost = line.unit_cost * 0.2  # 20% costo anual mantenimiento
        
        if holding_cost > 0:
            eoq = (2 * annual_demand * ordering_cost / holding_cost) ** 0.5
            return max(line.required_qty, eoq)
        
        return line.required_qty
    
    def _check_volume_discounts(self, line):
        """Verificar descuentos por volumen disponibles"""
        # Buscar info del proveedor sobre descuentos
        if line.preferred_supplier_id:
            supplier_info = line.product_id.seller_ids.filtered(
                lambda s: s.name == line.preferred_supplier_id
            )[:1]
            
            if supplier_info:
                # Simular descuentos por volumen (en implementación real vendría de configuración)
                if line.required_qty >= 1000:
                    return {
                        'percentage': 8.0,
                        'savings': line.required_qty * line.unit_cost * 0.08
                    }
                elif line.required_qty >= 500:
                    return {
                        'percentage': 5.0,
                        'savings': line.required_qty * line.unit_cost * 0.05
                    }
        
        return None
    
    def _find_better_supplier(self, line):
        """Buscar proveedor alternativo con mejor precio"""
        alternative_suppliers = line.product_id.seller_ids.filtered(
            lambda s: s.name != line.preferred_supplier_id and s.name.is_company
        )
        
        best_supplier = None
        best_savings = 0
        
        for supplier in alternative_suppliers:
            if supplier.price < line.unit_cost:
                savings = (line.unit_cost - supplier.price) * line.required_qty
                if savings > best_savings:
                    best_savings = savings
                    best_supplier = {
                        'supplier_id': supplier.name.id,
                        'unit_cost': supplier.price,
                        'savings': savings
                    }
        
        return best_supplier
    
    def action_generate_purchase_orders(self):
        """Generar órdenes de compra automáticamente"""
        self.ensure_one()
        
        if self.state != 'calculated':
            raise UserError("Debe calcular requerimientos antes de generar órdenes de compra.")
        
        # Agrupar por proveedor si está configurado
        if self.consolidate_suppliers:
            supplier_groups = {}
            for line in self.planning_line_ids.filtered('required_qty'):
                supplier_id = line.preferred_supplier_id.id
                if supplier_id not in supplier_groups:
                    supplier_groups[supplier_id] = []
                supplier_groups[supplier_id].append(line)
        else:
            # Una OC por material
            supplier_groups = {line.id: [line] for line in self.planning_line_ids.filtered('required_qty')}
        
        purchase_orders_created = 0
        
        for supplier_id, lines in supplier_groups.items():
            # Crear orden de compra
            po_vals = self._prepare_purchase_order_vals(supplier_id, lines)
            
            po = self.env['purchase.order'].create(po_vals)
            
            # Crear líneas de la orden
            for line in lines:
                po_line_vals = self._prepare_purchase_order_line_vals(line, po.id)
                self.env['purchase.order.line'].create(po_line_vals)
            
            purchase_orders_created += 1
            _logger.info(f"Orden de compra {po.name} creada para planificación {self.name}")
        
        self.state = 'approved'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Órdenes Generadas',
                'message': f'Se generaron {purchase_orders_created} órdenes de compra.',
                'type': 'success',
            }
        }
    
    def _prepare_purchase_order_vals(self, supplier_id, lines):
        """Preparar valores para orden de compra"""
        supplier = self.env['res.partner'].browse(supplier_id) if supplier_id else self.env['res.partner']
        
        return {
            'partner_id': supplier.id if supplier else False,
            'planning_id': self.id,
            'origin': f'Plan: {self.name}',
            'date_order': fields.Datetime.now(),
            'date_planned': self.planned_date,
            'company_id': self.env.company.id,
        }
    
    def _prepare_purchase_order_line_vals(self, planning_line, po_id):
        """Preparar valores para línea de orden de compra"""
        return {
            'order_id': po_id,
            'product_id': planning_line.product_id.id,
            'product_qty': planning_line.required_qty,
            'price_unit': planning_line.unit_cost,
            'date_planned': self.planned_date,
            'product_uom': planning_line.product_id.uom_po_id.id,
        }
    
    def action_view_purchase_orders(self):
        """Ver órdenes de compra generadas"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Órdenes de Compra',
            'res_model': 'purchase.order',
            'view_mode': 'tree,form',
            'domain': [('planning_id', '=', self.id)],
            'context': {'default_planning_id': self.id}
        }
    
    @api.model
    def auto_generate_planning_from_forecast(self):
        """Generar planificación automática basada en pronósticos"""
        # Buscar BOM inteligentes con auto-planificación activada
        intelligent_boms = self.env['mrp.bom'].search([
            ('is_intelligent', '=', True),
            ('active', '=', True)
        ])
        
        plannings_created = 0
        
        for bom in intelligent_boms:
            # Verificar si ya existe planificación reciente
            existing_planning = self.search([
                ('bom_id', '=', bom.id),
                ('state', 'in', ['draft', 'calculated', 'approved']),
                ('create_date', '>=', fields.Date.today() - timedelta(days=7))
            ], limit=1)
            
            if not existing_planning:
                # Calcular cantidad basada en pronóstico (simplificado)
                forecast_qty = self._calculate_forecast_quantity(bom)
                
                if forecast_qty > 0:
                    planning = self.create({
                        'name': f'Auto-Plan {bom.product_tmpl_id.name} {fields.Date.today()}',
                        'bom_id': bom.id,
                        'planning_type': 'forecast_based',
                        'production_quantity': forecast_qty,
                        'planned_date': fields.Date.today() + timedelta(days=30),
                        'auto_generate_po': True,
                        'consolidate_suppliers': True
                    })
                    
                    # Calcular requerimientos automáticamente
                    planning.action_calculate_requirements()
                    plannings_created += 1
        
        _logger.info(f"Generadas {plannings_created} planificaciones automáticas")
        return plannings_created
    
    def _calculate_forecast_quantity(self, bom):
        """Calcular cantidad de pronóstico simplificada"""
        # Buscar producciones recientes para estimar demanda
        recent_productions = self.env['mrp.production'].search([
            ('bom_id', '=', bom.id),
            ('date_planned_start', '>=', fields.Date.today() - timedelta(days=90)),
            ('state', '=', 'done')
        ])
        
        if recent_productions:
            total_produced = sum(recent_productions.mapped('product_qty'))
            avg_monthly = total_produced / 3  # Promedio mensual
            return avg_monthly * 1.2  # 20% adicional para crecimiento
        
        return 0


class PurchasePlanningLine(models.Model):
    _name = 'megastock.purchase.planning.line'
    _description = 'Línea de Planificación de Compras'
    _order = 'is_urgent desc, required_date'
    
    planning_id = fields.Many2one(
        'megastock.purchase.planning',
        string='Planificación',
        required=True,
        ondelete='cascade'
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Material',
        required=True,
        help='Material a comprar'
    )
    
    required_qty = fields.Float(
        string='Cantidad Requerida',
        required=True,
        help='Cantidad total necesaria'
    )
    
    current_stock = fields.Float(
        string='Stock Actual',
        help='Stock disponible actualmente'
    )
    
    qty_to_purchase = fields.Float(
        string='Cantidad a Comprar',
        compute='_compute_qty_to_purchase',
        store=True,
        help='Cantidad que debe comprarse'
    )
    
    purchased_qty = fields.Float(
        string='Cantidad Comprada',
        default=0.0,
        help='Cantidad ya comprada/ordenada'
    )
    
    unit_cost = fields.Float(
        string='Costo Unitario',
        required=True,
        help='Costo unitario estimado'
    )
    
    total_cost = fields.Float(
        string='Costo Total',
        compute='_compute_total_cost',
        store=True,
        help='Costo total de la línea'
    )
    
    preferred_supplier_id = fields.Many2one(
        'res.partner',
        string='Proveedor Preferido',
        help='Proveedor sugerido para esta compra'
    )
    
    minimum_qty = fields.Float(
        string='Cantidad Mínima',
        default=0.0,
        help='Cantidad mínima de compra del proveedor'
    )
    
    lead_time_days = fields.Integer(
        string='Días Lead Time',
        default=15,
        help='Días de entrega del proveedor'
    )
    
    required_date = fields.Date(
        string='Fecha Requerida',
        compute='_compute_required_date',
        store=True,
        help='Fecha en que se necesita el material'
    )
    
    is_urgent = fields.Boolean(
        string='Urgente',
        compute='_compute_is_urgent',
        store=True,
        help='Material con necesidad urgente'
    )
    
    savings_amount = fields.Float(
        string='Ahorros',
        default=0.0,
        help='Ahorros obtenidos por optimizaciones'
    )
    
    notes = fields.Text(
        string='Notas',
        help='Observaciones sobre esta línea'
    )
    
    purchase_order_line_ids = fields.One2many(
        'purchase.order.line',
        'planning_line_id',
        string='Líneas OC',
        help='Líneas de órdenes de compra relacionadas'
    )
    
    @api.depends('required_qty', 'current_stock')
    def _compute_qty_to_purchase(self):
        """Calcular cantidad a comprar"""
        for line in self:
            line.qty_to_purchase = max(0, line.required_qty - line.current_stock)
    
    @api.depends('qty_to_purchase', 'unit_cost')
    def _compute_total_cost(self):
        """Calcular costo total"""
        for line in self:
            line.total_cost = line.qty_to_purchase * line.unit_cost
    
    @api.depends('planning_id.planned_date', 'lead_time_days')
    def _compute_required_date(self):
        """Calcular fecha requerida"""
        for line in self:
            if line.planning_id.planned_date and line.lead_time_days:
                line.required_date = line.planning_id.planned_date - timedelta(days=line.lead_time_days)
            else:
                line.required_date = fields.Date.today()
    
    @api.depends('current_stock', 'required_qty', 'required_date')
    def _compute_is_urgent(self):
        """Determinar si es urgente"""
        for line in self:
            # Urgente si stock insuficiente y fecha próxima
            stock_insufficient = line.current_stock < line.required_qty * 0.5
            date_near = line.required_date and line.required_date <= fields.Date.today() + timedelta(days=7)
            line.is_urgent = stock_insufficient and date_near


# Extensión al modelo purchase.order para vincular con planificación
class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    planning_id = fields.Many2one(
        'megastock.purchase.planning',
        string='Planificación Origen',
        help='Planificación que generó esta orden de compra'
    )


# Extensión al modelo purchase.order.line para vincular con línea de planificación  
class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'
    
    planning_line_id = fields.Many2one(
        'megastock.purchase.planning.line',
        string='Línea Planificación',
        help='Línea de planificación que generó esta línea de compra'
    )