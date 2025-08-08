# -*- coding: utf-8 -*-

from odoo import fields, models


class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'

    production_line_type = fields.Selection([
        ('papel_periodico', 'Papel Periódico'),
        ('cajas', 'Cajas & Planchas'),
        ('lamina_micro', 'Lámina Micro Corrugada')
    ], string='Tipo de Línea de Producción', 
    help="Especifica a qué línea de producción pertenece este centro de trabajo")