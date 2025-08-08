# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    # Campos adicionales para MEGASTOCK
    megastock_transfer_type = fields.Selection([
        ('reception', 'Recepción Materias Primas'),
        ('production', 'Transferencia a Producción'),
        ('quality', 'Control de Calidad'),
        ('shipment', 'Envío Productos Terminados'),
        ('internal', 'Transferencia Interna'),
    ], string='Tipo de Transferencia MEGASTOCK', compute='_compute_megastock_transfer_type')
    
    requires_quality_check = fields.Boolean(
        string='Requiere Control de Calidad',
        compute='_compute_quality_requirements'
    )
    
    quality_status = fields.Selection([
        ('pending', 'Pendiente'),
        ('in_progress', 'En Proceso'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado'),
    ], string='Estado de Calidad', default='pending')
    
    @api.depends('picking_type_id', 'location_id', 'location_dest_id')
    def _compute_megastock_transfer_type(self):
        """Determinar tipo de transferencia MEGASTOCK"""
        for picking in self:
            if picking.picking_type_id.code == 'incoming':
                picking.megastock_transfer_type = 'reception'
            elif picking.picking_type_id.code == 'outgoing':
                picking.megastock_transfer_type = 'shipment'
            elif 'wip' in picking.location_dest_id.name.lower():
                picking.megastock_transfer_type = 'production'
            elif 'quality' in picking.location_dest_id.name.lower():
                picking.megastock_transfer_type = 'quality'
            else:
                picking.megastock_transfer_type = 'internal'
    
    @api.depends('move_ids', 'megastock_transfer_type')
    def _compute_quality_requirements(self):
        """Determinar si requiere control de calidad"""
        for picking in self:
            # Recepciones de materias primas siempre requieren QC
            if picking.megastock_transfer_type == 'reception':
                picking.requires_quality_check = True
            # Transferencias a producción de materiales críticos
            elif picking.megastock_transfer_type == 'production':
                critical_materials = picking.move_ids.filtered(
                    lambda m: m.product_id.megastock_category == 'materias_primas' and
                    any(word in m.product_id.name.lower() for word in ['kraft', 'tinta'])
                )
                picking.requires_quality_check = bool(critical_materials)
            else:
                picking.requires_quality_check = False
    
    def button_validate(self):
        """Override para manejar control de calidad"""
        # Si requiere QC y no está aprobado, mover a cuarentena
        if self.requires_quality_check and self.quality_status != 'approved':
            quarantine_location = self.env.ref('megastock_inventory_clean.stock_location_quarantine', False)
            if quarantine_location:
                for move in self.move_ids:
                    move.location_dest_id = quarantine_location.id
        
        return super().button_validate()
    
    def action_quality_approve(self):
        """Aprobar control de calidad"""
        self.quality_status = 'approved'
        
        # Si está en cuarentena, mover a ubicación correcta
        if any('quarantine' in move.location_dest_id.name.lower() for move in self.move_ids):
            for move in self.move_ids:
                correct_location = self._get_correct_location(move.product_id)
                if correct_location:
                    # Crear nuevo movimiento para sacar de cuarentena
                    self.env['stock.move'].create({
                        'name': f'QC Approved: {move.product_id.name}',
                        'product_id': move.product_id.id,
                        'product_uom_qty': move.quantity_done,
                        'product_uom': move.product_uom.id,
                        'location_id': move.location_dest_id.id,
                        'location_dest_id': correct_location.id,
                        'origin': f'QC-{self.name}',
                    })._action_confirm()._action_assign()._action_done()
    
    def action_quality_reject(self):
        """Rechazar control de calidad"""
        self.quality_status = 'rejected'
        
        # Mover a desperdicios
        scrap_location = self.env.ref('megastock_inventory_clean.stock_location_scrap', False)
        if scrap_location:
            for move in self.move_ids:
                if move.quantity_done > 0:
                    self.env['stock.move'].create({
                        'name': f'QC Rejected: {move.product_id.name}',
                        'product_id': move.product_id.id,
                        'product_uom_qty': move.quantity_done,
                        'product_uom': move.product_uom.id,
                        'location_id': move.location_dest_id.id,
                        'location_dest_id': scrap_location.id,
                        'origin': f'QC-REJECT-{self.name}',
                    })._action_confirm()._action_assign()._action_done()
    
    def _get_correct_location(self, product):
        """Obtener ubicación correcta según el producto"""
        if product.megastock_category == 'materias_primas':
            if product.material_type == 'kraft':
                return self.env.ref('megastock_inventory_clean.stock_location_kraft', False)
            elif 'medium' in product.name.lower():
                return self.env.ref('megastock_inventory_clean.stock_location_medium', False)
            elif 'liner' in product.name.lower():
                return self.env.ref('megastock_inventory_clean.stock_location_liner', False)
            elif 'tinta' in product.name.lower():
                return self.env.ref('megastock_inventory_clean.stock_location_inks_cmyk', False)
            elif any(word in product.name.lower() for word in ['almidon', 'pva']):
                return self.env.ref('megastock_inventory_clean.stock_location_adhesives', False)
        
        return self.env.ref('megastock_inventory_clean.stock_location_raw_materials', False)


class StockMove(models.Model):
    _inherit = 'stock.move'
    
    # Campos adicionales
    consumption_type = fields.Selection([
        ('production', 'Consumo Producción'),
        ('maintenance', 'Mantenimiento'),
        ('quality', 'Control Calidad'),
        ('waste', 'Desperdicio'),
    ], string='Tipo de Consumo')
    
    workcenter_id = fields.Many2one(
        'mrp.workcenter',
        string='Centro de Trabajo',
        help='Centro de trabajo que consume el material'
    )
    
    cost_per_unit = fields.Float(
        string='Costo por Unidad',
        related='product_id.standard_price'
    )
    
    total_cost = fields.Float(
        string='Costo Total',
        compute='_compute_total_cost'
    )
    
    @api.depends('product_uom_qty', 'cost_per_unit')
    def _compute_total_cost(self):
        """Calcular costo total del movimiento"""
        for move in self:
            move.total_cost = move.product_uom_qty * move.cost_per_unit