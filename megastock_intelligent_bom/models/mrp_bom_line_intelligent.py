# -*- coding: utf-8 -*-

from odoo import models, fields, api

class MrpBomLineIntelligent(models.Model):
    _inherit = 'mrp.bom.line'
    
    # Campos inteligentes
    is_calculated = fields.Boolean(
        string='Calculado Automáticamente',
        default=False,
        help='Indica si esta línea fue calculada por reglas automáticas'
    )
    
    calculation_rule_id = fields.Many2one(
        'megastock.bom.calculation.rule',
        string='Regla de Cálculo',
        help='Regla que calculó esta línea'
    )
    
    original_qty = fields.Float(
        string='Cantidad Original',
        help='Cantidad original antes de cálculo automático'
    )
    
    last_calculation_date = fields.Datetime(
        string='Última Actualización',
        help='Fecha de última actualización automática'
    )
    
    substitution_available = fields.Boolean(
        string='Sustitución Disponible',
        compute='_compute_substitution_available',
        help='Indica si hay reglas de sustitución para este material'
    )
    
    @api.depends('product_id')
    def _compute_substitution_available(self):
        """Verificar si hay reglas de sustitución disponibles"""
        for line in self:
            substitution_rules = self.env['megastock.material.substitution.rule'].search([
                ('primary_material_id', '=', line.product_id.id),
                ('active', '=', True)
            ])
            line.substitution_available = bool(substitution_rules)