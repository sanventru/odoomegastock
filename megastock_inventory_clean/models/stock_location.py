# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class StockLocation(models.Model):
    _inherit = 'stock.location'
    
    # Campos adicionales para MEGASTOCK
    megastock_location_type = fields.Selection([
        ('raw_materials', 'Materias Primas'),
        ('wip', 'Productos en Proceso'),
        ('finished_goods', 'Productos Terminados'),
        ('quality_control', 'Control de Calidad'),
        ('quarantine', 'Cuarentena'),
        ('scrap', 'Desperdicios'),
    ], string='Tipo de Ubicación MEGASTOCK')
    
    material_category = fields.Selection([
        ('papers', 'Papeles'),
        ('inks', 'Tintas'),
        ('adhesives', 'Adhesivos'),
        ('others', 'Otros'),
    ], string='Categoría de Material')
    
    temperature_controlled = fields.Boolean(
        string='Control de Temperatura',
        help='Ubicación requiere control de temperatura'
    )
    
    humidity_controlled = fields.Boolean(
        string='Control de Humedad',
        help='Ubicación requiere control de humedad'
    )
    
    max_capacity_tons = fields.Float(
        string='Capacidad Máxima (Ton)',
        help='Capacidad máxima en toneladas'
    )
    
    current_utilization = fields.Float(
        string='Utilización Actual (%)',
        compute='_compute_current_utilization',
        help='Porcentaje de utilización actual'
    )
    
    @api.depends('quant_ids', 'max_capacity_tons')
    def _compute_current_utilization(self):
        """Calcular utilización actual de la ubicación"""
        for location in self:
            if not location.max_capacity_tons:
                location.current_utilization = 0.0
                continue
            
            # Calcular peso total en la ubicación
            total_weight = 0.0
            for quant in location.quant_ids:
                # Estimar peso basado en UOM
                if quant.product_uom_id.category_id.name == 'Weight':
                    if 'ton' in quant.product_uom_id.name.lower():
                        total_weight += quant.quantity
                    elif 'kg' in quant.product_uom_id.name.lower():
                        total_weight += quant.quantity / 1000.0
            
            location.current_utilization = (total_weight / location.max_capacity_tons) * 100.0
    
    def action_view_stock_details(self):
        """Acción para ver detalles del stock en esta ubicación"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'Stock en {self.name}',
            'res_model': 'stock.quant',
            'view_mode': 'tree,form',
            'domain': [('location_id', '=', self.id)],
            'context': {'default_location_id': self.id}
        }