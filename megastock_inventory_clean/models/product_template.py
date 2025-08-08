# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    # Campos adicionales para control de inventarios MEGASTOCK
    stock_location_id = fields.Many2one(
        'stock.location',
        string='Ubicación Preferida',
        help='Ubicación preferida para almacenar este producto'
    )
    
    consumption_rate = fields.Float(
        string='Tasa de Consumo (por día)',
        help='Cantidad promedio consumida por día'
    )
    
    last_consumption_date = fields.Date(
        string='Última Fecha de Consumo',
        compute='_compute_consumption_info',
        store=True
    )
    
    total_consumed_month = fields.Float(
        string='Consumido Este Mes',
        compute='_compute_consumption_info',
        help='Total consumido en el mes actual'
    )
    
    stock_rotation_days = fields.Float(
        string='Días de Rotación',
        compute='_compute_stock_rotation',
        help='Días estimados para agotar el stock actual'
    )
    
    critical_stock_level = fields.Boolean(
        string='Nivel Crítico',
        compute='_compute_stock_alerts',
        help='Producto en nivel de stock crítico'
    )
    
    @api.depends('product_variant_ids.stock_quant_ids')
    def _compute_consumption_info(self):
        """Computar información de consumo"""
        for template in self:
            # Buscar consumos del mes actual
            consumptions = self.env['megastock.material.consumption'].search([
                ('product_id', 'in', template.product_variant_ids.ids),
                ('date', '>=', fields.Date.today().replace(day=1))
            ])
            
            if consumptions:
                template.last_consumption_date = max(consumptions.mapped('date')).date()
                template.total_consumed_month = sum(consumptions.mapped('quantity'))
            else:
                template.last_consumption_date = False
                template.total_consumed_month = 0.0
    
    @api.depends('qty_available', 'consumption_rate')
    def _compute_stock_rotation(self):
        """Computar días de rotación de stock"""
        for template in self:
            if template.consumption_rate > 0 and template.qty_available > 0:
                template.stock_rotation_days = template.qty_available / template.consumption_rate
            else:
                template.stock_rotation_days = 0.0
    
    @api.depends('qty_available', 'stock_rotation_days')
    def _compute_stock_alerts(self):
        """Computar alertas de stock"""
        for template in self:
            # Considerar crítico si quedan menos de 7 días de stock
            template.critical_stock_level = (
                template.stock_rotation_days > 0 and 
                template.stock_rotation_days < 7
            )
    
    def action_view_consumption_history(self):
        """Ver historial de consumos de este producto"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'Consumos - {self.name}',
            'res_model': 'megastock.material.consumption',
            'view_mode': 'tree,form',
            'domain': [('product_id', 'in', self.product_variant_ids.ids)],
            'context': {'default_product_id': self.product_variant_ids[0].id if self.product_variant_ids else False}
        }
    
    def action_request_material_transfer(self):
        """Solicitar transferencia de este material"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Solicitar Material',
            'res_model': 'megastock.material.transfer.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_line_ids': [(0, 0, {
                    'product_id': self.product_variant_ids[0].id if self.product_variant_ids else False,
                    'uom_id': self.uom_id.id,
                    'location_src_id': self.stock_location_id.id if self.stock_location_id else False,
                })]
            }
        }