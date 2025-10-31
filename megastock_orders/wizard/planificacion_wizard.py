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
        required=False,
        default=4,
        readonly=True,
        help='Cavidad límite fija en 4 (no modificable)'
    )

    bobinas_seleccionadas = fields.Many2many(
        'megastock.bobina',
        string='Bobinas a Utilizar',
        required=True,
        domain="[('activa', '=', True)]",
        help='Seleccione las bobinas (anchos) que desea considerar para la planificación. '
             'Si selecciona 1 bobina: todos los grupos usarán esa bobina. '
             'Si selecciona 2+ bobinas: cada grupo elegirá la mejor de las seleccionadas.'
    )

    def action_planificar(self):
        """Ejecuta la planificación con los parámetros ingresados"""
        self.ensure_one()

        # Validar que se hayan seleccionado bobinas
        if not self.bobinas_seleccionadas:
            raise UserError('Debe seleccionar al menos una bobina para planificar.')

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

        # Extraer los anchos de las bobinas seleccionadas y eliminar duplicados
        anchos_seleccionados = list(set(self.bobinas_seleccionadas.mapped('ancho')))

        # Determinar estrategia automáticamente según cantidad de anchos únicos
        bobina_unica = len(anchos_seleccionados) == 1

        # Ejecutar algoritmo de optimización con los parámetros
        resultado = ordenes_pendientes[0]._optimizar_ordenes(
            ordenes_pendientes,
            test_principal=self.test_principal,
            cavidad_limite=self.cavidad_limite,
            bobina_unica=bobina_unica,
            bobinas_disponibles=anchos_seleccionados
        )

        # Construir mensaje con información del resultado
        mensaje = f'Se han planificado {len(ordenes_pendientes)} órdenes en {resultado["grupos"]} grupos.'
        mensaje += f'\nEficiencia promedio: {resultado["eficiencia_promedio"]:.1f}%'
        mensaje += f'\nDesperdicio total: {resultado["desperdicio_total"]:.0f}mm'

        if bobina_unica and 'bobina_optima' in resultado:
            mensaje += f'\n\nBobina única utilizada: {resultado["bobina_optima"]:.0f}mm'
            mensaje += f'\nTodos los grupos usan la misma bobina.'
        else:
            bobinas_usadas = ', '.join([f'{b:.0f}mm' for b in anchos_seleccionados])
            mensaje += f'\n\nBobinas disponibles: {bobinas_usadas}'
            mensaje += f'\nCada grupo ha elegido la mejor bobina para minimizar su desperdicio.'

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
