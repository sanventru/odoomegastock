# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class StockLot(models.Model):
    _inherit = 'stock.lot'

    # === INFORMACIÓN DE PRODUCCIÓN ===
    production_id = fields.Many2one(
        'mrp.production',
        'Orden de Producción',
        help="Orden de producción que generó este lote"
    )
    
    workorder_id = fields.Many2one(
        'mrp.workorder',
        'Orden de Trabajo',
        help="Orden de trabajo específica que generó este lote"
    )
    
    production_line = fields.Selection(
        related='workorder_id.production_line',
        string='Línea de Producción',
        store=True,
        help="Línea de producción donde se fabricó este lote"
    )

    # === INFORMACIÓN DE TRAZABILIDAD ===
    pallet_number = fields.Char(
        'Número de Pallet',
        help="Número de pallet donde se encuentra este lote"
    )
    
    batch_code = fields.Char(
        'Código de Lote de Producción',
        help="Código del lote de producción del cual forma parte"
    )
    
    production_date = fields.Datetime(
        'Fecha de Producción',
        help="Fecha y hora exacta de producción"
    )
    
    shift = fields.Selection([
        ('morning', 'Mañana'), 
        ('afternoon', 'Tarde'), 
        ('night', 'Noche')
    ], 'Turno de Producción',
    help="Turno en el que se produjo este lote")

    # === PERSONAL RESPONSABLE ===
    operator_id = fields.Many2one(
        'hr.employee',
        'Operador',
        help="Operador responsable de la producción de este lote"
    )
    
    supervisor_id = fields.Many2one(
        'hr.employee', 
        'Supervisor',
        help="Supervisor responsable durante la producción"
    )
    
    quality_inspector_id = fields.Many2one(
        'hr.employee',
        'Inspector de Calidad',
        help="Inspector que validó la calidad del lote"
    )

    # === ESPECIFICACIONES TÉCNICAS ===
    grammage = fields.Float(
        'Gramaje (g/m²)',
        help="Gramaje del material producido"
    )
    
    thickness = fields.Float(
        'Grosor/Espesor (mm)',
        help="Grosor o espesor del material"
    )
    
    moisture = fields.Float(
        'Humedad (%)',
        help="Porcentaje de humedad del material"
    )
    
    resistance_test = fields.Char(
        'Test de Resistencia',
        help="Resultado del test de resistencia aplicado"
    )

    # === DIMENSIONES DEL PRODUCTO ===
    product_length = fields.Float(
        'Largo (mm)',
        help="Largo del producto en este lote"
    )
    
    product_width = fields.Float(
        'Ancho (mm)',
        help="Ancho del producto en este lote"
    )
    
    units_per_package = fields.Integer(
        'Unidades por Paquete',
        help="Cantidad de unidades por paquete en este lote"
    )
    
    total_packages = fields.Integer(
        'Total de Paquetes',
        help="Número total de paquetes en este lote"
    )

    # === ESTADO DE CALIDAD ===
    quality_state = fields.Selection([
        ('draft', 'Sin Inspeccionar'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado'),
        ('quarantine', 'En Cuarentena')
    ], string='Estado de Calidad',
    default='draft',
    help="Estado de control de calidad del lote")
    
    quality_notes = fields.Text(
        'Notas de Calidad',
        help="Observaciones del control de calidad"
    )
    
    rejection_reason = fields.Text(
        'Motivo de Rechazo',
        help="Motivo por el cual el lote fue rechazado"
    )

    # === INFORMACIÓN DE MATERIA PRIMA ===
    raw_material_lots = fields.Many2many(
        'stock.lot',
        'stock_lot_raw_material_rel',
        'finished_lot_id',
        'raw_lot_id',
        string='Lotes de Materia Prima',
        help="Lotes de materia prima utilizados para producir este lote"
    )
    
    supplier_batch = fields.Char(
        'Lote del Proveedor',
        help="Número de lote del proveedor de materia prima"
    )

    # === MÉTODOS COMPUTADOS ===
    
    @api.model
    def create(self, vals):
        """Override para asignar valores automáticos"""
        lot = super().create(vals)
        
        # Si viene de una orden de trabajo, copiar información relevante
        if lot.workorder_id:
            lot._copy_from_workorder()
            
        # Si viene de una producción, copiar información relevante  
        elif lot.production_id:
            lot._copy_from_production()
            
        return lot

    def _copy_from_workorder(self):
        """Copiar información desde la orden de trabajo"""
        if not self.workorder_id:
            return
            
        wo = self.workorder_id
        
        # Copiar información básica
        if not self.production_date and wo.date_start:
            self.production_date = wo.date_start
            
        if not self.pallet_number and wo.pallet_number:
            self.pallet_number = wo.pallet_number
            
        if not self.shift and wo.shift:
            self.shift = wo.shift
            
        if not self.operator_id and wo.operator_name:
            # Buscar empleado por nombre
            employee = self.env['hr.employee'].search([
                ('name', 'ilike', wo.operator_name)
            ], limit=1)
            if employee:
                self.operator_id = employee.id
                
        # Copiar especificaciones técnicas
        if not self.grammage and wo.grammage:
            self.grammage = wo.grammage
            
        if not self.product_length and wo.workcenter_id:
            self.product_length = wo.workcenter_id.product_length
            
        if not self.product_width and wo.workcenter_id:
            self.product_width = wo.workcenter_id.product_width

    def _copy_from_production(self):
        """Copiar información desde la orden de producción"""
        if not self.production_id:
            return
            
        production = self.production_id
        
        # Copiar código de lote
        if not self.batch_code and production.batch_code:
            self.batch_code = production.batch_code
            
        # Copiar dimensiones del producto
        if not self.product_length and production.product_length:
            self.product_length = production.product_length
            
        if not self.product_width and production.product_width:
            self.product_width = production.product_width

    # === ACCIONES ===
    
    def action_approve_quality(self):
        """Aprobar calidad del lote"""
        self.quality_state = 'approved'
        if not self.quality_inspector_id:
            self.quality_inspector_id = self.env.user.employee_id.id
        return True
        
    def action_reject_quality(self):
        """Rechazar calidad del lote"""
        return {
            'name': _('Rechazar Lote'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.lot.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_lot_id': self.id,
            }
        }
        
    def action_quarantine(self):
        """Poner lote en cuarentena"""
        self.quality_state = 'quarantine'
        return True

    def action_view_traceability(self):
        """Ver trazabilidad completa del lote"""
        return {
            'name': _('Trazabilidad del Lote %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'stock.lot',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('mrp_production_lines.view_stock_lot_traceability_form').id,
            'target': 'new',
        }

    def action_print_traceability_label(self):
        """Imprimir etiqueta de trazabilidad"""
        return {
            'type': 'ir.actions.report',
            'report_name': 'mrp_production_lines.stock_lot_traceability_label',
            'report_type': 'qweb-pdf',
            'data': {'ids': [self.id]},
            'context': self.env.context,
        }

    # === BÚSQUEDAS Y FILTROS ===
    
    @api.model
    def search_by_raw_material(self, raw_material_lot):
        """Buscar lotes finales que utilizaron una materia prima específica"""
        return self.search([
            ('raw_material_lots', 'in', [raw_material_lot.id])
        ])
        
    @api.model  
    def search_by_production_line(self, line_type):
        """Buscar lotes por línea de producción"""
        return self.search([
            ('production_line', '=', line_type)
        ])
        
    @api.model
    def search_by_quality_state(self, quality_state):
        """Buscar lotes por estado de calidad"""
        return self.search([
            ('quality_state', '=', quality_state)
        ])
        
    # === REPORTES ===
    
    def get_traceability_info(self):
        """Obtener información completa de trazabilidad"""
        return {
            'lot_name': self.name,
            'product': self.product_id.name,
            'production_date': self.production_date,
            'production_line': dict(self._fields['production_line'].selection).get(self.production_line),
            'operator': self.operator_id.name if self.operator_id else False,
            'supervisor': self.supervisor_id.name if self.supervisor_id else False,
            'quality_inspector': self.quality_inspector_id.name if self.quality_inspector_id else False,
            'quality_state': dict(self._fields['quality_state'].selection).get(self.quality_state),
            'raw_materials': [(rm.name, rm.product_id.name) for rm in self.raw_material_lots],
            'specifications': {
                'grammage': self.grammage,
                'thickness': self.thickness,
                'moisture': self.moisture,
                'dimensions': f"{self.product_length}x{self.product_width}" if self.product_length and self.product_width else False
            }
        }