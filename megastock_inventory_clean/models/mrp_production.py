# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class MrpProduction(models.Model):
    _inherit = 'mrp.production'
    
    # Consumo de materiales automático
    material_consumption_ids = fields.One2many(
        'megastock.material.consumption',
        'production_order_id',
        string='Consumos de Materiales'
    )
    
    total_material_cost = fields.Float(
        string='Costo Total Materiales',
        compute='_compute_material_costs'
    )
    
    @api.depends('material_consumption_ids.cost_total')
    def _compute_material_costs(self):
        """Calcular costo total de materiales"""
        for production in self:
            production.total_material_cost = sum(
                production.material_consumption_ids.mapped('cost_total')
            )
    
    def button_mark_done(self):
        """Override para registrar consumos automáticamente"""
        result = super().button_mark_done()
        
        # Registrar consumos de materiales automáticamente
        self._register_automatic_consumption()
        
        return result
    
    def _register_automatic_consumption(self):
        """Registrar consumo automático de materiales"""
        for move in self.move_raw_ids.filtered(lambda m: m.state == 'done'):
            # Buscar si ya existe un registro de consumo
            existing_consumption = self.env['megastock.material.consumption'].search([
                ('production_order_id', '=', self.id),
                ('product_id', '=', move.product_id.id),
                ('quantity', '=', move.quantity_done)
            ], limit=1)
            
            if not existing_consumption:
                self.env['megastock.material.consumption'].create({
                    'date': fields.Datetime.now(),
                    'product_id': move.product_id.id,
                    'quantity': move.quantity_done,
                    'uom_id': move.product_uom.id,
                    'location_src_id': move.location_id.id,
                    'location_dest_id': move.location_dest_id.id,
                    'production_order_id': self.id,
                    'transfer_type': 'production',
                    'lot_id': move.lot_ids[0].id if move.lot_ids else False,
                })
    
    def action_view_material_consumptions(self):
        """Ver consumos de materiales de esta orden"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'Consumos - {self.name}',
            'res_model': 'megastock.material.consumption',
            'view_mode': 'tree,form',
            'domain': [('production_order_id', '=', self.id)],
            'context': {'default_production_order_id': self.id}
        }


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'
    
    # Consumos específicos por orden de trabajo
    material_requests_ids = fields.One2many(
        'megastock.material.transfer.wizard',
        'work_order_id',
        string='Solicitudes de Material'
    )
    
    def action_request_materials(self):
        """Solicitar materiales para esta orden de trabajo"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'Solicitar Materiales - {self.name}',
            'res_model': 'megastock.material.transfer.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_work_order_id': self.id,
                'default_production_order_id': self.production_id.id,
                'default_workcenter_id': self.workcenter_id.id,
                'default_transfer_type': 'production',
            }
        }