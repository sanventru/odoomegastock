# -*- coding: utf-8 -*-

from odoo import models, fields, api

class MachineOperator(models.Model):
    _name = 'megastock.machine.operator'
    _description = 'Operador de Máquina MEGASTOCK'
    _order = 'name'
    _rec_name = 'display_name'
    
    # Información básica
    name = fields.Char(
        string='Nombre Completo',
        required=True,
        help='Nombre completo del operador'
    )
    
    display_name = fields.Char(
        string='Nombre para Mostrar',
        compute='_compute_display_name',
        store=True
    )
    
    operator_code = fields.Char(
        string='Código Operador',
        required=True,
        copy=False,
        default='OP/',
        help='Código único del operador'
    )
    
    employee_id = fields.Many2one(
        'hr.employee',
        string='Empleado Relacionado',
        help='Referencia al empleado en recursos humanos'
    )
    
    active = fields.Boolean(
        string='Activo',
        default=True,
        help='Indica si el operador está actualmente activo'
    )
    
    # Certificaciones
    certified_workcenters = fields.Many2many(
        'mrp.workcenter',
        'operator_workcenter_certification_rel',
        'operator_id',
        'workcenter_id',
        string='Centros de Trabajo Certificados',
        help='Máquinas que el operador está certificado para operar'
    )
    
    primary_workcenter_id = fields.Many2one(
        'mrp.workcenter',
        string='Centro de Trabajo Principal',
        help='Centro de trabajo donde el operador trabaja principalmente'
    )
    
    certification_level = fields.Selection([
        ('trainee', 'Aprendiz'),
        ('junior', 'Junior'),
        ('senior', 'Senior'),
        ('expert', 'Experto'),
        ('instructor', 'Instructor')
    ], string='Nivel de Certificación', default='junior', required=True)
    
    # Experiencia
    years_experience = fields.Integer(
        string='Años de Experiencia Total',
        default=0,
        help='Años totales de experiencia en manufactura'
    )
    
    experience_current_machine = fields.Integer(
        string='Años en Máquina Principal',
        default=0,
        help='Años de experiencia en la máquina principal actual'
    )
    
    # Turnos
    preferred_shift = fields.Selection([
        ('morning', 'Mañana (06:00-14:00)'),
        ('afternoon', 'Tarde (14:00-22:00)'),
        ('night', 'Noche (22:00-06:00)'),
        ('flexible', 'Flexible')
    ], string='Turno Preferido', default='morning')
    
    current_shift = fields.Selection([
        ('morning', 'Mañana'),
        ('afternoon', 'Tarde'),
        ('night', 'Noche'),
        ('off', 'Descanso')
    ], string='Turno Actual', default='morning')
    
    # Performance básico
    efficiency_rating = fields.Float(
        string='Calificación Eficiencia (%)',
        default=85.0,
        help='Calificación promedio de eficiencia del operador'
    )
    
    quality_rating = fields.Float(
        string='Calificación Calidad (%)',
        default=95.0,
        help='Calificación promedio de calidad del trabajo'
    )
    
    safety_rating = fields.Float(
        string='Calificación Seguridad (%)',
        default=100.0,
        help='Calificación de cumplimiento de normas de seguridad'
    )
    
    overall_performance = fields.Float(
        string='Performance General (%)',
        compute='_compute_overall_performance',
        store=True,
        help='Performance general calculado automáticamente'
    )
    
    # Fechas importantes
    hire_date = fields.Date(
        string='Fecha de Ingreso',
        help='Fecha de ingreso a la empresa'
    )
    
    last_safety_training = fields.Date(
        string='Última Capacitación Seguridad',
        help='Fecha de la última capacitación de seguridad'
    )
    
    # Mantenimiento básico
    can_perform_basic_maintenance = fields.Boolean(
        string='Mantenimiento Básico',
        default=False,
        help='Puede realizar mantenimiento de primer nivel'
    )
    
    # Estado actual
    current_status = fields.Selection([
        ('available', 'Disponible'),
        ('assigned', 'Asignado'),
        ('on_break', 'En Descanso'),
        ('training', 'En Capacitación'),
        ('vacation', 'Vacaciones'),
        ('sick', 'Incapacidad')
    ], string='Estado Actual', default='available')
    
    # Campos calculados
    workcenters_count = fields.Integer(
        string='Máquinas Certificadas',
        compute='_compute_workcenters_count'
    )
    
    # Métodos calculados
    @api.depends('name', 'operator_code')
    def _compute_display_name(self):
        """Calcular nombre para mostrar"""
        for operator in self:
            if operator.operator_code and operator.operator_code != 'OP/':
                operator.display_name = f"[{operator.operator_code}] {operator.name}"
            else:
                operator.display_name = operator.name or ''
    
    @api.depends('efficiency_rating', 'quality_rating', 'safety_rating')
    def _compute_overall_performance(self):
        """Calcular performance general ponderado"""
        for operator in self:
            # Ponderación: Calidad 40%, Eficiencia 35%, Seguridad 25%
            operator.overall_performance = (
                (operator.quality_rating * 0.40) +
                (operator.efficiency_rating * 0.35) +
                (operator.safety_rating * 0.25)
            )
    
    @api.depends('certified_workcenters')
    def _compute_workcenters_count(self):
        """Contar máquinas certificadas"""
        for operator in self:
            operator.workcenters_count = len(operator.certified_workcenters)
    
    # Métodos de acción
    def action_assign_to_workcenter(self):
        """Asignar operador a centro de trabajo"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Asignación de Operador',
                'message': f'Operador {self.name} listo para asignar. (Funcionalidad en desarrollo)',
                'type': 'info',
            }
        }
    
    def action_update_performance(self):
        """Actualizar calificaciones de performance"""
        return {
            'name': 'Actualizar Performance',
            'type': 'ir.actions.act_window',
            'res_model': 'megastock.machine.operator',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'form_view_initial_mode': 'edit',
                'focus_performance': True,
            }
        }
    
    def action_change_shift(self):
        """Cambiar turno del operador"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Cambio de Turno',
                'message': f'Turno actual del operador {self.name}: {dict(self._fields["current_shift"].selection)[self.current_shift]}',
                'type': 'info',
            }
        }
    
    def toggle_availability(self):
        """Alternar disponibilidad del operador"""
        if self.current_status == 'available':
            self.current_status = 'on_break'
            message = f'{self.name} marcado como En Descanso'
        else:
            self.current_status = 'available'
            message = f'{self.name} marcado como Disponible'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Estado Actualizado',
                'message': message,
                'type': 'success',
            }
        }


class OperatorShift(models.Model):
    _name = 'megastock.operator.shift'
    _description = 'Turno de Operador'
    _order = 'date desc, shift_type'
    
    operator_id = fields.Many2one(
        'megastock.machine.operator',
        string='Operador',
        required=True,
        ondelete='cascade'
    )
    
    workcenter_id = fields.Many2one(
        'mrp.workcenter',
        string='Centro de Trabajo',
        required=True
    )
    
    date = fields.Date(
        string='Fecha',
        required=True,
        default=fields.Date.today
    )
    
    shift_type = fields.Selection([
        ('morning', 'Mañana (06:00-14:00)'),
        ('afternoon', 'Tarde (14:00-22:00)'),
        ('night', 'Noche (22:00-06:00)')
    ], string='Turno', required=True)
    
    start_time = fields.Datetime(
        string='Hora Inicio',
        required=True
    )
    
    end_time = fields.Datetime(
        string='Hora Fin',
        required=True
    )
    
    actual_start_time = fields.Datetime(
        string='Hora Real Inicio',
        help='Hora real de inicio registrada'
    )
    
    actual_end_time = fields.Datetime(
        string='Hora Real Fin',
        help='Hora real de finalización registrada'
    )
    
    status = fields.Selection([
        ('scheduled', 'Programado'),
        ('started', 'Iniciado'),
        ('completed', 'Completado'),
        ('absent', 'Ausente'),
        ('cancelled', 'Cancelado')
    ], string='Estado', default='scheduled')
    
    notes = fields.Text(
        string='Notas',
        help='Observaciones del turno'
    )
    
    # Campos calculados
    duration_planned = fields.Float(
        string='Duración Planeada (hrs)',
        compute='_compute_duration_planned',
        store=True
    )
    
    duration_actual = fields.Float(
        string='Duración Real (hrs)',
        compute='_compute_duration_actual',
        store=True
    )
    
    @api.depends('start_time', 'end_time')
    def _compute_duration_planned(self):
        """Calcular duración planeada"""
        for shift in self:
            if shift.start_time and shift.end_time:
                duration = shift.end_time - shift.start_time
                shift.duration_planned = duration.total_seconds() / 3600.0
            else:
                shift.duration_planned = 0.0
    
    @api.depends('actual_start_time', 'actual_end_time')
    def _compute_duration_actual(self):
        """Calcular duración real"""
        for shift in self:
            if shift.actual_start_time and shift.actual_end_time:
                duration = shift.actual_end_time - shift.actual_start_time
                shift.duration_actual = duration.total_seconds() / 3600.0
            else:
                shift.duration_actual = 0.0