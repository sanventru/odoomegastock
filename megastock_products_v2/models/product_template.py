# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    # Campos básicos MEGASTOCK
    megastock_category = fields.Selection([
        ('cajas', 'CAJAS'),
        ('laminas', 'LÁMINAS'),
        ('papel', 'PAPEL PERIÓDICO'),
        ('planchas', 'PLANCHAS'),
        ('separadores', 'SEPARADORES'),
        ('materias_primas', 'MATERIAS PRIMAS'),
    ], string='Categoría MEGASTOCK')
    
    # Dimensiones básicas
    largo_cm = fields.Float(string='Largo (cm)')
    ancho_cm = fields.Float(string='Ancho (cm)')
    alto_cm = fields.Float(string='Alto (cm)')
    
    # Especificaciones básicas
    flauta = fields.Selection([
        ('c', 'C'), ('b', 'B'), ('e', 'E')
    ], string='Flauta')
    
    material_type = fields.Selection([
        ('kraft', 'KRAFT'),
        ('interstock', 'INTERSTOCK'),
        ('monus', 'MONUS'),
        ('westrock', 'WESTROCK'),
    ], string='Material')
    
    # Descripción técnica simple
    technical_description = fields.Text(string='Descripción Técnica')
    
    @api.onchange('largo_cm', 'ancho_cm', 'alto_cm', 'flauta', 'material_type')
    def _onchange_technical_specs(self):
        """Actualizar descripción técnica automáticamente"""
        desc_parts = []
        
        if self.largo_cm and self.ancho_cm:
            if self.alto_cm:
                desc_parts.append(f"Dimensiones: {self.largo_cm}x{self.ancho_cm}x{self.alto_cm} cm")
            else:
                desc_parts.append(f"Dimensiones: {self.largo_cm}x{self.ancho_cm} cm")
        
        if self.flauta:
            desc_parts.append(f"Flauta: {self.flauta.upper()}")
            
        if self.material_type:
            desc_parts.append(f"Material: {self.material_type.upper()}")
        
        self.technical_description = "\n".join(desc_parts)