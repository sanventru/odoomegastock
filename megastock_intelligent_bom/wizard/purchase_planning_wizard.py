# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime, timedelta

class PurchasePlanningWizard(models.TransientModel):
    _name = 'megastock.purchase.planning.wizard'
    _description = 'Asistente de Planificación de Compras'
    
    bom_id = fields.Many2one(
        'mrp.bom',
        string='BOM',
        required=True,
        help='BOM base para planificación'
    )
    
    production_quantity = fields.Float(
        string='Cantidad a Producir',
        required=True,
        default=1000.0,
        help='Cantidad de producto final a producir'
    )
    
    planned_date = fields.Date(
        string='Fecha Objetivo',
        required=True,
        default=lambda self: fields.Date.today() + timedelta(days=30),
        help='Fecha objetivo para producción'
    )
    
    planning_type = fields.Selection([
        ('immediate', 'Necesidad Inmediata'),
        ('forecast', 'Basado en Pronóstico'),
        ('reorder', 'Punto de Reorden'),
        ('custom', 'Personalizado')
    ], string='Tipo de Planificación', default='immediate', required=True)
    
    lead_time_days = fields.Integer(
        string='Días Lead Time',
        default=15,
        help='Días de anticipación para compras'
    )
    
    safety_stock_days = fields.Integer(
        string='Stock Seguridad (días)',
        default=7,
        help='Días adicionales de stock de seguridad'
    )
    
    include_forecast = fields.Boolean(
        string='Incluir Pronóstico',
        default=False,
        help='Incluir demanda pronosticada adicional'
    )
    
    forecast_months = fields.Integer(
        string='Meses Pronóstico',
        default=3,
        help='Meses de pronóstico a considerar'
    )
    
    auto_optimize = fields.Boolean(
        string='Optimizar Automáticamente',
        default=True,
        help='Aplicar optimizaciones automáticas'
    )
    
    consolidate_suppliers = fields.Boolean(
        string='Consolidar por Proveedor',
        default=True,
        help='Agrupar materiales por proveedor'
    )
    
    auto_generate_po = fields.Boolean(
        string='Generar OC Automáticamente',
        default=False,
        help='Crear órdenes de compra automáticamente'
    )
    
    # Información calculada
    estimated_cost = fields.Float(
        string='Costo Estimado',
        readonly=True,
        help='Costo total estimado'
    )
    
    materials_count = fields.Integer(
        string='Materiales Requeridos',
        readonly=True,
        help='Número de materiales diferentes'
    )
    
    urgent_count = fields.Integer(
        string='Materiales Urgentes',
        readonly=True,
        help='Materiales con stock insuficiente'
    )
    
    @api.onchange('bom_id', 'production_quantity')
    def _onchange_estimate_cost(self):
        """Estimar costo cuando cambian parámetros"""
        if self.bom_id and self.production_quantity:
            total_cost = 0.0
            materials_count = 0
            urgent_count = 0
            
            for bom_line in self.bom_id.bom_line_ids:
                materials_count += 1
                required_qty = bom_line.product_qty * (self.production_quantity / self.bom_id.product_qty)
                line_cost = required_qty * bom_line.product_id.standard_price
                total_cost += line_cost
                
                # Verificar si es urgente (stock bajo)
                if bom_line.product_id.qty_available < required_qty:
                    urgent_count += 1
            
            self.estimated_cost = total_cost
            self.materials_count = materials_count
            self.urgent_count = urgent_count
    
    def action_create_planning(self):
        """Crear planificación de compras"""
        self.ensure_one()
        
        if not self.bom_id:
            raise UserError("Debe seleccionar un BOM válido.")
        
        if self.production_quantity <= 0:
            raise UserError("La cantidad a producir debe ser mayor a cero.")
        
        # Crear planificación
        planning_vals = {
            'name': f'Plan {self.bom_id.product_tmpl_id.name} - {self.planned_date}',
            'bom_id': self.bom_id.id,
            'production_quantity': self.production_quantity,
            'planned_date': self.planned_date,
            'planning_type': 'manual',  # Siempre manual desde wizard
            'lead_time_days': self.lead_time_days,
            'safety_stock_days': self.safety_stock_days,
            'auto_generate_po': self.auto_generate_po,
            'consolidate_suppliers': self.consolidate_suppliers,
        }
        
        planning = self.env['megastock.purchase.planning'].create(planning_vals)
        
        # Calcular requerimientos
        planning.action_calculate_requirements()
        
        # Aplicar optimizaciones si está habilitado
        if self.auto_optimize:
            planning.action_optimize_purchases()
        
        # Incluir pronóstico si está seleccionado
        if self.include_forecast:
            self._add_forecast_requirements(planning)
        
        # Generar órdenes de compra si está habilitado
        if self.auto_generate_po:
            planning.action_generate_purchase_orders()
        
        # Abrir la planificación creada
        return {
            'type': 'ir.actions.act_window',
            'name': 'Planificación de Compras',
            'res_model': 'megastock.purchase.planning',
            'res_id': planning.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def _add_forecast_requirements(self, planning):
        """Agregar requerimientos basados en pronóstico"""
        # Buscar histórico de producción
        historical_productions = self.env['mrp.production'].search([
            ('bom_id', '=', self.bom_id.id),
            ('date_planned_start', '>=', fields.Date.today() - timedelta(days=90)),
            ('state', '=', 'done')
        ])
        
        if historical_productions:
            # Calcular demanda promedio mensual
            total_produced = sum(historical_productions.mapped('product_qty'))
            avg_monthly = total_produced / 3  # Últimos 3 meses
            
            # Proyectar demanda futura
            forecast_qty = avg_monthly * self.forecast_months * 1.1  # 10% crecimiento
            
            if forecast_qty > 0:
                # Actualizar cantidad de producción
                planning.production_quantity += forecast_qty
                
                # Recalcular requerimientos
                planning.action_calculate_requirements()
                
                # Agregar nota
                planning.notes = f"Incluye pronóstico de {forecast_qty:.0f} unidades ({self.forecast_months} meses)"
    
    def action_preview_requirements(self):
        """Preview de requerimientos sin crear planificación"""
        self.ensure_one()
        
        if not self.bom_id:
            raise UserError("Debe seleccionar un BOM válido.")
        
        # Crear planificación temporal
        temp_planning = self.env['megastock.purchase.planning'].new({
            'bom_id': self.bom_id.id,
            'production_quantity': self.production_quantity,
            'planned_date': self.planned_date,
            'lead_time_days': self.lead_time_days,
            'safety_stock_days': self.safety_stock_days,
        })
        
        # Calcular requerimientos temporalmente
        requirements = temp_planning._calculate_material_requirements()
        
        # Crear vista de preview
        preview_lines = []
        total_cost = 0.0
        
        for material_id, requirement in requirements.items():
            material = self.env['product.product'].browse(material_id)
            line_cost = requirement['quantity'] * requirement['unit_cost']
            total_cost += line_cost
            
            preview_lines.append({
                'material': material.name,
                'current_stock': requirement['current_stock'],
                'required_qty': requirement['quantity'],
                'unit_cost': requirement['unit_cost'],
                'total_cost': line_cost,
                'supplier': self.env['res.partner'].browse(requirement['supplier_id']).name if requirement['supplier_id'] else 'Sin proveedor'
            })
        
        # Mostrar resumen
        message = f"""
        <h3>Preview de Requerimientos</h3>
        <p><strong>BOM:</strong> {self.bom_id.display_name}</p>
        <p><strong>Cantidad:</strong> {self.production_quantity}</p>
        <p><strong>Fecha:</strong> {self.planned_date}</p>
        <p><strong>Materiales:</strong> {len(requirements)}</p>
        <p><strong>Costo Total Estimado:</strong> ${total_cost:,.2f}</p>
        
        <table class='table table-striped'>
            <thead>
                <tr>
                    <th>Material</th>
                    <th>Stock Actual</th>
                    <th>Cantidad Requerida</th>
                    <th>Costo Unit.</th>
                    <th>Costo Total</th>
                    <th>Proveedor</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for line in preview_lines:
            message += f"""
                <tr>
                    <td>{line['material']}</td>
                    <td>{line['current_stock']:.2f}</td>
                    <td>{line['required_qty']:.2f}</td>
                    <td>${line['unit_cost']:.2f}</td>
                    <td>${line['total_cost']:.2f}</td>
                    <td>{line['supplier']}</td>
                </tr>
            """
        
        message += """
            </tbody>
        </table>
        """
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Preview Requerimientos',
                'message': message,
                'type': 'info',
                'sticky': True,
            }
        }
    
    def action_quick_planning(self):
        """Planificación rápida con valores por defecto"""
        self.ensure_one()
        
        # Configurar valores por defecto optimizados
        self.planning_type = 'immediate'
        self.lead_time_days = 10
        self.safety_stock_days = 5
        self.auto_optimize = True
        self.consolidate_suppliers = True
        
        # Crear planificación
        return self.action_create_planning()