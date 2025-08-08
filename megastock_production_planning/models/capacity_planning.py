# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class CapacityPlanning(models.Model):
    _name = 'megastock.capacity.planning'
    _description = 'Planificación de Capacidad MEGASTOCK'
    _order = 'planning_date desc'
    
    name = fields.Char(
        string='Nombre',
        required=True,
        default=lambda self: self._get_default_name()
    )
    
    planning_date = fields.Date(
        string='Fecha de Planificación', 
        required=True,
        default=fields.Date.today
    )
    
    date_from = fields.Date(
        string='Desde',
        required=True,
        default=fields.Date.today
    )
    
    date_to = fields.Date(
        string='Hasta',
        required=True,
        default=lambda self: fields.Date.today() + timedelta(days=30)
    )
    
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('calculated', 'Calculado'),
        ('approved', 'Aprobado'),
        ('active', 'Activo')
    ], string='Estado', default='draft', required=True)
    
    # === CONFIGURACIÓN DE CAPACIDAD ===
    capacity_type = fields.Selection([
        ('finite', 'Capacidad Finita'),
        ('infinite', 'Capacidad Infinita'),
        ('flexible', 'Capacidad Flexible')
    ], string='Tipo de Capacidad', default='finite', required=True)
    
    include_overtime = fields.Boolean(
        string='Incluir Horas Extra',
        default=False,
        help='Considerar horas extra en el cálculo de capacidad'
    )
    
    max_overtime_percentage = fields.Float(
        string='Máximo Horas Extra (%)',
        default=20.0,
        help='Porcentaje máximo de horas extra sobre tiempo normal'
    )
    
    efficiency_factor = fields.Float(
        string='Factor de Eficiencia',
        default=85.0,
        help='Eficiencia promedio esperada (%)'
    )
    
    # === LÍNEAS DE CAPACIDAD ===
    capacity_line_ids = fields.One2many(
        'megastock.capacity.planning.line',
        'capacity_planning_id',
        string='Líneas de Capacidad'
    )
    
    # === ANÁLISIS DE RESULTADOS ===
    total_workcenters = fields.Integer(
        string='Total Centros de Trabajo',
        compute='_compute_totals',
        store=True
    )
    
    total_available_hours = fields.Float(
        string='Horas Disponibles Totales',
        compute='_compute_totals',
        store=True
    )
    
    total_required_hours = fields.Float(
        string='Horas Requeridas Totales',
        help='Horas requeridas según demanda planificada'
    )
    
    overall_utilization = fields.Float(
        string='Utilización Global (%)',
        compute='_compute_utilization',
        store=True
    )
    
    bottleneck_workcenter_id = fields.Many2one(
        'mrp.workcenter',
        string='Cuello de Botella Principal',
        compute='_compute_bottleneck',
        store=True
    )
    
    bottleneck_utilization = fields.Float(
        string='Utilización Cuello Botella (%)',
        compute='_compute_bottleneck',
        store=True
    )
    
    # === ALERTAS Y RECOMENDACIONES ===
    capacity_alerts = fields.Text(
        string='Alertas de Capacidad',
        compute='_compute_alerts',
        help='Alertas automáticas sobre problemas de capacidad'
    )
    
    optimization_suggestions = fields.Text(
        string='Sugerencias de Optimización',
        compute='_compute_suggestions',
        help='Sugerencias para optimizar capacidad'
    )
    
    # === CONFIGURACIÓN DE TURNOS ===
    shift_pattern = fields.Selection([
        ('single', '1 Turno (8 horas)'),
        ('double', '2 Turnos (16 horas)'),
        ('triple', '3 Turnos (24 horas)'),
        ('custom', 'Personalizado')
    ], string='Patrón de Turnos', default='double')
    
    hours_per_shift = fields.Float(
        string='Horas por Turno',
        default=8.0
    )
    
    shifts_per_day = fields.Integer(
        string='Turnos por Día',
        default=2
    )
    
    working_days = fields.Selection([
        ('5', '5 días (L-V)'),
        ('6', '6 días (L-S)'),
        ('7', '7 días (L-D)')
    ], string='Días Laborales', default='6')
    
    # === MÉTODOS COMPUTADOS ===
    
    def _get_default_name(self):
        """Generar nombre por defecto"""
        return f"Capacidad {datetime.now().strftime('%Y%m%d')}"
    
    @api.depends('capacity_line_ids')
    def _compute_totals(self):
        """Calcular totales de capacidad"""
        for planning in self:
            planning.total_workcenters = len(planning.capacity_line_ids)
            planning.total_available_hours = sum(
                planning.capacity_line_ids.mapped('available_hours')
            )
    
    @api.depends('total_available_hours', 'total_required_hours')
    def _compute_utilization(self):
        """Calcular utilización global"""
        for planning in self:
            if planning.total_available_hours > 0:
                planning.overall_utilization = (
                    planning.total_required_hours / planning.total_available_hours
                ) * 100
            else:
                planning.overall_utilization = 0.0
    
    @api.depends('capacity_line_ids.utilization_percentage')
    def _compute_bottleneck(self):
        """Identificar cuello de botella"""
        for planning in self:
            if planning.capacity_line_ids:
                bottleneck_line = max(
                    planning.capacity_line_ids,
                    key=lambda l: l.utilization_percentage,
                    default=None
                )
                
                if bottleneck_line:
                    planning.bottleneck_workcenter_id = bottleneck_line.workcenter_id
                    planning.bottleneck_utilization = bottleneck_line.utilization_percentage
                else:
                    planning.bottleneck_workcenter_id = False
                    planning.bottleneck_utilization = 0.0
            else:
                planning.bottleneck_workcenter_id = False
                planning.bottleneck_utilization = 0.0
    
    def _compute_alerts(self):
        """Generar alertas de capacidad"""
        for planning in self:
            alerts = []
            
            # Alerta por utilización alta
            if planning.overall_utilization > 95:
                alerts.append("⚠️ CRÍTICO: Utilización global excede 95%")
            elif planning.overall_utilization > 85:
                alerts.append("⚠️ ADVERTENCIA: Utilización global alta (>85%)")
            
            # Alerta por cuello de botella
            if planning.bottleneck_utilization > 100:
                alerts.append(f"🚫 SOBRECARGA: {planning.bottleneck_workcenter_id.name} - {planning.bottleneck_utilization:.1f}%")
            elif planning.bottleneck_utilization > 90:
                alerts.append(f"⚠️ SATURACIÓN: {planning.bottleneck_workcenter_id.name} - {planning.bottleneck_utilization:.1f}%")
            
            # Alertas por líneas específicas
            for line in planning.capacity_line_ids:
                if line.utilization_percentage > 100:
                    alerts.append(f"🔴 {line.workcenter_id.name}: Capacidad insuficiente ({line.utilization_percentage:.1f}%)")
                elif line.capacity_shortage > 0:
                    alerts.append(f"🟡 {line.workcenter_id.name}: Faltante de {line.capacity_shortage:.1f} horas")
            
            planning.capacity_alerts = '\n'.join(alerts) if alerts else 'Sin alertas de capacidad'
    
    def _compute_suggestions(self):
        """Generar sugerencias de optimización"""
        for planning in self:
            suggestions = []
            
            # Sugerencias generales
            if planning.overall_utilization > 85:
                suggestions.append("• Considerar horas extra o turnos adicionales")
                suggestions.append("• Evaluar tercerización de procesos no críticos")
                suggestions.append("• Revisar eficiencia de procesos")
            
            if planning.bottleneck_utilization > 90:
                suggestions.append(f"• Reforzar capacidad en {planning.bottleneck_workcenter_id.name}")
                suggestions.append("• Redistribuir carga desde cuello de botella")
            
            # Sugerencias por líneas subutilizadas
            underutilized = planning.capacity_line_ids.filtered(
                lambda l: l.utilization_percentage < 60
            )
            
            if underutilized:
                suggestions.append("• Líneas subutilizadas disponibles para redistribución:")
                for line in underutilized:
                    suggestions.append(f"  - {line.workcenter_id.name}: {line.utilization_percentage:.1f}%")
            
            # Sugerencias de balanceamiento
            utilization_variance = self._calculate_utilization_variance(planning)
            if utilization_variance > 25:
                suggestions.append("• Alto desbalance entre líneas - revisar distribución de trabajo")
            
            planning.optimization_suggestions = '\n'.join(suggestions) if suggestions else 'Sin sugerencias adicionales'
    
    def _calculate_utilization_variance(self, planning):
        """Calcular varianza en utilización entre líneas"""
        if not planning.capacity_line_ids:
            return 0.0
        
        utilizations = planning.capacity_line_ids.mapped('utilization_percentage')
        if not utilizations:
            return 0.0
        
        mean_util = sum(utilizations) / len(utilizations)
        variance = sum((u - mean_util) ** 2 for u in utilizations) / len(utilizations)
        
        return variance ** 0.5  # Desviación estándar
    
    # === MÉTODOS DE ACCIÓN ===
    
    def action_calculate_capacity(self):
        """Calcular capacidad disponible y requerida"""
        self.ensure_one()
        
        # Limpiar líneas existentes
        self.capacity_line_ids.unlink()
        
        # Obtener centros de trabajo activos
        workcenters = self.env['mrp.workcenter'].search([
            ('active', '=', True)
        ])
        
        for workcenter in workcenters:
            self._create_capacity_line(workcenter)
        
        # Calcular demanda requerida
        self._calculate_required_capacity()
        
        self.state = 'calculated'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Capacidad Calculada',
                'message': f'Se calculó capacidad para {len(workcenters)} centros de trabajo.',
                'type': 'success'
            }
        }
    
    def _create_capacity_line(self, workcenter):
        """Crear línea de capacidad para un centro de trabajo"""
        # Calcular capacidad disponible
        available_hours = self._calculate_available_capacity(workcenter)
        
        # Calcular capacidad con horas extra
        overtime_hours = 0.0
        if self.include_overtime:
            overtime_hours = available_hours * (self.max_overtime_percentage / 100.0)
        
        return self.env['megastock.capacity.planning.line'].create({
            'capacity_planning_id': self.id,
            'workcenter_id': workcenter.id,
            'available_hours': available_hours,
            'overtime_hours': overtime_hours,
            'total_capacity': available_hours + overtime_hours,
            'efficiency_factor': self.efficiency_factor,
            'effective_capacity': (available_hours + overtime_hours) * (self.efficiency_factor / 100.0)
        })
    
    def _calculate_available_capacity(self, workcenter):
        """Calcular capacidad disponible para un centro de trabajo"""
        # Calcular días laborales en el período
        working_days_count = self._get_working_days_count()
        
        # Capacidad diaria teórica
        daily_hours = self.hours_per_shift * self.shifts_per_day
        
        # Aplicar eficiencia del centro de trabajo
        workcenter_efficiency = workcenter.time_efficiency / 100.0 if workcenter.time_efficiency else 1.0
        
        # Capacidad total disponible
        total_hours = working_days_count * daily_hours * workcenter_efficiency
        
        return total_hours
    
    def _get_working_days_count(self):
        """Obtener número de días laborales en el período"""
        days_diff = (self.date_to - self.date_from).days + 1
        
        if self.working_days == '7':
            return days_diff
        elif self.working_days == '6':
            # Aproximación: 6/7 de los días
            return int(days_diff * 6 / 7)
        else:  # '5'
            # Aproximación: 5/7 de los días
            return int(days_diff * 5 / 7)
    
    def _calculate_required_capacity(self):
        """Calcular capacidad requerida basada en planes de producción"""
        required_hours_by_workcenter = {}
        
        # Buscar planes de producción activos en el período
        production_plans = self.env['megastock.production.plan'].search([
            ('state', 'in', ['confirmed', 'in_progress']),
            ('date_from', '<=', self.date_to),
            ('date_to', '>=', self.date_from)
        ])
        
        for plan in production_plans:
            for line in plan.plan_line_ids:
                # Distribuir horas entre centros de trabajo (simplificado)
                # En implementación real, esto vendría del routing
                bom = self.env['mrp.bom']._bom_find(product=line.product_id)
                
                if bom and bom.routing_id:
                    for operation in bom.routing_id.operation_ids:
                        workcenter_id = operation.workcenter_id.id
                        
                        if workcenter_id not in required_hours_by_workcenter:
                            required_hours_by_workcenter[workcenter_id] = 0.0
                        
                        # Calcular horas requeridas para esta operación
                        op_time = (operation.time_cycle * line.planned_quantity) / 60.0
                        required_hours_by_workcenter[workcenter_id] += op_time
        
        # Actualizar líneas de capacidad con demanda requerida
        for line in self.capacity_line_ids:
            required_hours = required_hours_by_workcenter.get(line.workcenter_id.id, 0.0)
            line.required_hours = required_hours
        
        # Actualizar total requerido
        self.total_required_hours = sum(required_hours_by_workcenter.values())
    
    def action_optimize_capacity(self):
        """Optimizar distribución de capacidad"""
        self.ensure_one()
        
        optimization_actions = []
        
        # Identificar líneas sobrecargadas y subutilizadas
        overloaded = self.capacity_line_ids.filtered(lambda l: l.utilization_percentage > 100)
        underutilized = self.capacity_line_ids.filtered(lambda l: l.utilization_percentage < 60)
        
        for overloaded_line in overloaded:
            excess_hours = overloaded_line.capacity_shortage
            
            # Buscar líneas que puedan absorber la carga
            for underutil_line in underutilized:
                available_capacity = underutil_line.total_capacity - underutil_line.required_hours
                
                if available_capacity > 0:
                    transfer_hours = min(excess_hours, available_capacity)
                    
                    # Simular transferencia
                    overloaded_line.required_hours -= transfer_hours
                    underutil_line.required_hours += transfer_hours
                    
                    optimization_actions.append({
                        'action': 'transfer_load',
                        'from': overloaded_line.workcenter_id.name,
                        'to': underutil_line.workcenter_id.name,
                        'hours': transfer_hours
                    })
                    
                    excess_hours -= transfer_hours
                    if excess_hours <= 0:
                        break
        
        # Sugerir horas extra para carga restante
        remaining_overloaded = self.capacity_line_ids.filtered(lambda l: l.utilization_percentage > 100)
        
        for line in remaining_overloaded:
            overtime_needed = line.capacity_shortage
            optimization_actions.append({
                'action': 'add_overtime',
                'workcenter': line.workcenter_id.name,
                'hours': overtime_needed
            })
        
        # Generar resumen de optimización
        if optimization_actions:
            summary = "Acciones de optimización aplicadas:\n"
            for action in optimization_actions:
                if action['action'] == 'transfer_load':
                    summary += f"• Transferir {action['hours']:.1f}h de {action['from']} a {action['to']}\n"
                elif action['action'] == 'add_overtime':
                    summary += f"• Agregar {action['hours']:.1f}h extra en {action['workcenter']}\n"
        else:
            summary = "No se requieren optimizaciones adicionales."
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Optimización Completada',
                'message': summary,
                'type': 'success',
                'sticky': True
            }
        }
    
    def action_generate_schedule(self):
        """Generar cronograma detallado de capacidad"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Cronograma de Capacidad',
            'res_model': 'megastock.production.schedule',
            'view_mode': 'gantt,tree,form',
            'domain': [('capacity_planning_id', '=', self.id)],
            'context': {
                'default_capacity_planning_id': self.id,
                'group_by': 'workcenter_id'
            }
        }
    
    def action_capacity_analysis(self):
        """Lanzar análisis detallado de capacidad"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Análisis de Capacidad',
            'res_model': 'megastock.capacity.analysis.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_capacity_planning_id': self.id}
        }


class CapacityPlanningLine(models.Model):
    _name = 'megastock.capacity.planning.line'
    _description = 'Línea de Planificación de Capacidad'
    _order = 'utilization_percentage desc'
    
    capacity_planning_id = fields.Many2one(
        'megastock.capacity.planning',
        string='Planificación de Capacidad',
        required=True,
        ondelete='cascade'
    )
    
    workcenter_id = fields.Many2one(
        'mrp.workcenter',
        string='Centro de Trabajo',
        required=True
    )
    
    # === CAPACIDAD DISPONIBLE ===
    available_hours = fields.Float(
        string='Horas Disponibles',
        help='Horas disponibles en tiempo normal'
    )
    
    overtime_hours = fields.Float(
        string='Horas Extra Disponibles',
        help='Horas adicionales disponibles en tiempo extra'
    )
    
    total_capacity = fields.Float(
        string='Capacidad Total',
        compute='_compute_total_capacity',
        store=True,
        help='Capacidad total incluyendo horas extra'
    )
    
    efficiency_factor = fields.Float(
        string='Factor de Eficiencia (%)',
        default=85.0,
        help='Factor de eficiencia aplicado'
    )
    
    effective_capacity = fields.Float(
        string='Capacidad Efectiva',
        compute='_compute_effective_capacity',
        store=True,
        help='Capacidad real considerando eficiencia'
    )
    
    # === DEMANDA REQUERIDA ===
    required_hours = fields.Float(
        string='Horas Requeridas',
        help='Horas requeridas según planificación'
    )
    
    # === ANÁLISIS ===
    utilization_percentage = fields.Float(
        string='Utilización (%)',
        compute='_compute_utilization',
        store=True
    )
    
    capacity_shortage = fields.Float(
        string='Faltante de Capacidad',
        compute='_compute_shortage',
        store=True,
        help='Horas faltantes (si es positivo)'
    )
    
    capacity_surplus = fields.Float(
        string='Exceso de Capacidad',
        compute='_compute_shortage',
        store=True,
        help='Horas sobrantes (si es positivo)'
    )
    
    status = fields.Selection([
        ('underutilized', 'Subutilizada'),
        ('optimal', 'Óptima'),
        ('high', 'Alta Utilización'),
        ('overloaded', 'Sobrecargada')
    ], string='Estado', compute='_compute_status', store=True)
    
    # === CONFIGURACIÓN ESPECÍFICA ===
    setup_time_hours = fields.Float(
        string='Tiempo Setup (h)',
        help='Tiempo promedio de setup por cambio'
    )
    
    maintenance_hours = fields.Float(
        string='Horas Mantenimiento',
        help='Horas reservadas para mantenimiento'
    )
    
    notes = fields.Text(
        string='Notas',
        help='Observaciones sobre esta línea de capacidad'
    )
    
    # === MÉTODOS COMPUTADOS ===
    
    @api.depends('available_hours', 'overtime_hours')
    def _compute_total_capacity(self):
        """Calcular capacidad total"""
        for line in self:
            line.total_capacity = line.available_hours + line.overtime_hours
    
    @api.depends('total_capacity', 'efficiency_factor')
    def _compute_effective_capacity(self):
        """Calcular capacidad efectiva"""
        for line in self:
            line.effective_capacity = line.total_capacity * (line.efficiency_factor / 100.0)
    
    @api.depends('required_hours', 'effective_capacity')
    def _compute_utilization(self):
        """Calcular porcentaje de utilización"""
        for line in self:
            if line.effective_capacity > 0:
                line.utilization_percentage = (line.required_hours / line.effective_capacity) * 100
            else:
                line.utilization_percentage = 0.0
    
    @api.depends('required_hours', 'effective_capacity')
    def _compute_shortage(self):
        """Calcular faltante o exceso de capacidad"""
        for line in self:
            difference = line.required_hours - line.effective_capacity
            
            if difference > 0:
                line.capacity_shortage = difference
                line.capacity_surplus = 0.0
            else:
                line.capacity_shortage = 0.0
                line.capacity_surplus = abs(difference)
    
    @api.depends('utilization_percentage')
    def _compute_status(self):
        """Determinar estado de la línea"""
        for line in self:
            if line.utilization_percentage > 100:
                line.status = 'overloaded'
            elif line.utilization_percentage > 85:
                line.status = 'high'
            elif line.utilization_percentage >= 60:
                line.status = 'optimal'
            else:
                line.status = 'underutilized'
    
    # === MÉTODOS DE UTILIDAD ===
    
    def get_capacity_details(self):
        """Obtener detalles de capacidad para análisis"""
        self.ensure_one()
        
        return {
            'workcenter_name': self.workcenter_id.name,
            'available_hours': self.available_hours,
            'overtime_hours': self.overtime_hours,
            'total_capacity': self.total_capacity,
            'effective_capacity': self.effective_capacity,
            'required_hours': self.required_hours,
            'utilization_percentage': self.utilization_percentage,
            'capacity_shortage': self.capacity_shortage,
            'capacity_surplus': self.capacity_surplus,
            'status': self.status,
            'efficiency_factor': self.efficiency_factor,
        }
    
    def action_view_workorders(self):
        """Ver órdenes de trabajo para este centro"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'Órdenes de Trabajo - {self.workcenter_id.name}',
            'res_model': 'mrp.workorder',
            'view_mode': 'tree,form',
            'domain': [
                ('workcenter_id', '=', self.workcenter_id.id),
                ('date_planned_start', '>=', self.capacity_planning_id.date_from),
                ('date_planned_start', '<=', self.capacity_planning_id.date_to)
            ]
        }