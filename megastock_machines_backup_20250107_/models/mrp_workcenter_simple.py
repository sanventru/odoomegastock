# -*- coding: utf-8 -*-

from odoo import models, fields, api

class MrpWorkcenterSimple(models.Model):
    _inherit = 'mrp.workcenter'
    
    # Solo campos básicos sin métodos computados
    power_consumption_kw = fields.Float(
        string='Consumo Energético (kW)',
        help='Potencia eléctrica consumida por hora en kW',
        default=0.0
    )
    
    max_width_mm = fields.Integer(
        string='Ancho Máximo (mm)',
        help='Ancho máximo de material que puede procesar',
        default=0
    )
    
    theoretical_capacity = fields.Float(
        string='Capacidad Teórica/Hora',
        help='Capacidad teórica máxima por hora',
        default=0.0
    )
    
    machine_status = fields.Selection([
        ('operational', 'Operativa'),
        ('maintenance', 'En Mantenimiento'),
        ('breakdown', 'Averiada'),
        ('setup', 'En Setup'),
        ('standby', 'En Espera')
    ], string='Estado de Máquina', default='operational')
    
    # Métricas OEE básicas
    downtime_count_today = fields.Integer(
        string='Paradas Hoy',
        compute='_compute_oee_metrics',
        help='Número de paradas registradas hoy'
    )
    
    downtime_duration_today = fields.Float(
        string='Tiempo Parado Hoy (h)',
        compute='_compute_oee_metrics',
        help='Total de horas parado hoy'
    )
    
    oee_availability = fields.Float(
        string='Disponibilidad (%)',
        compute='_compute_oee_metrics',
        help='Porcentaje de tiempo operativo vs tiempo programado'
    )
    
    @api.depends('machine_status')
    def _compute_oee_metrics(self):
        """Calcular métricas OEE básicas"""
        from datetime import datetime, date
        
        for record in self:
            # Obtener paradas de hoy
            today_start = datetime.combine(date.today(), datetime.min.time())
            today_end = datetime.combine(date.today(), datetime.max.time())
            
            downtimes = self.env['megastock.machine.downtime'].search([
                ('workcenter_id', '=', record.id),
                ('start_time', '>=', today_start),
                ('start_time', '<=', today_end)
            ])
            
            record.downtime_count_today = len(downtimes)
            record.downtime_duration_today = sum(dt.duration_minutes for dt in downtimes) / 60.0
            
            # Calcular disponibilidad simple (8 horas programadas por día)
            programmed_hours = 8.0
            if programmed_hours > 0:
                operational_hours = programmed_hours - record.downtime_duration_today
                record.oee_availability = (operational_hours / programmed_hours) * 100.0
            else:
                record.oee_availability = 100.0

    # Método simple sin dependencias
    def action_start_maintenance(self):
        """Cambiar estado a mantenimiento"""
        self.machine_status = 'maintenance'
        return True