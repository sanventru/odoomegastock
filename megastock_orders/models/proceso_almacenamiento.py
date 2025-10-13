# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError

class ProcesoAlmacenamiento(models.Model):
    _name = 'megastock.proceso.almacenamiento'
    _description = 'Proceso Almacenamiento MEGASTOCK'
    _order = 'fecha_inicio desc'
    _rec_name = 'work_order_id'

    work_order_id = fields.Many2one(
        'megastock.work.order',
        string='Orden de Trabajo',
        required=True,
        ondelete='cascade',
        readonly=True
    )
    fecha_inicio = fields.Datetime(
        string='Fecha de Inicio',
        required=True,
        readonly=True,
        default=fields.Datetime.now
    )
    fecha_fin = fields.Datetime(
        string='Fecha de Finalización',
        readonly=True
    )
    estado = fields.Selection([
        ('iniciado', 'Iniciado'),
        ('finalizado', 'Finalizado'),
    ], string='Estado', default='iniciado', required=True, tracking=True)

    ubicacion_almacen = fields.Char(string='Ubicación en Almacén', help='Ubicación física donde se almacena el producto')
    lote = fields.Char(string='Lote', help='Número de lote asignado')
    observaciones = fields.Text(string='Observaciones')

    def name_get(self):
        result = []
        for record in self:
            name = f"Almacenamiento - {record.work_order_id.numero_orden}"
            result.append((record.id, name))
        return result

    def action_finalizar(self):
        """Finalizar el proceso Almacenamiento y completar la orden de trabajo"""
        if self.estado == 'finalizado':
            raise UserError('Este proceso ya ha sido finalizado.')

        # Finalizar almacenamiento
        self.write({
            'estado': 'finalizado',
            'fecha_fin': fields.Datetime.now()
        })

        # Completar la orden de trabajo
        self.work_order_id.write({
            'estado': 'completada',
            'fecha_fin': fields.Datetime.now()
        })

        # Actualizar estado de órdenes de producción relacionadas
        self.work_order_id.production_order_ids.write({'estado': 'entregado'})

        # Retornar a la orden de trabajo
        return {
            'type': 'ir.actions.act_window',
            'name': 'Orden de Trabajo',
            'res_model': 'megastock.work.order',
            'res_id': self.work_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
