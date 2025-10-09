# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError

class ProcesoPreprinter(models.Model):
    _name = 'megastock.proceso.preprinter'
    _description = 'Proceso Preprinter MEGASTOCK'
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
        'megastock.proceso.preprinter.line',
        'preprinter_id',
        string='Materiales'
    )
    observaciones = fields.Text(string='Observaciones')

    def name_get(self):
        result = []
        for record in self:
            name = f"Preprinter - {record.work_order_id.numero_orden}"
            result.append((record.id, name))
        return result

    def action_finalizar(self):
        """Finalizar el proceso Preprinter y crear automáticamente Microcorrugado"""
        if self.estado == 'finalizado':
            raise UserError('Este proceso ya ha sido finalizado.')

        # Finalizar preprinter
        self.write({
            'estado': 'finalizado',
            'fecha_fin': fields.Datetime.now()
        })

        # CREAR AUTOMÁTICAMENTE EL PROCESO MICROCORRUGADO
        # Si quieres cambiar a creación MANUAL, comenta las siguientes líneas (líneas 61-74)
        microcorrugado = self.env['megastock.proceso.microcorrugado'].create({
            'work_order_id': self.work_order_id.id,
            'fecha_inicio': fields.Datetime.now(),
            'estado': 'iniciado',
        })

        # Actualizar la orden de trabajo
        self.work_order_id.write({
            'estado': 'microcorrugado',
            'microcorrugado_id': microcorrugado.id
        })

        # Abrir el formulario de microcorrugado
        return {
            'type': 'ir.actions.act_window',
            'name': 'Proceso Microcorrugado',
            'res_model': 'megastock.proceso.microcorrugado',
            'res_id': microcorrugado.id,
            'view_mode': 'form',
            'target': 'current',
        }


class ProcesoPreprinterLine(models.Model):
    _name = 'megastock.proceso.preprinter.line'
    _description = 'Línea de Material Preprinter'

    preprinter_id = fields.Many2one(
        'megastock.proceso.preprinter',
        string='Preprinter',
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
