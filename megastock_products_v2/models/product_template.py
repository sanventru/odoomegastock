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
    
    numero_troquel = fields.Char(
        string='Número de troquel',
        help='Número identificador del troquel utilizado'
    )
    
    empaque = fields.Selection([
        ('caja', 'Caja'),
        ('pallet', 'Pallet'),
        ('bulto', 'Bulto'),
        ('unidad', 'Unidad'),
        ('rollo', 'Rollo'),
    ], string='Empaque')
    
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
                 'material_type', 'colors_printing', 'gramaje', 'tipo_caja', 'numero_troquel', 'empaque')
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
            
            # Número de troquel
            if record.numero_troquel:
                desc_parts.append(f"Troquel: {record.numero_troquel}")
            
            # Material
            if record.material_type:
                desc_parts.append(f"Material: {record.material_type.upper()}")
            
            # Empaque
            if record.empaque:
                empaque_names = dict(record._fields['empaque'].selection)
                desc_parts.append(f"Empaque: {empaque_names.get(record.empaque)}")
            
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