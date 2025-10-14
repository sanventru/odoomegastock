# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError

class GenerarOrdenesWizard(models.TransientModel):
    _name = 'megastock.generar.ordenes.wizard'
    _description = 'Wizard para Generar Órdenes de Trabajo'

    requiere_doblez = fields.Boolean(
        string='Requiere Doblez',
        default=False,
        help='Indica si las órdenes de trabajo requieren proceso de doblado'
    )

    def action_registrar(self):
        """Registra el valor de requiere_doblez y genera las órdenes de trabajo"""
        self.ensure_one()

        # Buscar todas las órdenes que tienen grupo de planificación pero no tienen orden de trabajo
        ordenes_planificadas = self.env['megastock.production.order'].search([
            ('grupo_planificacion', '!=', False),
            ('work_order_id', '=', False)
        ])

        if not ordenes_planificadas:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Sin órdenes planificadas',
                    'message': 'No hay órdenes planificadas sin orden de trabajo para procesar.',
                    'type': 'warning',
                }
            }

        # Agrupar por grupo_planificacion
        grupos = {}
        for orden in ordenes_planificadas:
            grupo = orden.grupo_planificacion
            if grupo not in grupos:
                grupos[grupo] = []
            grupos[grupo].append(orden)

        # Crear una orden de trabajo por cada grupo
        work_orders_created = []
        for grupo, ordenes in grupos.items():
            # Tomar valores del primer elemento (todas las órdenes del grupo comparten estos valores)
            primera_orden = ordenes[0]

            # Calcular totales del grupo
            # SUMAR metros_lineales_planificados de todas las órdenes del grupo
            metros_totales = sum(orden.metros_lineales_planificados for orden in ordenes)
            # SUMAR cortes_planificados de todas las órdenes del grupo
            cortes_totales = sum(orden.cortes_planificados for orden in ordenes)

            # SUMAR sobrantes individuales de todas las órdenes del grupo
            sobrante_total = sum(orden.sobrante for orden in ordenes)

            # PROMEDIAR la eficiencia del grupo
            eficiencia_promedio = sum(orden.eficiencia for orden in ordenes) / len(ordenes) if ordenes else 0

            # Crear la orden de trabajo
            work_order = self.env['megastock.work.order'].create({
                'grupo_planificacion': grupo,
                'tipo_combinacion': primera_orden.tipo_combinacion,
                'bobina_utilizada': primera_orden.bobina_utilizada,
                'ancho_utilizado': primera_orden.ancho_utilizado,
                'sobrante': sobrante_total,  # SUMA de sobrantes del grupo
                'eficiencia': eficiencia_promedio,  # PROMEDIO de eficiencias
                'metros_lineales_totales': metros_totales,
                'cortes_totales': cortes_totales,
                'estado': 'programada',
                'requiere_doblez': self.requiere_doblez,  # Asignar el valor del wizard
            })

            # Asociar las órdenes de producción a esta orden de trabajo
            # Convertir lista de Python a recordset de Odoo
            ordenes_recordset = self.env['megastock.production.order'].browse([o.id for o in ordenes])
            ordenes_recordset.write({
                'work_order_id': work_order.id,
                'estado': 'ot'
            })
            work_orders_created.append(work_order.id)

        # Retornar a la vista de órdenes de trabajo creadas
        return {
            'type': 'ir.actions.act_window',
            'name': 'Órdenes de Trabajo Generadas',
            'res_model': 'megastock.work.order',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', work_orders_created)],
            'target': 'current',
        }
