# -*- coding: utf-8 -*-

from odoo import models, fields, api


class MrpBom(models.Model):
    _inherit = 'mrp.bom'
    
    # Campos inteligentes básicos
    is_megastock_intelligent = fields.Boolean(
        string='BOM Inteligente MEGASTOCK',
        default=False,
        help='Habilita cálculos automáticos basados en dimensiones del producto'
    )
    
    auto_calculate = fields.Boolean(
        string='Cálculo Automático',
        default=True,
        help='Recalcular cantidades automáticamente cuando cambien las especificaciones'
    )
    
    # Campos de análisis
    estimated_material_cost = fields.Float(
        string='Costo Estimado Material',
        compute='_compute_material_costs',
        store=True,
        help='Costo total estimado de materiales'
    )
    
    surface_area_m2 = fields.Float(
        string='Área Superficie (m²)',
        compute='_compute_surface_area',
        store=True,
        help='Área de superficie calculada automáticamente'
    )
    
    waste_percentage = fields.Float(
        string='Porcentaje Merma (%)',
        default=5.0,
        help='Porcentaje de merma aplicado a los cálculos'
    )
    
    last_auto_update = fields.Datetime(
        string='Última Actualización',
        readonly=True,
        help='Fecha de última actualización automática'
    )
    
    @api.depends('product_tmpl_id.largo_cm', 'product_tmpl_id.ancho_cm', 'product_tmpl_id.alto_cm')
    def _compute_surface_area(self):
        """Calcular área de superficie basada en dimensiones del producto"""
        for record in self:
            if record.product_tmpl_id and record.is_megastock_intelligent:
                largo = record.product_tmpl_id.largo_cm or 0
                ancho = record.product_tmpl_id.ancho_cm or 0
                alto = record.product_tmpl_id.alto_cm or 0
                
                if largo and ancho:
                    if alto:  # Caja 3D
                        # Área de desarrollo de caja
                        area_mm2 = ((largo + ancho) * 2 + 20) * ((ancho + alto) * 2 + 20)
                        record.surface_area_m2 = area_mm2 / 1000000.0
                    else:  # Lámina 2D
                        area_mm2 = largo * ancho
                        record.surface_area_m2 = area_mm2 / 1000000.0
                else:
                    record.surface_area_m2 = 0.0
            else:
                record.surface_area_m2 = 0.0
    
    @api.depends('bom_line_ids.product_qty', 'bom_line_ids.product_id.standard_price')
    def _compute_material_costs(self):
        """Calcular costo total de materiales"""
        for record in self:
            total_cost = 0.0
            for line in record.bom_line_ids:
                if line.product_id.standard_price:
                    total_cost += line.product_qty * line.product_id.standard_price
            
            # Aplicar merma
            if record.waste_percentage > 0:
                total_cost *= (1 + record.waste_percentage / 100.0)
            
            record.estimated_material_cost = total_cost
    
    def action_update_intelligent_quantities(self):
        """Actualizar cantidades basadas en dimensiones"""
        if not self.is_megastock_intelligent:
            return
        
        for line in self.bom_line_ids:
            # Lógica simple para materiales comunes
            if 'papel' in line.product_id.name.lower() or 'carton' in line.product_id.name.lower():
                # Calcular por área
                if self.surface_area_m2 > 0:
                    line.product_qty = self.surface_area_m2 * self.product_qty
            
            elif 'adhesivo' in line.product_id.name.lower():
                # 8g por m²
                if self.surface_area_m2 > 0:
                    line.product_qty = self.surface_area_m2 * 0.008 * self.product_qty
            
            elif 'tinta' in line.product_id.name.lower():
                # 15g por m² con 30% cobertura
                if self.surface_area_m2 > 0:
                    line.product_qty = self.surface_area_m2 * 0.015 * 0.3 * self.product_qty
        
        self.last_auto_update = fields.Datetime.now()
        return True