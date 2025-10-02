# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError

class Bobina(models.Model):
    _name = 'megastock.bobina'
    _description = 'Bobinas Disponibles MEGASTOCK'
    _order = 'ancho desc'
    _rec_name = 'display_name'

    ancho = fields.Float(string='Ancho (mm)', required=True, help='Ancho de la bobina en milímetros')
    activa = fields.Boolean(string='Activa', default=True, help='Si está marcada, la bobina estará disponible para planificación')
    notas = fields.Text(string='Notas', help='Observaciones adicionales sobre esta bobina')
    display_name = fields.Char(string='Nombre', compute='_compute_display_name', store=True)

    # Campos de información adicional
    proveedor = fields.Char(string='Proveedor', help='Proveedor de la bobina')
    stock_minimo = fields.Float(string='Stock Mínimo', help='Stock mínimo recomendado')
    stock_actual = fields.Float(string='Stock Actual', help='Stock actual disponible')
    costo = fields.Float(string='Costo por Unidad', help='Costo por unidad de la bobina')

    @api.depends('ancho')
    def _compute_display_name(self):
        for record in self:
            if record.ancho:
                record.display_name = f"Bobina {record.ancho:.0f}mm"
            else:
                record.display_name = "Bobina sin ancho"

    @api.constrains('ancho')
    def _check_ancho_positivo(self):
        for record in self:
            if record.ancho <= 0:
                raise ValidationError("El ancho de la bobina debe ser mayor a 0")

    @api.model
    def get_bobinas_activas(self):
        """Retorna una lista con los anchos de las bobinas activas ordenadas de mayor a menor"""
        bobinas = self.search([('activa', '=', True)], order='ancho desc')
        return [bobina.ancho for bobina in bobinas]

    def name_get(self):
        result = []
        for record in self:
            name = f"Bobina {record.ancho:.0f}mm"
            if not record.activa:
                name += " (Inactiva)"
            result.append((record.id, name))
        return result

    @api.model
    def create_default_bobinas(self):
        """Crear bobinas por defecto si no existen"""
        existing_bobinas = self.search([])
        if not existing_bobinas:
            anchos_default = [1800, 1600, 1400, 1200, 1000, 800]
            for ancho in anchos_default:
                self.create({
                    'ancho': ancho,
                    'activa': True,
                    'notas': 'Bobina creada automáticamente durante la inicialización'
                })