# -*- coding: utf-8 -*-

from odoo import models, fields, api

class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.request'
    
    # Campos adicionales para MEGASTOCK
    estimated_duration_hours = fields.Float(
        string='Duración Estimada (Horas)',
        help='Tiempo estimado para completar el mantenimiento'
    )
    
    actual_duration_hours = fields.Float(
        string='Duración Real (Horas)',
        help='Tiempo real utilizado para completar el mantenimiento'
    )
    
    # Materiales utilizados
    material_ids = fields.Many2many(
        'product.product',
        'maintenance_materials_rel',
        'maintenance_id',
        'product_id',
        string='Materiales Utilizados',
        help='Repuestos y materiales utilizados en el mantenimiento'
    )
    
    material_cost = fields.Float(
        string='Costo de Materiales',
        help='Costo total de materiales utilizados',
        compute='_compute_material_cost',
        store=True
    )
    
    labor_cost = fields.Float(
        string='Costo Mano de Obra',
        help='Costo de mano de obra técnica',
        compute='_compute_labor_cost',
        store=True
    )
    
    total_cost = fields.Float(
        string='Costo Total',
        help='Costo total del mantenimiento',
        compute='_compute_total_cost',
        store=True
    )
    
    # Clasificación de mantenimiento
    maintenance_category = fields.Selection([
        ('routine', 'Rutina'),
        ('inspection', 'Inspección'),
        ('repair', 'Reparación'),
        ('replacement', 'Reemplazo'),
        ('upgrade', 'Mejora'),
        ('calibration', 'Calibración')
    ], string='Categoría de Mantenimiento', default='routine')
    
    # Resultado del mantenimiento
    maintenance_result = fields.Selection([
        ('successful', 'Exitoso'),
        ('partial', 'Parcial'),
        ('failed', 'Fallido'),
        ('deferred', 'Diferido')
    ], string='Resultado', help='Resultado del mantenimiento realizado')
    
    # Observaciones técnicas
    technical_observations = fields.Text(
        string='Observaciones Técnicas',
        help='Observaciones técnicas del mantenimiento realizado'
    )
    
    recommendations = fields.Text(
        string='Recomendaciones',
        help='Recomendaciones para futuros mantenimientos'
    )
    
    # Impacto en producción
    production_impact = fields.Selection([
        ('none', 'Sin Impacto'),
        ('minimal', 'Mínimo'),
        ('moderate', 'Moderado'),
        ('significant', 'Significativo'),
        ('critical', 'Crítico')
    ], string='Impacto en Producción', default='none')
    
    downtime_created = fields.Boolean(
        string='Creó Parada',
        default=False,
        help='Indica si este mantenimiento generó una parada no programada'
    )
    
    # Técnicos asignados
    technician_ids = fields.Many2many(
        'hr.employee',
        'maintenance_technicians_rel',
        'maintenance_id',
        'employee_id',
        string='Técnicos Asignados',
        help='Técnicos asignados para realizar el mantenimiento'
    )
    
    # Seguimiento de calidad
    quality_check_required = fields.Boolean(
        string='Requiere Control de Calidad',
        default=False,
        help='Indica si requiere verificación de calidad post-mantenimiento'
    )
    
    quality_check_completed = fields.Boolean(
        string='Control de Calidad Completado',
        default=False,
        help='Indica si se completó la verificación de calidad'
    )
    
    quality_notes = fields.Text(
        string='Notas de Calidad',
        help='Observaciones del control de calidad'
    )
    
    # Programación de próximo mantenimiento
    schedule_next_maintenance = fields.Boolean(
        string='Programar Próximo Mantenimiento',
        default=False,
        help='Programar automáticamente el próximo mantenimiento'
    )
    
    next_maintenance_date = fields.Datetime(
        string='Próximo Mantenimiento',
        help='Fecha programada para el próximo mantenimiento'
    )
    
    @api.depends('material_ids', 'material_ids.standard_price')
    def _compute_material_cost(self):
        """Calcular costo de materiales"""
        for record in self:
            record.material_cost = sum(record.material_ids.mapped('standard_price'))
    
    @api.depends('actual_duration_hours')
    def _compute_labor_cost(self):
        """Calcular costo de mano de obra"""
        TECHNICIAN_HOURLY_RATE = 15.0  # USD por hora
        for record in self:
            record.labor_cost = record.actual_duration_hours * TECHNICIAN_HOURLY_RATE
    
    @api.depends('material_cost', 'labor_cost')
    def _compute_total_cost(self):
        """Calcular costo total"""
        for record in self:
            record.total_cost = record.material_cost + record.labor_cost
    
    def action_start_maintenance(self):
        """Iniciar mantenimiento"""
        # Cambiar estado del equipo/centro de trabajo
        if self.equipment_id and self.equipment_id.workcenter_id:
            self.equipment_id.workcenter_id.machine_status = 'maintenance'
        
        # Registrar hora de inicio si no está registrada
        if not self.request_date:
            self.request_date = fields.Datetime.now()
        
        return True
    
    def action_complete_maintenance(self):
        """Completar mantenimiento"""
        # Marcar como completado
        done_stage = self.env['maintenance.stage'].search([('done', '=', True)], limit=1)
        if done_stage:
            self.stage_id = done_stage.id
        
        # Registrar duración real si no está registrada
        if not self.actual_duration_hours and self.duration:
            self.actual_duration_hours = self.duration
        
        # Cambiar estado del equipo a operativo
        if self.equipment_id and self.equipment_id.workcenter_id:
            self.equipment_id.workcenter_id.machine_status = 'operational'
            self.equipment_id.workcenter_id.last_maintenance_date = fields.Datetime.now()
        
        # Programar próximo mantenimiento si está configurado
        if self.schedule_next_maintenance and self.next_maintenance_date:
            self._schedule_next_maintenance()
        
        return True
    
    def _schedule_next_maintenance(self):
        """Programar próximo mantenimiento automáticamente"""
        if self.maintenance_type == 'preventive':
            # Crear nuevo mantenimiento preventivo
            next_maintenance = self.copy({
                'name': f'Mantenimiento Programado - {self.equipment_id.name}',
                'schedule_date': self.next_maintenance_date,
                'request_date': False,
                'stage_id': self.env['maintenance.stage'].search([('sequence', '=', 1)], limit=1).id,
                'actual_duration_hours': 0,
                'material_ids': [(5, 0, 0)],  # Limpiar materiales
                'maintenance_result': False,
                'technical_observations': '',
                'recommendations': '',
            })
            
            # Notificar sobre el mantenimiento programado
            next_maintenance.message_post(
                body=f"Mantenimiento programado automáticamente basado en {self.name}",
                message_type='notification'
            )
    
    def action_request_quality_check(self):
        """Solicitar control de calidad"""
        self.quality_check_required = True
        
        # Crear actividad para control de calidad
        self.activity_schedule(
            'mail.mail_activity_data_todo',
            summary='Control de Calidad Post-Mantenimiento',
            note=f'Verificar funcionamiento del equipo {self.equipment_id.name} después del mantenimiento.',
            user_id=self.env.user.id,
        )
        
        return True
    
    def action_complete_quality_check(self):
        """Completar control de calidad"""
        self.quality_check_completed = True
        
        # Marcar actividades relacionadas como completadas
        activities = self.activity_ids.filtered(
            lambda a: 'Control de Calidad' in a.summary
        )
        activities.action_done()
        
        return True
    
    @api.model
    def get_maintenance_statistics(self, date_from, date_to, equipment_ids=None):
        """Obtener estadísticas de mantenimiento para dashboard"""
        domain = [
            ('request_date', '>=', date_from),
            ('request_date', '<=', date_to),
            ('stage_id.done', '=', True)
        ]
        
        if equipment_ids:
            domain.append(('equipment_id', 'in', equipment_ids))
        
        maintenance_records = self.search(domain)
        
        # Estadísticas generales
        preventive_count = len(maintenance_records.filtered(lambda m: m.maintenance_type == 'preventive'))
        corrective_count = len(maintenance_records.filtered(lambda m: m.maintenance_type == 'corrective'))
        
        total_cost = sum(maintenance_records.mapped('total_cost'))
        avg_duration = sum(maintenance_records.mapped('actual_duration_hours')) / len(maintenance_records) if maintenance_records else 0
        
        # Eficiencia (mantenimientos completados a tiempo)
        on_time_count = len(maintenance_records.filtered(
            lambda m: m.schedule_date and m.request_date and m.request_date <= m.schedule_date
        ))
        efficiency_percentage = (on_time_count / len(maintenance_records) * 100) if maintenance_records else 0
        
        return {
            'total_maintenances': len(maintenance_records),
            'preventive_count': preventive_count,
            'corrective_count': corrective_count,
            'preventive_percentage': (preventive_count / len(maintenance_records) * 100) if maintenance_records else 0,
            'total_cost': total_cost,
            'average_duration': avg_duration,
            'efficiency_percentage': efficiency_percentage,
            'cost_per_maintenance': total_cost / len(maintenance_records) if maintenance_records else 0,
        }