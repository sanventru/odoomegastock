# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ProductTemplateIntelligent(models.Model):
    _inherit = 'product.template'
    
    # Campos para cálculos inteligentes
    length = fields.Float(
        string='Longitud (mm)',
        help='Longitud del producto en milímetros'
    )
    
    width = fields.Float(
        string='Ancho (mm)',
        help='Ancho del producto en milímetros'
    )
    
    height = fields.Float(
        string='Alto (mm)',
        help='Alto del producto en milímetros'
    )
    
    surface_area = fields.Float(
        string='Área Superficie (m²)',
        compute='_compute_surface_area',
        store=True,
        help='Área de superficie calculada automáticamente'
    )
    
    volume = fields.Float(
        string='Volumen (cm³)',
        compute='_compute_volume',
        store=True,
        help='Volumen calculado automáticamente'
    )
    
    @api.depends('length', 'width', 'height')
    def _compute_surface_area(self):
        """Calcular área de superficie"""
        for product in self:
            if product.length and product.width:
                # Área básica para desarrollo de caja
                area = (product.length * product.width) / 1000000  # Convertir a m²
                product.surface_area = area
            else:
                product.surface_area = 0.0
    
    @api.depends('length', 'width', 'height')
    def _compute_volume(self):
        """Calcular volumen"""
        for product in self:
            if product.length and product.width and product.height:
                volume = (product.length * product.width * product.height) / 1000  # Convertir a cm³
                product.volume = volume
            else:
                product.volume = 0.0