# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    # Campos adicionales para MEGASTOCK
    material_category = fields.Selection([
        ('papers', 'Papeles'),
        ('inks', 'Tintas'),
        ('adhesives', 'Adhesivos'),
        ('others', 'Otros'),
    ], string='Categoría de Materiales', compute='_compute_material_category', store=True)
    
    quality_inspection_required = fields.Boolean(
        string='Requiere Inspección de Calidad',
        default=True,
        help='Indica si los materiales requieren inspección antes de ser aprobados'
    )
    
    @api.depends('order_line.product_id')
    def _compute_material_category(self):
        """Determinar categoría principal de materiales"""
        for order in self:
            categories = []
            for line in order.order_line:
                if line.product_id.megastock_category == 'materias_primas':
                    if 'kraft' in line.product_id.name.lower() or 'medium' in line.product_id.name.lower() or 'liner' in line.product_id.name.lower():
                        categories.append('papers')
                    elif 'tinta' in line.product_id.name.lower():
                        categories.append('inks')
                    elif any(word in line.product_id.name.lower() for word in ['almidon', 'pva', 'adhesiv']):
                        categories.append('adhesives')
                    else:
                        categories.append('others')
            
            # Tomar la categoría más común
            if categories:
                order.material_category = max(set(categories), key=categories.count)
            else:
                order.material_category = 'others'
    
    def button_confirm(self):
        """Override para configurar ubicaciones específicas"""
        result = super().button_confirm()
        
        # Configurar ubicaciones de destino según el tipo de material
        for picking in self.picking_ids:
            for move in picking.move_ids:
                dest_location = self._get_material_location(move.product_id)
                if dest_location:
                    move.location_dest_id = dest_location.id
        
        return result
    
    def _get_material_location(self, product):
        """Obtener ubicación específica según el tipo de material"""
        if product.megastock_category == 'materias_primas':
            if product.material_type == 'kraft':
                return self.env.ref('megastock_inventory_clean.stock_location_kraft', False)
            elif 'medium' in product.name.lower():
                return self.env.ref('megastock_inventory_clean.stock_location_medium', False)
            elif 'liner' in product.name.lower():
                return self.env.ref('megastock_inventory_clean.stock_location_liner', False)
            elif 'tinta' in product.name.lower():
                return self.env.ref('megastock_inventory_clean.stock_location_inks_cmyk', False)
            elif any(word in product.name.lower() for word in ['almidon', 'pva', 'adhesiv']):
                return self.env.ref('megastock_inventory_clean.stock_location_adhesives', False)
        
        return False


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'
    
    # Información adicional de la línea
    expected_quality = fields.Selection([
        ('standard', 'Estándar'),
        ('premium', 'Premium'),
        ('custom', 'Personalizado'),
    ], string='Calidad Esperada', default='standard')
    
    technical_specs = fields.Text(
        string='Especificaciones Técnicas',
        help='Especificaciones técnicas requeridas para este material'
    )
    
    @api.onchange('product_id')
    def _onchange_product_megastock(self):
        """Autocompletar especificaciones técnicas"""
        if self.product_id and self.product_id.megastock_category == 'materias_primas':
            specs = []
            
            if self.product_id.gramaje:
                specs.append(f"Gramaje: {self.product_id.gramaje} g/m²")
            
            if self.product_id.material_type:
                specs.append(f"Material: {self.product_id.material_type.upper()}")
            
            if specs:
                self.technical_specs = "\n".join(specs)