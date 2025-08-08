# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime


class MaterialTransferWizard(models.TransientModel):
    _name = 'megastock.material.transfer.wizard'
    _description = 'Formulario Digitalizado: EGRESO MATERIA PRIMA'
    
    # Cabecera del formulario
    transfer_date = fields.Datetime(
        string='Fecha y Hora',
        default=fields.Datetime.now,
        required=True
    )
    
    operator_id = fields.Many2one(
        'res.users',
        string='Operador',
        default=lambda self: self.env.user,
        required=True
    )
    
    workcenter_id = fields.Many2one(
        'mrp.workcenter',
        string='Centro de Trabajo',
        required=True,
        help='Centro de trabajo que solicita el material'
    )
    
    production_order_id = fields.Many2one(
        'mrp.production',
        string='Orden de Producción',
        help='Orden de producción asociada (opcional)'
    )
    
    work_order_id = fields.Many2one(
        'mrp.workorder',
        string='Orden de Trabajo',
        help='Orden de trabajo específica (opcional)'
    )
    
    transfer_type = fields.Selection([
        ('production', 'Para Producción'),
        ('maintenance', 'Para Mantenimiento'),
        ('quality', 'Para Control de Calidad'),
        ('other', 'Otro'),
    ], string='Tipo de Egreso', default='production', required=True)
    
    notes = fields.Text(string='Observaciones')
    
    # Líneas de materiales
    line_ids = fields.One2many(
        'megastock.material.transfer.line',
        'wizard_id',
        string='Materiales a Transferir'
    )
    
    # Estado del formulario
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmado'),
        ('done', 'Transferido'),
        ('cancelled', 'Cancelado'),
    ], string='Estado', default='draft')
    
    # Información de autorización
    authorized_by = fields.Many2one(
        'res.users',
        string='Autorizado por',
        help='Usuario que autoriza la transferencia'
    )
    
    authorization_date = fields.Datetime(string='Fecha de Autorización')
    
    # Picking generado
    picking_id = fields.Many2one(
        'stock.picking',
        string='Transferencia Generada',
        readonly=True
    )
    
    def action_add_material_line(self):
        """Acción para agregar línea de material"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Seleccionar Material',
            'res_model': 'megastock.material.selection.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_transfer_wizard_id': self.id}
        }
    
    def action_confirm_transfer(self):
        """Confirmar el formulario de egreso"""
        if not self.line_ids:
            raise ValidationError(_('Debe agregar al menos un material para transferir.'))
        
        # Validar disponibilidad de stock
        for line in self.line_ids:
            available_qty = self._get_available_quantity(
                line.product_id, 
                line.location_src_id, 
                line.lot_id
            )
            if available_qty < line.quantity:
                raise ValidationError(_(
                    'Stock insuficiente para %s.\n'
                    'Solicitado: %s %s\n'
                    'Disponible: %s %s'
                ) % (
                    line.product_id.name,
                    line.quantity, line.uom_id.name,
                    available_qty, line.uom_id.name
                ))
        
        self.state = 'confirmed'
        
        # Crear picking de transferencia
        self._create_stock_picking()
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'megastock.material.transfer.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def action_execute_transfer(self):
        """Ejecutar la transferencia física"""
        if self.state != 'confirmed':
            raise ValidationError(_('Solo se pueden ejecutar transferencias confirmadas.'))
        
        if not self.picking_id:
            raise ValidationError(_('No se ha generado la transferencia de stock.'))
        
        # Validar autorización si es requerida
        if self._requires_authorization() and not self.authorized_by:
            raise ValidationError(_('Esta transferencia requiere autorización.'))
        
        # Procesar el picking
        self.picking_id.action_confirm()
        self.picking_id.action_assign()
        
        # Validar automáticamente si todo está disponible
        if self.picking_id.state == 'assigned':
            for move in self.picking_id.move_ids:
                move.quantity_done = move.product_uom_qty
            
            self.picking_id.button_validate()
            
            self.state = 'done'
            
            # Registrar en historial de consumos
            self._register_consumption_history()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Transferencia Completada'),
                    'message': _('Los materiales han sido transferidos exitosamente.'),
                    'type': 'success'
                }
            }
        else:
            raise ValidationError(_('No se pudo completar la transferencia. Verifique la disponibilidad.'))
    
    def action_cancel_transfer(self):
        """Cancelar transferencia"""
        if self.picking_id and self.picking_id.state not in ['done', 'cancel']:
            self.picking_id.action_cancel()
        
        self.state = 'cancelled'
    
    def _create_stock_picking(self):
        """Crear picking de transferencia de stock"""
        # Determinar tipo de picking
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'internal'),
            ('warehouse_id', '=', self.env.ref('stock.warehouse0').id)
        ], limit=1)
        
        if not picking_type:
            raise ValidationError(_('No se encontró un tipo de picking interno.'))
        
        # Crear picking
        picking_vals = {
            'picking_type_id': picking_type.id,
            'location_id': self.line_ids[0].location_src_id.id,  # Primera ubicación como origen
            'location_dest_id': self._get_destination_location().id,
            'origin': f'EGRESO-MP-{self.id}',
            'note': f'Egreso de materiales para {self.workcenter_id.name}\nOperador: {self.operator_id.name}\nObservaciones: {self.notes or ""}',
            'user_id': self.operator_id.id,
        }
        
        picking = self.env['stock.picking'].create(picking_vals)
        
        # Crear movimientos de stock
        for line in self.line_ids:
            move_vals = {
                'name': line.product_id.name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,
                'product_uom': line.uom_id.id,
                'location_id': line.location_src_id.id,
                'location_dest_id': self._get_destination_location().id,
                'picking_id': picking.id,
                'origin': picking.origin,
            }
            
            # Agregar información de lote si existe
            if line.lot_id:
                move_vals['restrict_lot_id'] = line.lot_id.id
            
            self.env['stock.move'].create(move_vals)
        
        self.picking_id = picking.id
    
    def _get_destination_location(self):
        """Obtener ubicación de destino según el tipo de transferencia"""
        if self.transfer_type == 'production':
            # Ubicación WIP del centro de trabajo
            wip_location = self.env['stock.location'].search([
                ('name', 'ilike', f'WIP - {self.workcenter_id.name}')
            ], limit=1)
            
            if wip_location:
                return wip_location
            else:
                # Ubicación WIP general
                return self.env.ref('megastock_inventory_clean.stock_location_wip')
        
        elif self.transfer_type == 'quality':
            return self.env.ref('megastock_inventory_clean.stock_location_quality_control')
        
        elif self.transfer_type == 'maintenance':
            # Ubicación de mantenimiento (crear si no existe)
            maintenance_location = self.env['stock.location'].search([
                ('name', '=', 'Mantenimiento')
            ], limit=1)
            
            if not maintenance_location:
                maintenance_location = self.env['stock.location'].create({
                    'name': 'Mantenimiento',
                    'location_id': self.env.ref('megastock_inventory_clean.stock_location_megastock_main').id,
                    'usage': 'internal',
                    'barcode': 'MAINT',
                })
            
            return maintenance_location
        
        else:
            # Ubicación general
            return self.env.ref('stock.stock_location_stock')
    
    def _get_available_quantity(self, product, location, lot=None):
        """Obtener cantidad disponible de un producto en una ubicación"""
        domain = [
            ('product_id', '=', product.id),
            ('location_id', '=', location.id),
        ]
        
        if lot:
            domain.append(('lot_id', '=', lot.id))
        
        quants = self.env['stock.quant'].search(domain)
        return sum(quants.mapped('quantity'))
    
    def _requires_authorization(self):
        """Verificar si la transferencia requiere autorización"""
        # Requerir autorización para cantidades grandes o materiales críticos
        for line in self.line_ids:
            # Materiales críticos (papel > 1 tonelada)
            if line.product_id.megastock_category == 'materias_primas':
                if line.uom_id.category_id.name == 'Weight' and 'ton' in line.uom_id.name.lower():
                    if line.quantity > 1.0:  # Más de 1 tonelada
                        return True
        
        return False
    
    def _register_consumption_history(self):
        """Registrar en historial de consumos"""
        for line in self.line_ids:
            consumption_vals = {
                'date': self.transfer_date,
                'product_id': line.product_id.id,
                'quantity': line.quantity,
                'uom_id': line.uom_id.id,
                'location_src_id': line.location_src_id.id,
                'location_dest_id': self._get_destination_location().id,
                'workcenter_id': self.workcenter_id.id,
                'operator_id': self.operator_id.id,
                'production_order_id': self.production_order_id.id if self.production_order_id else False,
                'work_order_id': self.work_order_id.id if self.work_order_id else False,
                'lot_id': line.lot_id.id if line.lot_id else False,
                'transfer_type': self.transfer_type,
            }
            
            self.env['megastock.material.consumption'].create(consumption_vals)


class MaterialTransferLine(models.TransientModel):
    _name = 'megastock.material.transfer.line'
    _description = 'Línea de Transferencia de Material'
    
    wizard_id = fields.Many2one(
        'megastock.material.transfer.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade'
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Material',
        required=True,
        domain=[('megastock_category', '=', 'materias_primas')]
    )
    
    quantity = fields.Float(
        string='Cantidad',
        required=True,
        digits='Product Unit of Measure'
    )
    
    uom_id = fields.Many2one(
        'uom.uom',
        string='Unidad de Medida',
        required=True
    )
    
    location_src_id = fields.Many2one(
        'stock.location',
        string='Ubicación Origen',
        required=True,
        domain=[('usage', '=', 'internal')]
    )
    
    lot_id = fields.Many2one(
        'stock.lot',
        string='Lote',
        domain="[('product_id', '=', product_id)]"
    )
    
    available_qty = fields.Float(
        string='Cantidad Disponible',
        compute='_compute_available_qty',
        digits='Product Unit of Measure'
    )
    
    notes = fields.Char(string='Observaciones')
    
    @api.depends('product_id', 'location_src_id', 'lot_id')
    def _compute_available_qty(self):
        """Computar cantidad disponible"""
        for line in self:
            if line.product_id and line.location_src_id:
                domain = [
                    ('product_id', '=', line.product_id.id),
                    ('location_id', '=', line.location_src_id.id),
                ]
                
                if line.lot_id:
                    domain.append(('lot_id', '=', line.lot_id.id))
                
                quants = self.env['stock.quant'].search(domain)
                line.available_qty = sum(quants.mapped('quantity'))
            else:
                line.available_qty = 0.0
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Cambiar UOM por defecto al cambiar producto"""
        if self.product_id:
            self.uom_id = self.product_id.uom_id.id
            
            # Sugerir ubicación más común para este producto
            common_location = self.env['stock.quant'].search([
                ('product_id', '=', self.product_id.id),
                ('quantity', '>', 0)
            ], limit=1).location_id
            
            if common_location:
                self.location_src_id = common_location.id


class MaterialConsumption(models.Model):
    _name = 'megastock.material.consumption'
    _description = 'Historial de Consumo de Materiales'
    _order = 'date desc'
    
    date = fields.Datetime(string='Fecha', required=True)
    product_id = fields.Many2one('product.product', string='Producto', required=True)
    quantity = fields.Float(string='Cantidad Consumida', required=True)
    uom_id = fields.Many2one('uom.uom', string='Unidad de Medida', required=True)
    location_src_id = fields.Many2one('stock.location', string='Origen')
    location_dest_id = fields.Many2one('stock.location', string='Destino')
    workcenter_id = fields.Many2one('mrp.workcenter', string='Centro de Trabajo')
    operator_id = fields.Many2one('res.users', string='Operador')
    production_order_id = fields.Many2one('mrp.production', string='Orden de Producción')
    work_order_id = fields.Many2one('mrp.workorder', string='Orden de Trabajo')
    lot_id = fields.Many2one('stock.lot', string='Lote')
    transfer_type = fields.Selection([
        ('production', 'Producción'),
        ('maintenance', 'Mantenimiento'),
        ('quality', 'Control de Calidad'),
        ('other', 'Otro'),
    ], string='Tipo')
    
    cost_total = fields.Float(
        string='Costo Total',
        compute='_compute_cost_total',
        store=True
    )
    
    @api.depends('product_id', 'quantity')
    def _compute_cost_total(self):
        """Calcular costo total del consumo"""
        for record in self:
            record.cost_total = record.quantity * record.product_id.standard_price