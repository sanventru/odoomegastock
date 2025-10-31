# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError

class ProcesoEmpaque(models.Model):
    _name = 'megastock.proceso.empaque'
    _description = 'Proceso Empaque MEGASTOCK'
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
        'megastock.proceso.empaque.line',
        'empaque_id',
        string='Materiales'
    )
    personal_ids = fields.One2many(
        'megastock.proceso.empaque.personal',
        'empaque_id',
        string='Personal de Empaque'
    )
    observaciones = fields.Text(string='Observaciones')

    def name_get(self):
        result = []
        for record in self:
            name = f"Empaque - {record.work_order_id.numero_orden}"
            result.append((record.id, name))
        return result

    def action_finalizar(self):
        """Finalizar el proceso Empaque e iniciar Almacenamiento"""
        if self.estado == 'finalizado':
            raise UserError('Este proceso ya ha sido finalizado.')

        # Finalizar empaque
        self.write({
            'estado': 'finalizado',
            'fecha_fin': fields.Datetime.now()
        })

        # Crear proceso Almacenamiento
        almacenamiento = self.env['megastock.proceso.almacenamiento'].create({
            'work_order_id': self.work_order_id.id,
            'fecha_inicio': fields.Datetime.now(),
            'estado': 'iniciado',
        })

        # Actualizar la orden de trabajo
        self.work_order_id.write({
            'estado': 'almacenamiento',
            'almacenamiento_id': almacenamiento.id
        })

        # Abrir el formulario de almacenamiento
        return {
            'type': 'ir.actions.act_window',
            'name': 'Proceso Almacenamiento',
            'res_model': 'megastock.proceso.almacenamiento',
            'res_id': almacenamiento.id,
            'view_mode': 'form',
            'target': 'current',
        }


class ProcesoEmpaqueLine(models.Model):
    _name = 'megastock.proceso.empaque.line'
    _description = 'Línea de Material Empaque'

    empaque_id = fields.Many2one(
        'megastock.proceso.empaque',
        string='Empaque',
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


class ProcesoEmpaquePersonal(models.Model):
    _name = 'megastock.proceso.empaque.personal'
    _description = 'Personal de Empaque'

    empaque_id = fields.Many2one(
        'megastock.proceso.empaque',
        string='Empaque',
        required=True,
        ondelete='cascade'
    )
    empleado_id = fields.Many2one(
        'hr.employee',
        string='Nombre Personal',
        required=True
    )
    hora_inicial = fields.Datetime(string='Hora Inicial')
    hora_final = fields.Datetime(string='Hora Final')
    total_horas = fields.Float(
        string='Total Horas',
        compute='_compute_total_horas',
        store=True,
        digits=(16, 2)
    )
    cantidad_empacada = fields.Float(string='Cantidad Empacada', digits=(16, 2))
    paquetes = fields.Integer(string='Paquetes')
    papel_empaque = fields.Char(string='Papel Empaque')
    nota = fields.Text(string='Nota')
    fecha_entrega = fields.Date(string='Fecha Entrega')

    @api.depends('hora_inicial', 'hora_final')
    def _compute_total_horas(self):
        for record in self:
            if record.hora_inicial and record.hora_final:
                delta = record.hora_final - record.hora_inicial
                record.total_horas = delta.total_seconds() / 3600.0
            else:
                record.total_horas = 0.0
