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
            base_code = record.megastock_code or record.product_tmpl_id.megastock_code
            if not base_code:
                record.variant_code = ""
                continue
            
            # Obtener valores de atributos ordenados
            attribute_values = []
            for ptav in record.product_template_attribute_value_ids.sorted('attribute_id'):
                # Crear sufijo basado en el tipo de atributo
                attr_name = ptav.attribute_id.name.lower()
                value = ptav.name
                
                if 'largo' in attr_name:
                    attribute_values.append(f"L{value}")
                elif 'ancho' in attr_name:
                    attribute_values.append(f"A{value}")
                elif 'alto' in attr_name:
                    attribute_values.append(f"H{value}")
                elif 'ceja' in attr_name:
                    attribute_values.append(f"C{value}")
                elif 'flauta' in attr_name:
                    attribute_values.append(f"F{value}")
                elif 'test' in attr_name:
                    attribute_values.append(f"T{value}")
                elif 'gramaje' in attr_name:
                    attribute_values.append(f"G{value}")
                elif 'material' in attr_name:
                    # Usar primeras 2 letras del material
                    material_codes = {
                        'KRAFT': 'KR',
                        'INTERSTOCK': 'IN',
                        'MONUS': 'MO',
                        'WESTROCK': 'WR'
                    }
                    attribute_values.append(material_codes.get(value, value[:2]))
                elif 'color' in attr_name:
                    if 'sin' in value.lower():
                        attribute_values.append("0C")
                    elif 'cmyk' in value.lower():
                        attribute_values.append("4C")
                    else:
                        color_num = ''.join(filter(str.isdigit, value))
                        if color_num:
                            attribute_values.append(f"{color_num}C")
            
            # Construir código de variante
            if attribute_values:
                suffix = "-" + "-".join(attribute_values)
                record.variant_code = base_code + suffix
            else:
                record.variant_code = base_code
    
    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """Mejorar búsqueda para incluir códigos MEGASTOCK"""
        if args is None:
            args = []
        
        # Búsqueda por código MEGASTOCK
        if name:
            # Buscar por código exacto
            products = self.search([('megastock_code', '=', name)] + args, limit=limit)
            if products:
                return products.name_get()
            
            # Buscar por código de variante
            products = self.search([('variant_code', '=', name)] + args, limit=limit)
            if products:
                return products.name_get()
            
            # Buscar por código que contenga el término
            products = self.search([
                '|', '|',
                ('megastock_code', 'ilike', name),
                ('variant_code', 'ilike', name),
                ('default_code', 'ilike', name)
            ] + args, limit=limit)
            if products:
                return products.name_get()
        
        return super().name_search(name=name, args=args, operator=operator, limit=limit)
    
    def name_get(self):
        """Personalizar nombre mostrado"""
        result = []
        for record in self:
            name = record.name
            
            # Incluir código MEGASTOCK si existe
            if record.variant_code:
                name = f"[{record.variant_code}] {name}"
            elif record.megastock_code:
                name = f"[{record.megastock_code}] {name}"
            
            # Agregar información técnica resumida si existe
            if record.technical_description:
                # Extraer dimensiones de la descripción técnica
                desc_lines = record.technical_description.split('\n')
                for line in desc_lines:
                    if 'Dimensiones:' in line:
                        dimensions = line.replace('Dimensiones: ', '').replace(' cm', '')
                        name += f" ({dimensions})"
                        break
            
            result.append((record.id, name))
        
        return result
    
    def action_generate_megastock_code(self):
        """Generar código MEGASTOCK para el template de este producto"""
        self.ensure_one()
        return self.product_tmpl_id.action_generate_megastock_code()
    
    def action_update_technical_description(self):
        """Actualizar descripción técnica para el template de este producto"""
        self.ensure_one()
        return self.product_tmpl_id.action_update_technical_description()
    
    def action_duplicate_with_variants(self):
        """Acción para duplicar producto con todas sus variantes"""
        self.ensure_one()
        
        # Duplicar template
        new_template = self.product_tmpl_id.copy({
            'name': f"{self.product_tmpl_id.name} (Copia)",
            'megastock_code': False,  # Se generará nuevo código
            'default_code': False,
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'product.template',
            'res_id': new_template.id,
            'view_mode': 'form',
            'target': 'current',
        }