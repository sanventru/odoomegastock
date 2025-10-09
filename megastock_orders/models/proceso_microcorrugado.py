# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError

class ProcesoMicrocorrugado(models.Model):
    _name = 'megastock.proceso.microcorrugado'
    _description = 'Proceso Microcorrugado MEGASTOCK'
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

    material_ids = fields.One2many(
        'megastock.proceso.microcorrugado.line',
        'microcorrugado_id',
        string='Materiales'
    )
    observaciones = fields.Text(string='Observaciones')

    def name_get(self):
        result = []
        for record in self:
            name = f"Microcorrugado - {record.work_order_id.numero_orden}"
            result.append((record.id, name))
        return result

    def action_finalizar(self):
        """Finalizar el proceso Microcorrugado"""
        if self.estado == 'finalizado':
            raise UserError('Este proceso ya ha sido finalizado.')

        # Finalizar microcorrugado
        self.write({
            'estado': 'finalizado',
            'fecha_fin': fields.Datetime.now()
        })

        # Aquí puedes agregar el siguiente proceso cuando me lo indiques
        # Por ahora, simplemente retornamos a la orden de trabajo
        return {
            'type': 'ir.actions.act_window',
            'name': 'Orden de Trabajo',
            'res_model': 'megastock.work.order',
            'res_id': self.work_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }


class ProcesoMicrocorrugadoLine(models.Model):
    _name = 'megastock.proceso.microcorrugado.line'
    _description = 'Línea de Material Microcorrugado'

    microcorrugado_id = fields.Many2one(
        'megastock.proceso.microcorrugado',
        string='Microcorrugado',
        required=True,
        ondelete='cascade'
    )
    producto_id = fields.Many2one(
        'product.product',
        string='Producto',
        required=True,
        domain=[('type', 'in', ['product', 'consu'])]
    )
    cantidad = fields.Float(
        string='Cantidad',
        required=True,
        default=1.0
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='Unidad de Medida',
        related='producto_id.uom_id',
        readonly=True
    )

    @api.onchange('producto_id')
    def _onchange_producto_id(self):
        if self.producto_id:
            self.uom_id = self.producto_id.uom_id
