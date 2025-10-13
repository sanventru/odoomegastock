# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError

class ProcesoCorteCeja(models.Model):
    _name = 'megastock.proceso.corte.ceja'
    _description = 'Proceso Corte de Ceja MEGASTOCK'
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
        'megastock.proceso.corte.ceja.line',
        'corte_ceja_id',
        string='Materiales'
    )
    observaciones = fields.Text(string='Observaciones')

    def name_get(self):
        result = []
        for record in self:
            name = f"Corte de Ceja - {record.work_order_id.numero_orden}"
            result.append((record.id, name))
        return result

    def action_finalizar(self):
        """Finalizar el proceso Corte de Ceja e iniciar Corte de Guillotina"""
        if self.estado == 'finalizado':
            raise UserError('Este proceso ya ha sido finalizado.')

        # Finalizar corte de ceja
        self.write({
            'estado': 'finalizado',
            'fecha_fin': fields.Datetime.now()
        })

        # Crear proceso Corte de Guillotina
        guillotina = self.env['megastock.proceso.corte.guillotina'].create({
            'work_order_id': self.work_order_id.id,
            'fecha_inicio': fields.Datetime.now(),
            'estado': 'iniciado',
        })

        # Actualizar la orden de trabajo
        self.work_order_id.write({
            'estado': 'guillotina',
            'corte_guillotina_id': guillotina.id
        })

        # Abrir el formulario de corte de guillotina
        return {
            'type': 'ir.actions.act_window',
            'name': 'Proceso Corte de Guillotina',
            'res_model': 'megastock.proceso.corte.guillotina',
            'res_id': guillotina.id,
            'view_mode': 'form',
            'target': 'current',
        }


class ProcesoCorteCejaLine(models.Model):
    _name = 'megastock.proceso.corte.ceja.line'
    _description = 'Línea de Material Corte de Ceja'

    corte_ceja_id = fields.Many2one(
        'megastock.proceso.corte.ceja',
        string='Corte de Ceja',
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
