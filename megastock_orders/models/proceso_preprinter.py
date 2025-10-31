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

    # Sección COLOR - Tintas
    tinta_ids = fields.One2many(
        'megastock.proceso.preprinter.tinta',
        'preprinter_id',
        string='Tintas'
    )

    # Sección DESPERDICIOS
    cantidad_corrugada = fields.Float(string='Cantidad Corrugada', default=0.0)
    cuadre = fields.Float(string='Cuadre', default=0.0)
    operativo_tinta_mala = fields.Float(string='Operativo / Tinta Mala', default=0.0)
    caida_maltrato_transportacion = fields.Float(string='Caída Maltrato x Transportación', default=0.0)
    maltrato_montacargas = fields.Float(string='Maltrato a Montacargas', default=0.0)
    combada = fields.Float(string='Combada', default=0.0)
    otros_desperdicios = fields.Float(string='Otros', default=0.0)
    suma_total_desperdicios = fields.Float(string='Suma Total Desperdicios', default=0.0)

    # Sección PLANCHAS PROCESADAS
    planchas_procesadas = fields.Integer(string='Planchas Procesadas', default=0)

    # Sección PERSONAL FLEXOGRAFÍA
    personal_ids = fields.One2many(
        'megastock.proceso.preprinter.personal',
        'preprinter_id',
        string='Personal Flexografía'
    )

    observaciones = fields.Text(string='Observaciones')

    def _calcular_suma_desperdicios(self):
        """Calcula la suma total de desperdicios"""
        return (
            (self.cantidad_corrugada or 0.0) +
            (self.cuadre or 0.0) +
            (self.operativo_tinta_mala or 0.0) +
            (self.caida_maltrato_transportacion or 0.0) +
            (self.maltrato_montacargas or 0.0) +
            (self.combada or 0.0) +
            (self.otros_desperdicios or 0.0)
        )

    @api.model
    def create(self, vals):
        record = super(ProcesoPreprinter, self).create(vals)
        record.suma_total_desperdicios = record._calcular_suma_desperdicios()
        return record

    def write(self, vals):
        res = super(ProcesoPreprinter, self).write(vals)
        campos_desperdicios = ['cantidad_corrugada', 'cuadre', 'operativo_tinta_mala',
                               'caida_maltrato_transportacion', 'maltrato_montacargas',
                               'combada', 'otros_desperdicios']
        if any(campo in vals for campo in campos_desperdicios):
            for record in self:
                suma = record._calcular_suma_desperdicios()
                print(f"========> CALCULANDO SUMA DESPERDICIOS: {suma}")
                super(ProcesoPreprinter, record).write({'suma_total_desperdicios': suma})
        return res

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


class ProcesoPreprinterTinta(models.Model):
    _name = 'megastock.proceso.preprinter.tinta'
    _description = 'Línea de Tinta para Preprinter'

    preprinter_id = fields.Many2one(
        'megastock.proceso.preprinter',
        string='Preprinter',
        required=True,
        ondelete='cascade'
    )
    tinta_id = fields.Many2one(
        'product.product',
        string='Tinta',
        required=True,
        domain=[('type', 'in', ['product', 'consu'])]
    )
    porcentaje = fields.Float(
        string='%',
        default=0.0
    )
    peso_inicial = fields.Float(
        string='Peso Inicial'
    )
    peso_final = fields.Float(
        string='Peso Final'
    )
    consumo_real = fields.Float(
        string='Consumo Real',
        compute='_compute_consumo_real',
        store=True
    )
    viscosidad = fields.Float(
        string='Viscosidad'
    )
    ph = fields.Float(
        string='PH'
    )

    @api.depends('peso_inicial', 'peso_final')
    def _compute_consumo_real(self):
        for record in self:
            record.consumo_real = record.peso_inicial - record.peso_final


class ProcesoPreprinterPersonal(models.Model):
    _name = 'megastock.proceso.preprinter.personal'
    _description = 'Personal Flexografía Preprinter'

    preprinter_id = fields.Many2one(
        'megastock.proceso.preprinter',
        string='Preprinter',
        required=True,
        ondelete='cascade'
    )
    empleado_id = fields.Many2one(
        'hr.employee',
        string='Empleado',
        required=True
    )
    turno = fields.Selection([
        ('manana', 'Mañana'),
        ('tarde', 'Tarde'),
        ('noche', 'Noche'),
    ], string='Turno')
    tarea_hora_inicio = fields.Datetime(string='Tarea - Hora Inicio')
    tarea_hora_final = fields.Datetime(string='Tarea - Hora Final')
    fondo_hora_inicio = fields.Datetime(string='Fondo - Hora Inicio')
    fondo_hora_final = fields.Datetime(string='Fondo - Hora Final')
