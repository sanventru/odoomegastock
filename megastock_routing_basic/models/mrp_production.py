# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, timedelta

class MrpProduction(models.Model):
    _inherit = 'mrp.production'
    
    # Campos básicos de planificación MEGASTOCK
    megastock_production_type = fields.Selection([
        ('cajas', 'Cajas Corrugadas'),
        ('planchas', 'Planchas'),
        ('displays', 'Displays'),
        ('otros', 'Otros')
    ], string='Tipo de Producción MEGASTOCK', default='cajas')
    
    planned_efficiency = fields.Float(
        string='Eficiencia Planificada (%)',
        default=85.0,
        help='Eficiencia esperada para esta orden de producción'
    )
    
    corrugado_type = fields.Selection([
        ('simple', 'Corrugado Simple'),
        ('doble', 'Corrugado Doble'),
        ('triple', 'Corrugado Triple')
    ], string='Tipo de Corrugado')
    
    quality_required = fields.Boolean(
        string='Control Calidad Requerido',
        default=True,
        help='Indica si esta producción requiere control de calidad'
    )
    
    megastock_notes = fields.Text(
        string='Notas Especiales MEGASTOCK',
        help='Instrucciones especiales para la producción'
    )