# -*- coding: utf-8 -*-

from odoo import models, fields, api

class RequiereDoblezWizard(models.TransientModel):
    _name = 'megastock.requiere.doblez.wizard'
    _description = 'Wizard - ¿Requiere Doblez?'

    microcorrugado_id = fields.Many2one(
        'megastock.proceso.microcorrugado',
        string='Proceso Microcorrugado',
        required=True
    )

    def action_si_requiere_doblez(self):
        """Usuario indica que SÍ requiere doblez - Crear proceso Dobladora"""
        self.ensure_one()

        # Crear el proceso Dobladora
        dobladora = self.env['megastock.proceso.dobladora'].create({
            'work_order_id': self.microcorrugado_id.work_order_id.id,
            'fecha_inicio': fields.Datetime.now(),
            'estado': 'iniciado',
        })

        # Actualizar la orden de trabajo
        self.microcorrugado_id.work_order_id.write({
            'estado': 'dobladora',
            'dobladora_id': dobladora.id
        })

        # Abrir el formulario de dobladora
        return {
            'type': 'ir.actions.act_window',
            'name': 'Proceso Dobladora',
            'res_model': 'megastock.proceso.dobladora',
            'res_id': dobladora.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_no_requiere_doblez(self):
        """Usuario indica que NO requiere doblez - Continuar con siguiente proceso"""
        self.ensure_one()

        # Por ahora, solo retornamos a la orden de trabajo
        # Aquí puedes agregar el siguiente proceso cuando lo definas
        return {
            'type': 'ir.actions.act_window',
            'name': 'Orden de Trabajo',
            'res_model': 'megastock.work.order',
            'res_id': self.microcorrugado_id.work_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
