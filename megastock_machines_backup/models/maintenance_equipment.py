# -*- coding: utf-8 -*-

from odoo import models, fields, api

class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'
    
    # Relación con centro de trabajo
    workcenter_id = fields.Many2one(
        'mrp.workcenter',
        string='Centro de Trabajo',
        help='Centro de trabajo asociado a este equipo'
    )
    
    # Información técnica del equipo
    installation_date = fields.Date(
        string='Fecha de Instalación',
        help='Fecha en que se instaló el equipo'
    )
    
    technical_specifications = fields.Text(
        string='Especificaciones Técnicas',
        help='Detalles técnicos completos del equipo'
    )
    
    operating_manual_url = fields.Char(
        string='URL Manual de Operación',
        help='Enlace al manual de operación digital'
    )
    
    maintenance_manual_url = fields.Char(
        string='URL Manual de Mantenimiento',
        help='Enlace al manual de mantenimiento digital'
    )
    
    # Métricas de mantenimiento
    mtbf_hours = fields.Float(
        string='MTBF (Horas)',
        help='Mean Time Between Failures - Tiempo promedio entre fallas',
        compute='_compute_mtbf',
        store=True
    )
    
    mttr_hours = fields.Float(
        string='MTTR (Horas)',
        help='Mean Time To Repair - Tiempo promedio de reparación',
        compute='_compute_mttr',
        store=True
    )
    
    availability_percentage = fields.Float(
        string='Disponibilidad (%)',
        help='Porcentaje de disponibilidad del equipo',
        compute='_compute_availability',
        store=True
    )
    
    # Costos de mantenimiento
    maintenance_cost_ytd = fields.Float(
        string='Costo Mantenimiento Año Actual',
        help='Costo total de mantenimiento en el año actual',
        compute='_compute_maintenance_costs',
        store=True
    )
    
    maintenance_budget_year = fields.Float(
        string='Presupuesto Anual Mantenimiento',
        help='Presupuesto asignado para mantenimiento del equipo'
    )
    
    # Repuestos críticos
    critical_spare_part_ids = fields.Many2many(
        'product.product',
        'equipment_spare_parts_rel',
        'equipment_id',
        'product_id',
        string='Repuestos Críticos',
        domain=[('categ_id.name', 'ilike', 'Repuestos')],
        help='Repuestos críticos para este equipo'
    )
    
    @api.depends('maintenance_ids', 'maintenance_ids.stage_id')
    def _compute_mtbf(self):
        """Calcular Mean Time Between Failures"""
        for equipment in self:
            # Obtener mantenimientos correctivos completados
            corrective_maintenances = equipment.maintenance_ids.filtered(
                lambda m: m.maintenance_type == 'corrective' and m.stage_id.done
            )
            
            if len(corrective_maintenances) > 1:
                # Calcular tiempo entre fallas
                total_operating_hours = 0
                failure_count = len(corrective_maintenances) - 1
                
                # Asumir 8 horas de operación diaria para estimación
                DAILY_HOURS = 8
                dates = corrective_maintenances.mapped('request_date')
                if dates:
                    dates.sort()
                    total_days = (dates[-1] - dates[0]).days
                    total_operating_hours = total_days * DAILY_HOURS
                
                equipment.mtbf_hours = total_operating_hours / failure_count if failure_count > 0 else 0
            else:
                equipment.mtbf_hours = 0
    
    @api.depends('maintenance_ids', 'maintenance_ids.duration')
    def _compute_mttr(self):
        """Calcular Mean Time To Repair"""
        for equipment in self:
            corrective_maintenances = equipment.maintenance_ids.filtered(
                lambda m: m.maintenance_type == 'corrective' and m.stage_id.done and m.duration > 0
            )
            
            if corrective_maintenances:
                total_repair_time = sum(corrective_maintenances.mapped('duration'))
                equipment.mttr_hours = total_repair_time / len(corrective_maintenances)
            else:
                equipment.mttr_hours = 0
    
    @api.depends('mtbf_hours', 'mttr_hours')
    def _compute_availability(self):
        """Calcular disponibilidad del equipo"""
        for equipment in self:
            if equipment.mtbf_hours and equipment.mttr_hours:
                equipment.availability_percentage = (
                    equipment.mtbf_hours / 
                    (equipment.mtbf_hours + equipment.mttr_hours)
                ) * 100
            else:
                # Valor por defecto si no hay datos suficientes
                equipment.availability_percentage = 95.0
    
    @api.depends('maintenance_ids', 'maintenance_ids.stage_id')
    def _compute_maintenance_costs(self):
        """Calcular costos de mantenimiento del año actual"""
        current_year = fields.Date.today().year
        
        for equipment in self:
            year_maintenances = equipment.maintenance_ids.filtered(
                lambda m: m.request_date and m.request_date.year == current_year and m.stage_id.done
            )
            
            # Estimar costo basado en duración y tarifa técnico
            TECHNICIAN_HOURLY_RATE = 15.0  # USD por hora
            total_cost = 0
            
            for maintenance in year_maintenances:
                labor_cost = maintenance.duration * TECHNICIAN_HOURLY_RATE
                # Agregar costo estimado de repuestos (20% del costo laboral para preventivo, 50% para correctivo)
                spare_parts_multiplier = 0.5 if maintenance.maintenance_type == 'corrective' else 0.2
                spare_parts_cost = labor_cost * spare_parts_multiplier
                total_cost += labor_cost + spare_parts_cost
            
            equipment.maintenance_cost_ytd = total_cost
    
    def action_schedule_preventive_maintenance(self):
        """Programar mantenimiento preventivo"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Programar Mantenimiento Preventivo',
            'res_model': 'maintenance.request',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_equipment_id': self.id,
                'default_maintenance_type': 'preventive',
                'default_name': f'Mantenimiento Preventivo - {self.name}',
            }
        }
    
    def action_report_breakdown(self):
        """Reportar avería del equipo"""
        # Cambiar estado del centro de trabajo si existe
        if self.workcenter_id:
            self.workcenter_id.machine_status = 'breakdown'
        
        # Crear registro de parada no programada
        downtime_record = self.env['megastock.machine.downtime'].create({
            'workcenter_id': self.workcenter_id.id if self.workcenter_id else False,
            'problem_description': f'Avería reportada en equipo {self.name}',
            'downtime_type': 'mechanical',  # Por defecto
            'severity': 'high',
            'state': 'reported',
        })
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Registro de Parada No Programada',
            'res_model': 'megastock.machine.downtime',
            'res_id': downtime_record.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def get_equipment_kpis(self):
        """Obtener KPIs del equipo para dashboard"""
        return {
            'name': self.name,
            'mtbf': self.mtbf_hours,
            'mttr': self.mttr_hours,
            'availability': self.availability_percentage,
            'maintenance_cost_ytd': self.maintenance_cost_ytd,
            'maintenance_budget': self.maintenance_budget_year,
            'budget_used_percentage': (
                (self.maintenance_cost_ytd / self.maintenance_budget_year * 100) 
                if self.maintenance_budget_year else 0
            ),
            'critical_spare_parts_count': len(self.critical_spare_part_ids),
            'pending_maintenances': len(self.maintenance_ids.filtered(lambda m: not m.stage_id.done)),
        }