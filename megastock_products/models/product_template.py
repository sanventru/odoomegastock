# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    # Campos adicionales MEGASTOCK
    megastock_code = fields.Char(
        string='Código MEGASTOCK',
        copy=False,
        help='Código interno MEGASTOCK generado automáticamente'
    )
    
    megastock_category = fields.Selection([
        ('cajas', 'CAJAS'),
        ('laminas', 'LÁMINAS'),
        ('papel', 'PAPEL PERIÓDICO'),
        ('planchas', 'PLANCHAS'),
        ('separadores', 'SEPARADORES'),
        ('materias_primas', 'MATERIAS PRIMAS'),
    ], string='Categoría MEGASTOCK', help='Categoría para codificación automática')
    
    # Campos técnicos específicos
    largo_cm = fields.Float(string='Largo (cm)', digits=(8, 2))
    ancho_cm = fields.Float(string='Ancho (cm)', digits=(8, 2))
    alto_cm = fields.Float(string='Alto (cm)', digits=(8, 2))
    ceja_cm = fields.Float(string='Ceja (cm)', digits=(8, 2))
    
    flauta = fields.Selection([
        ('c', 'C'),
        ('b', 'B'),
        ('e', 'E'),
    ], string='Flauta')
    
    test_value = fields.Selection([
        ('200', '200'),
        ('250', '250'),
        ('275', '275'),
        ('300', '300'),
    ], string='Test')
    
    kl_value = fields.Selection([
        ('32', '32'),
        ('44', '44'),
    ], string='KL (Kilolibras)')
    
    material_type = fields.Selection([
        ('kraft', 'KRAFT'),
        ('interstock', 'INTERSTOCK'),
        ('monus', 'MONUS'),
        ('westrock', 'WESTROCK'),
    ], string='Material')
    
    colors_printing = fields.Selection([
        ('1', '1 Color'),
        ('2', '2 Colores'),
        ('3', '3 Colores'),
        ('4', '4 Colores (CMYK)'),
        ('0', 'Sin Impresión'),
    ], string='Colores Impresión')
    
    gramaje = fields.Selection([
        ('90', '90'),
        ('125', '125'),
        ('150', '150'),
        ('175', '175'),
        ('200', '200'),
    ], string='Gramaje (g/m²)')
    
    tipo_caja = fields.Selection([
        ('tapa_fondo', 'Tapa y Fondo'),
        ('jumbo', 'Jumbo'),
        ('exportacion', 'Exportación'),
        ('americana', 'Americana'),
    ], string='Tipo de Caja')
    
    # Campo calculado para descripción técnica
    technical_description = fields.Text(
        string='Descripción Técnica',
        compute='_compute_technical_description',
        store=True
    )
    
    @api.depends('largo_cm', 'ancho_cm', 'alto_cm', 'ceja_cm', 'flauta', 'test_value', 
                 'material_type', 'colors_printing', 'gramaje', 'tipo_caja')
    def _compute_technical_description(self):
        """Genera descripción técnica automática"""
        for record in self:
            desc_parts = []
            
            # Dimensiones
            if record.largo_cm and record.ancho_cm:
                if record.alto_cm:
                    desc_parts.append(f"Dimensiones: {record.largo_cm}x{record.ancho_cm}x{record.alto_cm} cm")
                else:
                    desc_parts.append(f"Dimensiones: {record.largo_cm}x{record.ancho_cm} cm")
            
            if record.ceja_cm:
                desc_parts.append(f"Ceja: {record.ceja_cm} cm")
            
            # Especificaciones cartón
            if record.flauta:
                desc_parts.append(f"Flauta: {record.flauta.upper()}")
            
            if record.test_value:
                desc_parts.append(f"Test: {record.test_value}")
            
            if record.kl_value:
                desc_parts.append(f"KL: {record.kl_value}")
            
            # Material
            if record.material_type:
                desc_parts.append(f"Material: {record.material_type.upper()}")
            
            # Impresión
            if record.colors_printing:
                if record.colors_printing == '0':
                    desc_parts.append("Sin Impresión")
                elif record.colors_printing == '4':
                    desc_parts.append("4 Colores (CMYK)")
                else:
                    desc_parts.append(f"{record.colors_printing} Color{'es' if int(record.colors_printing) > 1 else ''}")
            
            # Gramaje
            if record.gramaje:
                desc_parts.append(f"Gramaje: {record.gramaje} g/m²")
            
            # Tipo de caja
            if record.tipo_caja:
                tipo_names = dict(record._fields['tipo_caja'].selection)
                desc_parts.append(f"Tipo: {tipo_names.get(record.tipo_caja)}")
            
            record.technical_description = "\n".join(desc_parts) if desc_parts else ""
    
    @api.model
    def create(self, vals):
        """Override create para generar código automático"""
        # Determinar categoría MEGASTOCK basada en categoría de producto
        if 'categ_id' in vals and not vals.get('megastock_category'):
            vals['megastock_category'] = self._get_megastock_category_from_categ(vals['categ_id'])
        
        # Generar código MEGASTOCK si está habilitado
        if not vals.get('megastock_code') and vals.get('megastock_category'):
            auto_coding = self.env['ir.config_parameter'].sudo().get_param('megastock.auto_product_coding', 'False')
            if auto_coding == 'True':
                vals['megastock_code'] = self._generate_megastock_code(vals.get('megastock_category'))
                if not vals.get('default_code'):
                    vals['default_code'] = vals['megastock_code']
        
        return super().create(vals)
    
    def write(self, vals):
        """Override write para validar códigos"""
        # Validar código MEGASTOCK si se modifica
        if 'megastock_code' in vals:
            for record in self:
                if vals['megastock_code'] and not record._validate_megastock_code(vals['megastock_code']):
                    raise ValidationError(_('El código MEGASTOCK "%s" no tiene el formato válido.') % vals['megastock_code'])
        
        return super().write(vals)
    
    def _get_megastock_category_from_categ(self, categ_id):
        """Determina la categoría MEGASTOCK basada en la categoría del producto"""
        categ = self.env['product.category'].browse(categ_id)
        
        # Mapeo de categorías
        category_mapping = {
            'CAJAS': 'cajas',
            'LÁMINAS': 'laminas',
            'PAPEL PERIÓDICO': 'papel',
            'PLANCHAS': 'planchas',
            'SEPARADORES': 'separadores',
            'MATERIAS PRIMAS': 'materias_primas',
        }
        
        # Buscar en la jerarquía de categorías
        current_categ = categ
        while current_categ:
            if current_categ.name in category_mapping:
                return category_mapping[current_categ.name]
            current_categ = current_categ.parent_id
        
        return False
    
    def _generate_megastock_code(self, category):
        """Genera código MEGASTOCK automático basado en la categoría"""
        sequence_mapping = {
            'cajas': 'megastock.product.cajas',
            'laminas': 'megastock.product.laminas',
            'papel': 'megastock.product.papel',
            'planchas': 'megastock.product.planchas',
            'separadores': 'megastock.product.separadores',
            'materias_primas': 'megastock.product.materias.primas',
        }
        
        sequence_code = sequence_mapping.get(category)
        if sequence_code:
            return self.env['ir.sequence'].next_by_code(sequence_code)
        
        return False
    
    def _validate_megastock_code(self, code):
        """Valida formato del código MEGASTOCK"""
        if not code:
            return True
        
        # Patrón para códigos MEGASTOCK: 3 dígitos de prefijo + 5 dígitos de secuencia
        pattern = r'^[0-9]{3}[0-9]{5}$'
        return bool(re.match(pattern, code))
    
    @api.constrains('megastock_code')
    def _check_megastock_code_unique(self):
        """Valida que el código MEGASTOCK sea único"""
        for record in self:
            if record.megastock_code:
                existing = self.search([
                    ('megastock_code', '=', record.megastock_code),
                    ('id', '!=', record.id)
                ])
                if existing:
                    raise ValidationError(_('El código MEGASTOCK "%s" ya existe en el producto "%s".') % 
                                        (record.megastock_code, existing[0].name))
    
    def action_generate_megastock_code(self):
        """Acción para generar código MEGASTOCK manualmente"""
        for record in self:
            if record.megastock_category and not record.megastock_code:
                code = record._generate_megastock_code(record.megastock_category)
                if code:
                    record.megastock_code = code
                    if not record.default_code:
                        record.default_code = code
    
    def action_update_technical_description(self):
        """Acción para actualizar descripción técnica manualmente"""
        self._compute_technical_description()