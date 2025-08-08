# -*- coding: utf-8 -*-

from odoo import models, fields, api

class MachineOperator(models.Model):
    _name = 'megastock.machine.operator'
    _description = 'Operador de Máquina Especializado'
    _order = 'name'
    
    name = fields.Char(
        string='Nombre Completo',
        required=True,
        help='Nombre completo del operador'
    )
    
    employee_id = fields.Many2one(
        'hr.employee',
        string='Empleado',
        required=True,
        ondelete='cascade',
        help='Referencia al empleado en recursos humanos'
    )
    
    # Información básica
    operator_code = fields.Char(
        string='Código Operador',
        required=True,
        copy=False,
        default=lambda self: self.env['ir.sequence'].next_by_code('megastock.machine.operator') or 'OP/'
    )
    
    active = fields.Boolean(
        string='Activo',
        default=True,
        help='Indica si el operador está actualmente activo'
    )
    
    # Certificaciones y competencias
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
        string='Años de Experiencia',
        default=0,
        help='Años totales de experiencia en manufactura'
    )
    
    experience_current_machine = fields.Integer(
        string='Años en Máquina Actual',
        default=0,
        help='Años de experiencia en la máquina principal actual'
    )
    
    # Horarios y turnos
    preferred_shift = fields.Selection([
        ('morning', 'Mañana (06:00-14:00)'),
        ('afternoon', 'Tarde (14:00-22:00)'),
        ('night', 'Noche (22:00-06:00)'),
        ('flexible', 'Flexible')
    ], string='Turno Preferido', default='morning')
    
    current_shift_calendar_id = fields.Many2one(
        'resource.calendar',
        string='Calendario de Turno Actual',
        help='Calendario de trabajo actual del operador'
    )
    
    # Performance y métricas
    efficiency_rating = fields.Float(
        string='Calificación de Eficiencia (%)',
        default=85.0,
        help='Calificación promedio de eficiencia del operador'
    )
    
    quality_rating = fields.Float(
        string='Calificación de Calidad (%)',
        default=95.0,
        help='Calificación promedio de calidad del trabajo'
    )
    
    safety_rating = fields.Float(
        string='Calificación de Seguridad (%)',
        default=100.0,
        help='Calificación de cumplimiento de normas de seguridad'
    )
    
    overall_performance = fields.Float(
        string='Performance General (%)',
        compute='_compute_overall_performance',
        store=True,
        help='Performance general calculado automáticamente'
    )
    
    # Capacitaciones
    training_ids = fields.One2many(
        'megastock.operator.training',
        'operator_id',
        string='Capacitaciones',
        help='Historial de capacitaciones del operador'
    )
    
    # Incidentes y seguridad
    safety_incidents_count = fields.Integer(
        string='Incidentes de Seguridad',
        default=0,
        help='Número de incidentes de seguridad registrados'
    )
    
    last_safety_training = fields.Date(
        string='Última Capacitación de Seguridad',
        help='Fecha de la última capacitación de seguridad'
    )
    
    # Mantenimiento de primer nivel
    can_perform_basic_maintenance = fields.Boolean(
        string='Puede Realizar Mantenimiento Básico',
        default=False,
        help='Indica si el operador puede realizar mantenimiento de primer nivel'
    )
    
    maintenance_certification_date = fields.Date(
        string='Fecha Certificación Mantenimiento',
        help='Fecha de certificación para mantenimiento básico'
    )
    
    # Historial de asignaciones
    assignment_history_ids = fields.One2many(
        'megastock.operator.assignment',
        'operator_id',
        string='Historial de Asignaciones',
        help='Historial de asignaciones a diferentes máquinas'
    )
    
    # Campos calculados
    current_assignment = fields.Char(
        string='Asignación Actual',
        compute='_compute_current_assignment',
        help='Asignación actual del operador'
    )
    
    days_since_last_incident = fields.Integer(
        string='Días sin Incidentes',
        compute='_compute_safety_metrics',
        help='Días transcurridos desde el último incidente de seguridad'
    )
    
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
    
    @api.depends('assignment_history_ids')
    def _compute_current_assignment(self):
        """Determinar asignación actual"""
        for operator in self:
            current_assignment = operator.assignment_history_ids.filtered(
                lambda a: not a.end_date or a.end_date >= fields.Date.today()
            )
            if current_assignment:
                operator.current_assignment = current_assignment[0].workcenter_id.name
            else:
                operator.current_assignment = 'Sin asignación'
    
    def _compute_safety_metrics(self):
        """Calcular métricas de seguridad"""
        for operator in self:
            # Esta función se puede implementar con datos reales de incidentes
            # Por ahora, establecer un valor por defecto
            operator.days_since_last_incident = 90
    
    def action_assign_to_workcenter(self):
        """Asignar operador a centro de trabajo"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Asignar a Centro de Trabajo',
            'res_model': 'megastock.operator.assignment',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_operator_id': self.id,
                'default_start_date': fields.Date.today(),
            }
        }
    
    def action_schedule_training(self):
        """Programar capacitación"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Programar Capacitación',
            'res_model': 'megastock.operator.training',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_operator_id': self.id,
                'default_training_date': fields.Date.today(),
            }
        }
    
    def action_update_performance(self):
        """Actualizar calificaciones de performance"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Actualizar Performance',
            'res_model': 'megastock.operator.performance.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_operator_id': self.id,
            }
        }


class OperatorTraining(models.Model):
    _name = 'megastock.operator.training'
    _description = 'Capacitación de Operador'
    _order = 'training_date desc'
    
    operator_id = fields.Many2one(
        'megastock.machine.operator',
        string='Operador',
        required=True,
        ondelete='cascade'
    )
    
    training_type = fields.Selection([
        ('safety', 'Seguridad Industrial'),
        ('technical', 'Técnica Especializada'),
        ('quality', 'Control de Calidad'),
        ('maintenance', 'Mantenimiento Básico'),
        ('software', 'Software/Sistemas'),
        ('leadership', 'Liderazgo'),
        ('other', 'Otro')
    ], string='Tipo de Capacitación', required=True)
    
    training_name = fields.Char(
        string='Nombre de la Capacitación',
        required=True
    )
    
    training_date = fields.Date(
        string='Fecha de Capacitación',
        required=True
    )
    
    duration_hours = fields.Float(
        string='Duración (Horas)',
        required=True
    )
    
    instructor = fields.Char(
        string='Instructor',
        help='Nombre del instructor o institución'
    )
    
    certificate_obtained = fields.Boolean(
        string='Certificado Obtenido',
        default=False
    )
    
    certificate_expiry_date = fields.Date(
        string='Fecha Vencimiento Certificado',
        help='Fecha de vencimiento del certificado (si aplica)'
    )
    
    training_score = fields.Float(
        string='Calificación (%)',
        help='Calificación obtenida en la capacitación'
    )
    
    notes = fields.Text(
        string='Notas',
        help='Observaciones adicionales sobre la capacitación'
    )


class OperatorAssignment(models.Model):
    _name = 'megastock.operator.assignment'
    _description = 'Asignación de Operador a Centro de Trabajo'
    _order = 'start_date desc'
    
    operator_id = fields.Many2one(
        'megastock.machine.operator',
        string='Operador',
        required=True,
        ondelete='cascade'
    )
    
    workcenter_id = fields.Many2one(
        'mrp.workcenter',
        string='Centro de Trabajo',
        required=True,
        ondelete='restrict'
    )
    
    start_date = fields.Date(
        string='Fecha Inicio',
        required=True,
        default=fields.Date.today
    )
    
    end_date = fields.Date(
        string='Fecha Fin',
        help='Fecha de finalización de la asignación (vacío = asignación actual)'
    )
    
    assignment_type = fields.Selection([
        ('primary', 'Asignación Principal'),
        ('backup', 'Respaldo/Suplente'),
        ('training', 'Entrenamiento'),
        ('temporary', 'Temporal')
    ], string='Tipo de Asignación', default='primary', required=True)
    
    shift_calendar_id = fields.Many2one(
        'resource.calendar',
        string='Turno Asignado',
        required=True
    )
    
    is_active = fields.Boolean(
        string='Asignación Activa',
        compute='_compute_is_active',
        store=True
    )
    
    notes = fields.Text(
        string='Notas',
        help='Observaciones sobre la asignación'
    )
    
    @api.depends('start_date', 'end_date')
    def _compute_is_active(self):
        """Determinar si la asignación está activa"""
        today = fields.Date.today()
        for assignment in self:
            assignment.is_active = (
                assignment.start_date <= today and
                (not assignment.end_date or assignment.end_date >= today)
            )