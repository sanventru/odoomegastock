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
    materia_prima_ids = fields.One2many(
        'megastock.proceso.microcorrugado.materia.prima',
        'microcorrugado_id',
        string='Materia Prima'
    )
    tiro_ids = fields.One2many(
        'megastock.proceso.microcorrugado.tiro',
        'microcorrugado_id',
        string='TIRO'
    )
    retiro_ids = fields.One2many(
        'megastock.proceso.microcorrugado.retiro',
        'microcorrugado_id',
        string='RETIRO'
    )
    personal_ids = fields.One2many(
        'megastock.proceso.microcorrugado.personal',
        'microcorrugado_id',
        string='Personal de Corrugación'
    )

    # Cuadre Inicio de Corrida
    cuadre_empalme = fields.Float(string='Empalme', digits=(16, 2))
    cuadre_operativo = fields.Float(string='Operativo', digits=(16, 2))
    cuadre_causa_operativo = fields.Text(string='Causa Operativo')
    cuadre_otros_especifique = fields.Text(string='Otros Especifique')

    # Sumatoria Total del Desperdicio y Cantidad Entregada
    sumatoria_total_desperdicios = fields.Float(string='Sumatoria Total del Desperdicio', digits=(16, 2))
    cantidad_entregada = fields.Float(string='Cantidad Entregada', digits=(16, 2))

    observaciones = fields.Text(string='Observaciones')

    def name_get(self):
        result = []
        for record in self:
            name = f"Microcorrugado - {record.work_order_id.numero_orden}"
            result.append((record.id, name))
        return result

    def action_finalizar(self):
        """Finalizar el proceso Microcorrugado e iniciar el siguiente proceso según configuración"""
        if self.estado == 'finalizado':
            raise UserError('Este proceso ya ha sido finalizado.')

        # Finalizar microcorrugado
        self.write({
            'estado': 'finalizado',
            'fecha_fin': fields.Datetime.now()
        })

        # Verificar si requiere doblez
        if self.work_order_id.requiere_doblez:
            # Iniciar proceso Dobladora
            dobladora = self.env['megastock.proceso.dobladora'].create({
                'work_order_id': self.work_order_id.id,
                'fecha_inicio': fields.Datetime.now(),
                'estado': 'iniciado',
            })

            self.work_order_id.write({
                'estado': 'dobladora',
                'dobladora_id': dobladora.id
            })

            return {
                'type': 'ir.actions.act_window',
                'name': 'Proceso Dobladora',
                'res_model': 'megastock.proceso.dobladora',
                'res_id': dobladora.id,
                'view_mode': 'form',
                'target': 'current',
            }

        # No requiere doblez, verificar si algún producto tiene ceja > 0
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
            # No requiere doblez ni ceja, ir directo a Empaque
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


class ProcesoMicrocorrugadoMateriaPrima(models.Model):
    _name = 'megastock.proceso.microcorrugado.materia.prima'
    _description = 'Materia Prima Microcorrugado'

    microcorrugado_id = fields.Many2one(
        'megastock.proceso.microcorrugado',
        string='Microcorrugado',
        required=True,
        ondelete='cascade'
    )
    codigo_imp = fields.Char(string='Código IMP')
    ancho = fields.Float(string='Ancho')
    gramaje = fields.Float(string='Gramaje')
    peso_inicial = fields.Float(string='P. Inicial', digits=(16, 2))
    peso_final = fields.Float(string='P. Final', digits=(16, 2))
    consumo_kg = fields.Float(
        string='Consumo Kg',
        compute='_compute_consumo_kg',
        store=True,
        digits=(16, 2)
    )
    metros_producidos = fields.Float(string='Metros Producidos', digits=(16, 2))
    medium_tiro_corru_1 = fields.Float(string='Medium Tiro Corru 1')
    medium_tiro_corru_2 = fields.Float(string='Medium Tiro Corru 2')
    medium_tiro_corru_3 = fields.Float(string='Medium Tiro Corru 3')
    medium_tiro_corru_4 = fields.Float(string='Medium Tiro Corru 4')

    @api.depends('peso_inicial', 'peso_final')
    def _compute_consumo_kg(self):
        for record in self:
            if record.peso_inicial and record.peso_final:
                record.consumo_kg = record.peso_inicial - record.peso_final
            else:
                record.consumo_kg = 0.0


class ProcesoMicrocorrugadoTiro(models.Model):
    _name = 'megastock.proceso.microcorrugado.tiro'
    _description = 'TIRO Microcorrugado'

    microcorrugado_id = fields.Many2one(
        'megastock.proceso.microcorrugado',
        string='Microcorrugado',
        required=True,
        ondelete='cascade'
    )
    medium_tiro_corru_1 = fields.Float(string='Medium Tiro Corru 1')
    medium_tiro_corru_2 = fields.Float(string='Medium Tiro Corru 2')
    medium_tiro_corru_3 = fields.Float(string='Medium Tiro Corru 3')
    medium_tiro_corru_4 = fields.Float(string='Medium Tiro Corru 4')


class ProcesoMicrocorrugadoRetiro(models.Model):
    _name = 'megastock.proceso.microcorrugado.retiro'
    _description = 'RETIRO Microcorrugado'

    microcorrugado_id = fields.Many2one(
        'megastock.proceso.microcorrugado',
        string='Microcorrugado',
        required=True,
        ondelete='cascade'
    )
    medium_retiro_corru_1 = fields.Float(string='Medium ReTiro Corru 1')
    medium_retiro_corru_2 = fields.Float(string='Medium ReTiro Corru 2')
    medium_retiro_corru_3 = fields.Float(string='Medium ReTiro Corru 3')
    medium_retiro_corru_4 = fields.Float(string='Medium ReTiro Corru 4')


class ProcesoMicrocorrugadoPersonal(models.Model):
    _name = 'megastock.proceso.microcorrugado.personal'
    _description = 'Personal de Corrugación Microcorrugado'

    microcorrugado_id = fields.Many2one(
        'megastock.proceso.microcorrugado',
        string='Microcorrugado',
        required=True,
        ondelete='cascade'
    )
    empleado_id = fields.Many2one(
        'hr.employee',
        string='Nombre Empleado',
        required=True
    )
    turno = fields.Selection([
        ('manana', 'Mañana'),
        ('tarde', 'Tarde'),
        ('noche', 'Noche')
    ], string='Turno')
    hora_ingreso = fields.Datetime(string='Hora Ingreso')
    hora_final = fields.Datetime(string='Hora Final')
    horas_total = fields.Float(
        string='Horas Total',
        compute='_compute_horas_total',
        store=True,
        digits=(16, 2)
    )

    @api.depends('hora_ingreso', 'hora_final')
    def _compute_horas_total(self):
        for record in self:
            if record.hora_ingreso and record.hora_final:
                delta = record.hora_final - record.hora_ingreso
                record.horas_total = delta.total_seconds() / 3600.0
            else:
                record.horas_total = 0.0
