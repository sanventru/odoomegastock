# -*- coding: utf-8 -*-
#compensacion
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class Flauta(models.Model):
    _name = 'megastock.flauta'
    _description = 'Catálogo de Flautas'
    _order = 'codigo'
    _rec_name = 'codigo'

    codigo = fields.Char(
        string='Código',
        required=True,
        index=True,
        help='Código de la flauta (E, B, C, A, EB, BC, etc.)'
    )
    nombre = fields.Char(
        string='Nombre/Descripción',
        required=True,
        help='Descripción de la flauta'
    )
    compensacion_largo = fields.Float(
        string='Compensación Largo',
        digits=(16, 2),
        default=0.0,
        help='Valor de compensación para el largo'
    )
    compensacion_ancho = fields.Float(
        string='Compensación Ancho',
        digits=(16, 2),
        default=0.0,
        help='Valor de compensación para el ancho'
    )
    compensacion_alto = fields.Float(
        string='Compensación Alto',
        digits=(16, 2),
        default=0.0,
        help='Valor de compensación para el alto'
    )
    activo = fields.Boolean(
        string='Activo',
        default=True,
        help='Indica si la flauta está activa para su uso'
    )

    _sql_constraints = [
        ('codigo_unique', 'unique(codigo)', 'El código de flauta debe ser único!')
    ]

    @api.model_create_multi
    def create(self, vals_list):
        # Normalizar código antes de crear
        for vals in vals_list:
            if 'codigo' in vals and vals['codigo']:
                vals['codigo'] = vals['codigo'].upper().strip()
        return super(Flauta, self).create(vals_list)

    def write(self, vals):
        # Normalizar código antes de escribir
        if 'codigo' in vals and vals['codigo']:
            vals['codigo'] = vals['codigo'].upper().strip()
        return super(Flauta, self).write(vals)

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.codigo} - {record.nombre}"
            result.append((record.id, name))
        return result
