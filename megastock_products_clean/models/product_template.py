# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    # Código automático MEGASTOCK
    megastock_code = fields.Char(
        string='Código MEGASTOCK', 
        copy=False, 
        readonly=True,
        help='Código generado automáticamente para MEGASTOCK'
    )
    
    # Campo de categoría MEGASTOCK
    megastock_category = fields.Selection([
        ('cajas', 'CAJAS'),
        ('laminas', 'LÁMINAS'),
        ('papel', 'PAPEL PERIÓDICO'),
        ('planchas', 'PLANCHAS'),
        ('separadores', 'SEPARADORES'),
        ('materias_primas', 'MATERIAS PRIMAS'),
    ], string='Categoría MEGASTOCK', help='Categoría específica de MEGASTOCK')
    
    # Dimensiones
    largo_cm = fields.Float(string='Largo (cm)', digits=(10, 2))
    ancho_cm = fields.Float(string='Ancho (cm)', digits=(10, 2))
    alto_cm = fields.Float(string='Alto (cm)', digits=(10, 2))
    
    # Especificaciones básicas
    flauta = fields.Selection([
        ('c', 'C'),
        ('b', 'B'), 
        ('e', 'E'),
    ], string='Tipo de Flauta')
    
    material_type = fields.Selection([
        ('kraft', 'KRAFT'),
        ('interstock', 'INTERSTOCK'),
        ('monus', 'MONUS'),
        ('westrock', 'WESTROCK'),
    ], string='Tipo de Material')
    
    # Descripción técnica automática
    technical_description = fields.Text(
        string='Descripción Técnica',
        compute='_compute_technical_description',
        store=True,
        help='Descripción generada automáticamente basada en especificaciones'
    )
    
    @api.model
    def create(self, vals):
        """Generar código MEGASTOCK al crear producto"""
        if not vals.get('megastock_code') and vals.get('megastock_category'):
            vals['megastock_code'] = self._generate_megastock_code(vals.get('megastock_category'))
        return super().create(vals)
    
    def _generate_megastock_code(self, category):
        """Generar código automático para MEGASTOCK"""
        if not category:
            return False
            
        # Prefijos por categoría
        prefixes = {
            'cajas': 'CAJ',
            'laminas': 'LAM', 
            'papel': 'PAP',
            'planchas': 'PLA',
            'separadores': 'SEP',
            'materias_primas': 'MAT'
        }
        
        prefix = prefixes.get(category, 'PRO')
        
        # Buscar el último número para esta categoría
        last_product = self.search([
            ('megastock_code', 'like', f'{prefix}%')
        ], limit=1, order='megastock_code desc')
        
        if last_product and last_product.megastock_code:
            try:
                last_number = int(last_product.megastock_code[3:])
                new_number = last_number + 1
            except ValueError:
                new_number = 1
        else:
            new_number = 1
            
        return f'{prefix}{new_number:04d}'
    
    @api.depends('largo_cm', 'ancho_cm', 'alto_cm', 'flauta', 'material_type', 'megastock_category')
    def _compute_technical_description(self):
        """Generar descripción técnica automáticamente"""
        for record in self:
            desc_parts = []
            
            if record.megastock_category:
                desc_parts.append(f"Categoría: {dict(record._fields['megastock_category'].selection).get(record.megastock_category)}")
            
            if record.largo_cm and record.ancho_cm:
                if record.alto_cm:
                    desc_parts.append(f"Dimensiones: {record.largo_cm} x {record.ancho_cm} x {record.alto_cm} cm")
                else:
                    desc_parts.append(f"Dimensiones: {record.largo_cm} x {record.ancho_cm} cm")
            
            if record.flauta:
                desc_parts.append(f"Flauta: {record.flauta.upper()}")
                
            if record.material_type:
                desc_parts.append(f"Material: {dict(record._fields['material_type'].selection).get(record.material_type)}")
            
            record.technical_description = '\n'.join(desc_parts) if desc_parts else False