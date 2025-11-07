# -*- coding: utf-8 -*-
#para carga
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class Bobina(models.Model):
    _name = 'megastock.bobina'
    _description = 'Bobinas Disponibles MEGASTOCK'
    _order = 'ancho desc'
    _rec_name = 'display_name'

    codigo = fields.Char(string='Código', help='Código único de identificación de la bobina')
    ancho = fields.Float(string='Ancho (mm)', required=True, help='Ancho de la bobina en milímetros')
    descripcion = fields.Text(string='Descripción', help='Descripción detallada de la bobina')
    activa = fields.Boolean(string='Activa', default=True, help='Si está marcada, la bobina estará disponible para planificación')
    notas = fields.Text(string='Notas', help='Observaciones adicionales sobre esta bobina')
    display_name = fields.Char(string='Nombre', compute='_compute_display_name', store=False)

    # Campos de información adicional
    proveedor = fields.Char(string='Proveedor', help='Proveedor de la bobina')
    stock_minimo = fields.Float(string='Stock Mínimo', help='Stock mínimo recomendado')
    stock_actual = fields.Float(string='Stock Actual', help='Stock actual disponible')
    costo = fields.Float(string='Costo por Unidad', help='Costo por unidad de la bobina')

    @api.depends('ancho')
    def _compute_display_name(self):
        for record in self:
            if record.ancho:
                # Mostrar solo el ancho (sin código)
                record.display_name = f"{record.ancho:.0f}mm"
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
            # Mostrar solo el ancho (sin código)
            name = f"{record.ancho:.0f}mm"
            if not record.activa:
                name += " (Inactiva)"
            result.append((record.id, name))
        return result

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """Retorna solo una bobina por cada ancho único para evitar duplicados en selectores"""
        if args is None:
            args = []

        # Buscar todas las bobinas que cumplan el criterio
        bobinas = self.search(args)

        # Agrupar por ancho y tomar solo la primera de cada grupo
        anchos_vistos = set()
        bobinas_unicas = self.browse()

        for bobina in bobinas.sorted('ancho', reverse=True):
            if bobina.ancho not in anchos_vistos:
                anchos_vistos.add(bobina.ancho)
                bobinas_unicas |= bobina

        # Aplicar límite si se especifica
        if limit:
            bobinas_unicas = bobinas_unicas[:limit]

        # Filtrar por nombre si se proporciona
        if name:
            bobinas_unicas = bobinas_unicas.filtered(
                lambda b: name.lower() in f"{b.ancho:.0f}mm".lower()
            )

        # Retornar en formato name_search: lista de tuplas (id, nombre)
        return bobinas_unicas.name_get()

    def action_recalcular_display_name(self):
        """Recalcula el display_name de todas las bobinas para reflejar cambios"""
        for record in self:
            record._compute_display_name()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Recálculo completado',
                'message': f'Se han recalculado los nombres de {len(self)} bobinas.',
                'type': 'success',
            }
        }

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