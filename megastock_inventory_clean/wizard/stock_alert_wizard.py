# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class StockAlertWizard(models.TransientModel):
    _name = 'megastock.stock.alert.wizard'
    _description = 'Wizard de Alertas de Stock'
    
    alert_type = fields.Selection([
        ('low_stock', 'Stock Bajo'),
        ('expiry', 'Próximo a Expirar'),
        ('quality_pending', 'Calidad Pendiente'),
    ], string='Tipo de Alerta', default='low_stock', required=True)
    
    def action_generate_alert_report(self):
        """Generar reporte de alertas"""
        if self.alert_type == 'low_stock':
            return self._generate_low_stock_report()
        elif self.alert_type == 'expiry':
            return self._generate_expiry_report()
        elif self.alert_type == 'quality_pending':
            return self._generate_quality_pending_report()
    
    def _generate_low_stock_report(self):
        """Generar reporte de stock bajo"""
        # Buscar productos con stock bajo según reglas de reabastecimiento
        orderpoints = self.env['stock.warehouse.orderpoint'].search([])
        low_stock_products = []
        
        for orderpoint in orderpoints:
            current_qty = orderpoint.product_id.qty_available
            if current_qty <= orderpoint.product_min_qty:
                low_stock_products.append(orderpoint.product_id.id)
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Productos con Stock Bajo',
            'res_model': 'product.template',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', low_stock_products)],
        }
    
    def _generate_expiry_report(self):
        """Generar reporte de productos próximos a expirar"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Productos Próximos a Expirar',
            'res_model': 'stock.quant',
            'view_mode': 'tree,form',
            'domain': [('expiry_alert', '=', True)],
        }
    
    def _generate_quality_pending_report(self):
        """Generar reporte de calidad pendiente"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Control de Calidad Pendiente',
            'res_model': 'stock.quant',
            'view_mode': 'tree,form',
            'domain': [('quality_status', '=', 'pending')],
        }