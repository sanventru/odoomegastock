# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    # === CAMPOS PARA TRAZABILIDAD Y ETIQUETADO ===
    master_pallet_number = fields.Char(
        'N° Pallet Principal', 
        help="Número de pallet principal para toda la orden de producción"
    )
    
    custom_production_code = fields.Char(
        'Código de Producción Personalizado',
        help="Código personalizado para identificación en etiquetas"
    )
    
    internal_reference = fields.Char(
        'Referencia Interna',
        help="Referencia interna adicional para control"
    )
    
    batch_code = fields.Char(
        'Código de Lote',
        help="Código del lote de producción"
    )

    # === INFORMACIÓN DE LÍNEA DE PRODUCCIÓN ===
    production_line = fields.Selection([
        ('papel_periodico', 'Papel Periódico'),
        ('cajas', 'Cajas & Planchas'),
        ('lamina_micro', 'Lámina Micro Corrugada')
    ], string='Línea de Producción',
    compute='_compute_production_line',
    store=True,
    help="Línea de producción determinada por los centros de trabajo de la ruta")

    # === CAMPOS ESPECÍFICOS POR LÍNEA ===
    # Para control de calidad y especificaciones
    quality_specifications = fields.Text(
        'Especificaciones de Calidad',
        help="Especificaciones técnicas y de calidad del producto"
    )
    
    # Dimensiones del producto
    product_length = fields.Float(
        'Largo (mm)',
        help="Largo del producto en milímetros"
    )
    
    product_width = fields.Float(
        'Ancho (mm)', 
        help="Ancho del producto en milímetros"
    )
    
    product_height = fields.Float(
        'Alto (mm)',
        help="Alto/grosor del producto en milímetros"
    )

    # === CONTADORES Y ESTADÍSTICAS ===
    total_pallets = fields.Integer(
        'Total de Pallets',
        compute='_compute_pallet_stats',
        store=True,
        help="Número total de pallets generados en esta producción"
    )
    
    workorder_with_pallets = fields.Integer(
        'Órdenes con Pallet',
        compute='_compute_pallet_stats', 
        store=True,
        help="Número de órdenes de trabajo que tienen asignado número de pallet"
    )

    # === MÉTODOS COMPUTADOS ===
    
    @api.depends('workorder_ids.workcenter_id.production_line_type')
    def _compute_production_line(self):
        """Determinar línea de producción basada en centros de trabajo"""
        for record in self:
            line_types = record.workorder_ids.mapped('workcenter_id.production_line_type')
            # Filtrar valores vacíos
            line_types = [lt for lt in line_types if lt]
            
            if line_types:
                # Si hay diferentes tipos, tomar el más común
                line_counts = {}
                for line_type in line_types:
                    line_counts[line_type] = line_counts.get(line_type, 0) + 1
                
                # Obtener el tipo más frecuente
                record.production_line = max(line_counts, key=line_counts.get)
            else:
                record.production_line = False

    @api.depends('workorder_ids.pallet_number')
    def _compute_pallet_stats(self):
        """Calcular estadísticas de pallets"""
        for record in self:
            workorders_with_pallet = record.workorder_ids.filtered('pallet_number')
            record.workorder_with_pallets = len(workorders_with_pallet)
            
            # Contar pallets únicos
            pallet_numbers = set(workorders_with_pallet.mapped('pallet_number'))
            record.total_pallets = len(pallet_numbers)

    # === ACCIONES Y MÉTODOS ===
    
    def action_generate_pallet_numbers(self):
        """Generar números de pallet automáticamente para órdenes de trabajo"""
        if not self.workorder_ids:
            raise UserError(_('No hay órdenes de trabajo para asignar números de pallet.'))
        
        # Obtener el siguiente número de secuencia para pallets
        sequence = self.env['ir.sequence'].next_by_code('mrp.production.pallet') or '001'
        
        pallet_counter = 1
        for workorder in self.workorder_ids.filtered(lambda w: not w.pallet_number):
            workorder.pallet_number = f"{self.name}-P{pallet_counter:03d}"
            pallet_counter += 1
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Pallets Generados'),
                'message': _('Se generaron %d números de pallet automáticamente.') % (pallet_counter - 1),
                'type': 'success',
            }
        }

    def action_view_workorder_labels(self):
        """Ver/imprimir etiquetas de todas las órdenes de trabajo"""
        if not self.workorder_ids:
            raise UserError(_('No hay órdenes de trabajo para mostrar etiquetas.'))
        
        return {
            'name': _('Etiquetas de Órdenes de Trabajo'),
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.workorder',
            'view_mode': 'tree,form',
            'domain': [('production_id', '=', self.id)],
            'context': {
                'default_production_id': self.id,
                'search_default_production_id': self.id,
            }
        }

    def action_production_efficiency_report(self):
        """Generar reporte de eficiencia de la producción"""
        return {
            'type': 'ir.actions.report',
            'report_name': 'mrp_production_lines.production_efficiency_report',
            'report_type': 'qweb-pdf',
            'data': {'ids': [self.id]},
            'context': self.env.context,
        }

    # === VALIDACIONES ===
    
    @api.constrains('master_pallet_number')
    def _check_master_pallet_unique(self):
        """Validar que el número de pallet principal sea único"""
        for record in self:
            if record.master_pallet_number:
                existing = self.search([
                    ('master_pallet_number', '=', record.master_pallet_number),
                    ('id', '!=', record.id),
                    ('state', '!=', 'cancel')
                ])
                if existing:
                    raise UserError(_(
                        'El número de pallet principal "%s" ya está siendo usado en la orden de producción %s.'
                    ) % (record.master_pallet_number, existing[0].name))

    # === OVERRIDE DE MÉTODOS ESTÁNDAR ===
    
    @api.model
    def create(self, vals):
        """Override para generar códigos automáticos"""
        production = super().create(vals)
        
        # Generar código de producción personalizado si no se proporciona
        if not production.custom_production_code:
            production.custom_production_code = f"PROD-{production.name}"
            
        # Generar código de lote basado en fecha si no se proporciona
        if not production.batch_code:
            date_str = fields.Date.today().strftime('%Y%m%d')
            sequence = self.env['ir.sequence'].next_by_code('mrp.production.batch') or '001'
            production.batch_code = f"LOTE-{date_str}-{sequence}"
            
        return production

    def write(self, vals):
        """Override para validaciones adicionales"""
        result = super().write(vals)
        
        # Si se cambia el producto, actualizar dimensiones automáticamente
        if 'product_id' in vals:
            for record in self:
                if record.product_id:
                    # Buscar dimensiones en atributos del producto si existen
                    attributes = record.product_id.product_template_attribute_value_ids
                    for attr in attributes:
                        attr_name = attr.attribute_id.name.lower()
                        if 'largo' in attr_name or 'length' in attr_name:
                            try:
                                record.product_length = float(attr.name)
                            except:
                                pass
                        elif 'ancho' in attr_name or 'width' in attr_name:
                            try:
                                record.product_width = float(attr.name)
                            except:
                                pass
                        elif 'alto' in attr_name or 'height' in attr_name or 'grosor' in attr_name:
                            try:
                                record.product_height = float(attr.name)
                            except:
                                pass
        
        return result