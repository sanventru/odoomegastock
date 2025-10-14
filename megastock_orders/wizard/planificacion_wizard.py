# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError

class PlanificacionWizard(models.TransientModel):
    _name = 'megastock.planificacion.wizard'
    _description = 'Wizard para Planificación de Órdenes'

    test_principal = fields.Integer(
        string='Test Principal',
        required=True,
        help='Test'
    )

    cavidad_limite = fields.Integer(
        string='Cavidad Límite',
        required=True,
        default=1,
        help='Cavidad'
    )

    bobina_unica = fields.Boolean(
        string='Bobina Única',
        default=False,
        help='Si está marcado, todos los grupos usarán una sola bobina (la que minimice el desperdicio total). '
             'Si no está marcado, cada grupo elegirá la bobina que minimice su propio desperdicio.'
    )

    @api.constrains('cavidad_limite')
    def _check_cavidad_limite(self):
        """Validar que la cavidad límite sea mayor a 0"""
        for wizard in self:
            if wizard.cavidad_limite <= 0:
                raise UserError('La cavidad límite debe ser mayor a 0.')

    def action_planificar(self):
        """Ejecuta la planificación con los parámetros ingresados"""
        self.ensure_one()

        # Obtener las órdenes seleccionadas desde el contexto
        active_ids = self.env.context.get('active_ids', [])
        if not active_ids:
            raise UserError('No hay órdenes seleccionadas para planificar.')

        # Obtener las órdenes seleccionadas
        ordenes = self.env['megastock.production.order'].browse(active_ids)

        # Filtrar solo órdenes pendientes
        ordenes_pendientes = ordenes.filtered(lambda r: r.estado == 'pendiente')

        if not ordenes_pendientes:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Sin órdenes válidas',
                    'message': 'Solo se pueden planificar órdenes en estado pendiente.',
                    'type': 'warning',
                }
            }

        # Ejecutar algoritmo de optimización con los parámetros
        resultado = ordenes_pendientes[0]._optimizar_ordenes(
            ordenes_pendientes,
            test_principal=self.test_principal,
            cavidad_limite=self.cavidad_limite,
            bobina_unica=self.bobina_unica
        )

        # Construir mensaje con información del resultado
        mensaje = f'Se han planificado {len(ordenes_pendientes)} órdenes en {resultado["grupos"]} grupos.'
        mensaje += f'\nEficiencia promedio: {resultado["eficiencia_promedio"]:.1f}%'
        mensaje += f'\nDesperdicio total: {resultado["desperdicio_total"]:.0f}mm'

        if self.bobina_unica and 'bobina_optima' in resultado:
            mensaje += f'\n\nBobina única utilizada: {resultado["bobina_optima"]:.0f}mm'
            mensaje += f'\nTodos los grupos usan la misma bobina que minimiza el desperdicio total.'
        else:
            mensaje += f'\n\nCada grupo ha sido optimizado con la bobina que minimiza su propio desperdicio.'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Planificación Masiva Completada',
                'message': mensaje,
                'type': 'success',
                'sticky': True,
            }
        }
