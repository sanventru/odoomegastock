# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class BomCostAnalysis(models.Model):
    _name = 'megastock.bom.cost.analysis'
    _description = 'Análisis de Costos BOM'
    _order = 'analysis_date desc'
    
    name = fields.Char(
        string='Nombre',
        required=True,
        default=lambda self: f'Análisis {fields.Date.today()}'
    )
    
    bom_id = fields.Many2one(
        'mrp.bom',
        string='BOM',
        required=True,
        help='BOM analizado'
    )
    
    analysis_date = fields.Datetime(
        string='Fecha Análisis',
        default=fields.Datetime.now,
        required=True
    )
    
    current_total_cost = fields.Float(
        string='Costo Total Actual',
        help='Costo total con precios actuales'
    )
    
    historical_cost = fields.Float(
        string='Costo Histórico',
        help='Costo histórico de referencia'
    )
    
    cost_variance = fields.Float(
        string='Variación Costo',
        compute='_compute_cost_variance',
        store=True
    )
    
    cost_variance_percentage = fields.Float(
        string='Variación %',
        compute='_compute_cost_variance',
        store=True
    )
    
    most_expensive_material = fields.Many2one(
        'product.product',
        string='Material Más Costoso',
        help='Material con mayor impacto en costo'
    )
    
    optimization_suggestions = fields.Text(
        string='Sugerencias de Optimización',
        help='Sugerencias automáticas de optimización'
    )
    
    @api.depends('current_total_cost', 'historical_cost')
    def _compute_cost_variance(self):
        """Calcular variación de costos"""
        for analysis in self:
            if analysis.historical_cost > 0:
                analysis.cost_variance = analysis.current_total_cost - analysis.historical_cost
                analysis.cost_variance_percentage = (analysis.cost_variance / analysis.historical_cost) * 100
            else:
                analysis.cost_variance = 0.0
                analysis.cost_variance_percentage = 0.0