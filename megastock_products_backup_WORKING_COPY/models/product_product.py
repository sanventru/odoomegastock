# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    # Heredar campos del template
    megastock_code = fields.Char(related='product_tmpl_id.megastock_code', store=True, readonly=True)
    megastock_category = fields.Selection(related='product_tmpl_id.megastock_category', readonly=True)
    technical_description = fields.Text(related='product_tmpl_id.technical_description', readonly=True)
    
    # Código específico de variante
    variant_code = fields.Char(
        string='Código Variante',
        compute='_compute_variant_code',
        store=True,
        help='Código específico de esta variante basado en atributos'
    )
    
    @api.depends('product_template_attribute_value_ids', 'megastock_code')
    def _compute_variant_code(self):
        """Genera código específico de variante basado en atributos"""
        for record in self:
            base_code = record.megastock_code
            if not base_code:
                record.variant_code = ""
                continue
            
            # Obtener valores de atributos ordenados
            attribute_values = []
            for ptav in record.product_template_attribute_value_ids.sorted('attribute_id'):
                attr_name = ptav.attribute_id.name
                value = ptav.product_attribute_value_id.name
                
                # Mapeo de abreviaciones para códigos
                if 'Largo' in attr_name:
                    attribute_values.append(f"L{value}")
                elif 'Ancho' in attr_name:
                    attribute_values.append(f"A{value}")
                elif 'Alto' in attr_name:
                    attribute_values.append(f"H{value}")
                elif 'Flauta' in attr_name:
                    attribute_values.append(f"F{value}")
                elif 'Test' in attr_name:
                    attribute_values.append(f"T{value}")
                elif 'Material' in attr_name:
                    attribute_values.append(f"M{value[:3]}")
                elif 'Color' in attr_name:
                    if 'Sin' in value:
                        attribute_values.append("C0")
                    else:
                        attribute_values.append(f"C{value[0]}")
                elif 'Gramaje' in attr_name:
                    attribute_values.append(f"G{value}")
                else:
                    attribute_values.append(value[:2])
            
            # Generar código de variante
            if attribute_values:
                variant_suffix = "-" + "-".join(attribute_values)
                record.variant_code = base_code + variant_suffix
            else:
                record.variant_code = base_code
    
    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        """Búsqueda extendida por código MEGASTOCK y código de variante"""
        args = args or []
        
        if name and operator in ('=', 'ilike', '=ilike', 'like', '=like'):
            # Buscar por código MEGASTOCK exacto
            products = self.search([('megastock_code', '=', name)] + args, limit=limit)
            if products:
                return products.name_get()
            
            # Buscar por código de variante exacto
            products = self.search([('variant_code', '=', name)] + args, limit=limit)
            if products:
                return products.name_get()
            
            # Búsqueda por similitud
            search_domain = [
                '|', '|', '|',
                ('name', operator, name),
                ('default_code', operator, name),
                ('megastock_code', 'ilike', name),
                ('variant_code', 'ilike', name),
            ]
            products = self.search(search_domain + args, limit=limit)
            if products:
                return products.name_get()
        
        return super()._name_search(name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)
    
    def name_get(self):
        """Formato de nombre personalizado con código MEGASTOCK"""
        result = []
        for record in self:
            name = record.name
            
            # Agregar código de variante si existe
            if record.variant_code:
                name = f"[{record.variant_code}] {name}"
            elif record.megastock_code:
                name = f"[{record.megastock_code}] {name}"
            elif record.default_code:
                name = f"[{record.default_code}] {name}"
            
            # Agregar información técnica resumida
            tech_info = []
            if record.product_tmpl_id.largo_cm and record.product_tmpl_id.ancho_cm:
                tech_info.append(f"{record.product_tmpl_id.largo_cm}x{record.product_tmpl_id.ancho_cm}")
            if record.product_tmpl_id.flauta:
                tech_info.append(f"F{record.product_tmpl_id.flauta.upper()}")
            
            if tech_info:
                name += f" ({' '.join(tech_info)})"
            
            result.append((record.id, name))
        
        return result
    
    def action_generate_megastock_code(self):
        """Delegamos la generación de código al template"""
        return self.product_tmpl_id.action_generate_megastock_code()
    
    def action_update_technical_description(self):
        """Delegamos la actualización de descripción al template"""
        return self.product_tmpl_id.action_update_technical_description()
    
    @api.model
    def create(self, vals):
        """Override create para variantes"""
        product = super().create(vals)
        
        # Actualizar código de variante después de creación
        if product.product_template_attribute_value_ids:
            product._compute_variant_code()
        
        return product
    
    def copy(self, default=None):
        """Override copy para productos"""
        if default is None:
            default = {}
        
        # No copiar códigos específicos
        default.update({
            'variant_code': False,
            'megastock_code': False,  # Se generará nuevo código
        })
        
        return super().copy(default)