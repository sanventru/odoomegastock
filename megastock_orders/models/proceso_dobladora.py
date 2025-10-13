# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError

class ProcesoDobladora(models.Model):
    _name = 'megastock.proceso.dobladora'
    _description = 'Proceso Dobladora MEGASTOCK'
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
        'megastock.proceso.dobladora.line',
        'dobladora_id',
        string='Materiales'
    )
    observaciones = fields.Text(string='Observaciones')

    def name_get(self):
        result = []
        for record in self:
            name = f"Dobladora - {record.work_order_id.numero_orden}"
            result.append((record.id, name))
        return result

    def action_finalizar(self):
        """Finalizar el proceso Dobladora y verificar si requiere corte de ceja"""
        if self.estado == 'finalizado':
            raise UserError('Este proceso ya ha sido finalizado.')

        # Finalizar dobladora
        self.write({
            'estado': 'finalizado',
            'fecha_fin': fields.Datetime.now()
        })

        # Verificar si algún producto tiene ceja > 0
        requiere_corte_ceja = False
        for orden in self.work_order_id.production_order_ids:
            # Acceder al product.template a través de product.product
            if hasattr(orden, 'product_id') and orden.product_id and hasattr(orden.product_id.product_tmpl_id, 'ceja'):
                ceja = orden.product_id.product_tmpl_id.ceja or 0
                if ceja and ceja > 0:
                    requiere_corte_ceja = True
                    break

        if requiere_corte_ceja:
            # Iniciar proceso Corte de Ceja
            corte_ceja = self.env['megastock.proceso.corte.ceja'].create({
                'work_order_id': self.work_order_id.id,
                'fecha_inicio': fields.Datetime.now(),
                'estado': 'iniciado',
            })

            self.work_order_id.write({
                'estado': 'corte_ceja',
                'corte_ceja_id': corte_ceja.id
            })

            return {
                'type': 'ir.actions.act_window',
                'name': 'Proceso Corte de Ceja',
                'res_model': 'megastock.proceso.corte.ceja',
                'res_id': corte_ceja.id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            # No requiere ceja, ir directo a Empaque
            empaque = self.env['megastock.proceso.empaque'].create({
                'work_order_id': self.work_order_id.id,
                'fecha_inicio': fields.Datetime.now(),
                'estado': 'iniciado',
            })

            self.work_order_id.write({
                'estado': 'empaque',
                'empaque_id': empaque.id
            })

            return {
                'type': 'ir.actions.act_window',
                'name': 'Proceso Empaque',
                'res_model': 'megastock.proceso.empaque',
                'res_id': empaque.id,
                'view_mode': 'form',
                'target': 'current',
            }


class ProcesoDobleadoraLine(models.Model):
    _name = 'megastock.proceso.dobladora.line'
    _description = 'Línea de Material Dobladora'

    dobladora_id = fields.Many2one(
        'megastock.proceso.dobladora',
        string='Dobladora',
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
