# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    # Campos específicos para repuestos de máquinas
    is_machine_spare_part = fields.Boolean(
        string='Es Repuesto de Máquina',
        default=False,
        help='Indica si este producto es un repuesto para maquinaria'
    )
    
    compatible_equipment_ids = fields.Many2many(
        'maintenance.equipment',
        'product_equipment_compatibility_rel',
        'product_id',
        'equipment_id',
        string='Equipos Compatibles',
        help='Equipos con los que este repuesto es compatible'
    )
    
    compatible_workcenter_ids = fields.Many2many(
        'mrp.workcenter',
        'product_workcenter_compatibility_rel',
        'product_id',
        'workcenter_id',
        string='Centros de Trabajo Compatibles',
        help='Centros de trabajo donde se puede usar este repuesto'
    )
    
    # Clasificación de criticidad del repuesto
    spare_part_criticality = fields.Selection([
        ('low', 'Baja'),
        ('medium', 'Media'),
        ('high', 'Alta'),
        ('critical', 'Crítica')
    ], string='Criticidad del Repuesto', 
       help='Nivel de criticidad del repuesto para la operación')
    
    # Información técnica del repuesto
    manufacturer_part_number = fields.Char(
        string='Número de Parte Fabricante',
        help='Número de parte original del fabricante'
    )
    
    technical_drawing_url = fields.Char(
        string='URL Plano Técnico',
        help='Enlace al plano técnico o diagrama del repuesto'
    )
    
    installation_instructions = fields.Text(
        string='Instrucciones de Instalación',
        help='Instrucciones específicas para la instalación del repuesto'
    )
    
    # Historial de uso
    average_replacement_interval = fields.Integer(
        string='Intervalo Promedio Reemplazo (días)',
        help='Días promedio entre reemplazos de este repuesto'
    )
    
    last_replacement_date = fields.Date(
        string='Última Fecha de Reemplazo',
        help='Fecha del último reemplazo registrado'
    )
    
    # Información de mantenimiento
    requires_special_tools = fields.Boolean(
        string='Requiere Herramientas Especiales',
        default=False,
        help='Indica si la instalación requiere herramientas especiales'
    )
    
    special_tools_required = fields.Text(
        string='Herramientas Especiales Requeridas',
        help='Descripción de las herramientas especiales necesarias'
    )
    
    installation_time_hours = fields.Float(
        string='Tiempo de Instalación (Horas)',
        help='Tiempo estimado para instalar este repuesto'
    )
    
    # Información de stock para repuestos críticos
    min_stock_alert_days = fields.Integer(
        string='Alerta Stock Mínimo (días)',
        default=30,
        help='Días de anticipación para alerta de stock mínimo'
    )
    
    max_storage_temperature = fields.Float(
        string='Temperatura Máxima Almacenamiento (°C)',
        help='Temperatura máxima de almacenamiento recomendada'
    )
    
    storage_conditions = fields.Text(
        string='Condiciones de Almacenamiento',
        help='Condiciones específicas de almacenamiento del repuesto'
    )
    
    @api.onchange('is_machine_spare_part')
    def _onchange_is_machine_spare_part(self):
        """Cambios automáticos cuando se marca como repuesto"""
        if self.is_machine_spare_part:
            # Configurar automáticamente como producto almacenable
            self.type = 'product'
            # Activar tracking por lotes si es crítico
            if self.spare_part_criticality in ['high', 'critical']:
                self.tracking = 'lot' 
        else:
            # Limpiar campos específicos de repuestos
            self.compatible_equipment_ids = [(5, 0, 0)]
            self.compatible_workcenter_ids = [(5, 0, 0)]
            self.spare_part_criticality = False
    
    def action_view_usage_history(self):
        """Ver historial de uso del repuesto"""
        if not self.is_machine_spare_part:
            return
            
        # Buscar órdenes de mantenimiento que usaron este repuesto
        maintenance_requests = self.env['maintenance.request'].search([
            ('material_ids', 'in', self.product_variant_ids.ids)
        ])
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Historial de Uso - {self.name}',
            'res_model': 'maintenance.request',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', maintenance_requests.ids)],
            'context': {'search_default_group_by_equipment': 1}
        }
    
    def action_check_compatibility(self):
        """Verificar compatibilidad con equipos"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'Compatibilidad - {self.name}',
            'res_model': 'maintenance.equipment',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.compatible_equipment_ids.ids)],
        }
    
    def get_spare_part_metrics(self):
        """Obtener métricas del repuesto para dashboard"""
        if not self.is_machine_spare_part:
            return {}
            
        # Calcular métricas de uso
        maintenance_requests = self.env['maintenance.request'].search([
            ('material_ids', 'in', self.product_variant_ids.ids),
            ('stage_id.done', '=', True)
        ])
        
        # Stock actual
        current_stock = sum(self.product_variant_ids.mapped('qty_available'))
        
        # Costo total de mantenimientos que usaron este repuesto
        total_maintenance_cost = sum(maintenance_requests.mapped('total_cost'))
        
        return {
            'name': self.name,
            'current_stock': current_stock,
            'criticality': self.spare_part_criticality,
            'usage_count': len(maintenance_requests),
            'total_maintenance_cost': total_maintenance_cost,
            'compatible_equipment_count': len(self.compatible_equipment_ids),
            'average_cost_per_use': (
                total_maintenance_cost / len(maintenance_requests) 
                if maintenance_requests else 0
            ),
            'days_since_last_use': (
                (fields.Date.today() - self.last_replacement_date).days 
                if self.last_replacement_date else 999
            )
        }