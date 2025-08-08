# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import timedelta

class MachineDowntime(models.Model):
    _name = 'megastock.machine.downtime'
    _description = 'Registro de Paradas No Programadas'
    _order = 'start_datetime desc'
    _rec_name = 'name'
    
    name = fields.Char(
        string='Referencia',
        required=True,
        copy=False,
        default=lambda self: self.env['ir.sequence'].next_by_code('megastock.machine.downtime') or 'DT/'
    )
    
    # Información Básica
    workcenter_id = fields.Many2one(
        'mrp.workcenter',
        string='Centro de Trabajo',
        required=True,
        ondelete='restrict'
    )
    
    equipment_id = fields.Many2one(
        'maintenance.equipment',
        string='Equipo',
        related='workcenter_id.maintenance_equipment_ids',
        store=True
    )
    
    # Fechas y Duración
    start_datetime = fields.Datetime(
        string='Inicio de Parada',
        required=True,
        default=fields.Datetime.now
    )
    
    end_datetime = fields.Datetime(
        string='Fin de Parada'
    )
    
    duration_hours = fields.Float(
        string='Duración (Horas)',
        compute='_compute_duration',
        store=True,
        help='Duración total de la parada en horas'
    )
    
    duration_minutes = fields.Integer(
        string='Minutos Totales',
        compute='_compute_duration',
        store=True
    )
    
    # Clasificación de la Parada
    downtime_type = fields.Selection([
        ('mechanical', 'Falla Mecánica'),
        ('electrical', 'Falla Eléctrica'),
        ('pneumatic', 'Falla Neumática/Hidráulica'),
        ('software', 'Problema de Software/Control'),
        ('material', 'Problema de Material'),
        ('quality', 'Problema de Calidad'),
        ('setup', 'Problema de Setup'),
        ('operator', 'Error de Operador'),
        ('external', 'Factor Externo'),
        ('other', 'Otro')
    ], string='Tipo de Parada', required=True)
    
    severity = fields.Selection([
        ('low', 'Baja'),
        ('medium', 'Media'),
        ('high', 'Alta'),
        ('critical', 'Crítica')
    ], string='Severidad', required=True, default='medium')
    
    # Descripción del Problema
    problem_description = fields.Text(
        string='Descripción del Problema',
        required=True,
        help='Descripción detallada del problema que causó la parada'
    )
    
    root_cause = fields.Text(
        string='Causa Raíz',
        help='Análisis de la causa raíz del problema'
    )
    
    solution_applied = fields.Text(
        string='Solución Aplicada',
        help='Descripción de las acciones tomadas para resolver el problema'
    )
    
    # Personal Involucrado
    reported_by = fields.Many2one(
        'hr.employee',
        string='Reportado por',
        required=True,
        default=lambda self: self.env.user.employee_id
    )
    
    operator_id = fields.Many2one(
        'hr.employee',
        string='Operador en Turno',
        help='Operador que estaba en turno cuando ocurrió la parada'
    )
    
    maintenance_technician_id = fields.Many2one(
        'hr.employee',
        string='Técnico de Mantenimiento',
        help='Técnico que atendió la parada'
    )
    
    supervisor_id = fields.Many2one(
        'hr.employee',
        string='Supervisor',
        help='Supervisor que validó la resolución'
    )
    
    # Estado del Registro
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('reported', 'Reportado'),
        ('in_progress', 'En Progreso'),
        ('resolved', 'Resuelto'),
        ('cancelled', 'Cancelado')
    ], string='Estado', default='draft', required=True)
    
    # Impacto Económico
    production_lost_units = fields.Float(
        string='Unidades Perdidas',
        help='Cantidad de unidades que se dejaron de producir'
    )
    
    estimated_cost_loss = fields.Float(
        string='Costo Estimado Pérdida (USD)',
        compute='_compute_cost_impact',
        store=True,
        help='Costo estimado de la pérdida por parada'
    )
    
    repair_cost = fields.Float(
        string='Costo de Reparación (USD)',
        help='Costo directo de materiales y mano de obra para la reparación'
    )
    
    # Órdenes de Producción Afectadas
    production_order_ids = fields.Many2many(
        'mrp.production',
        'downtime_production_rel',
        'downtime_id',
        'production_id',
        string='Órdenes de Producción Afectadas'
    )
    
    # Repuestos Utilizados
    spare_part_ids = fields.Many2many(
        'product.product',
        'downtime_spare_parts_rel',
        'downtime_id',
        'product_id',
        string='Repuestos Utilizados',
        domain=[('categ_id.name', 'ilike', 'Repuestos')]
    )
    
    # Solicitud de Mantenimiento Generada
    maintenance_request_id = fields.Many2one(
        'maintenance.request',
        string='Solicitud de Mantenimiento',
        help='Solicitud de mantenimiento correctivo generada automáticamente'
    )
    
    # Seguimiento y Prevención
    preventive_actions = fields.Text(
        string='Acciones Preventivas',
        help='Acciones recomendadas para prevenir futuros problemas similares'
    )
    
    follow_up_required = fields.Boolean(
        string='Requiere Seguimiento',
        default=False,
        help='Marcar si el problema requiere seguimiento adicional'
    )
    
    follow_up_date = fields.Date(
        string='Fecha de Seguimiento',
        help='Fecha programada para verificar que la solución es efectiva'
    )
    
    # Campos Computados
    is_recurring = fields.Boolean(
        string='Es Recurrente',
        compute='_compute_is_recurring',
        store=True,
        help='Indica si este tipo de problema es recurrente en esta máquina'
    )
    
    @api.depends('start_datetime', 'end_datetime')
    def _compute_duration(self):
        """Calcular duración de la parada"""
        for record in self:
            if record.start_datetime and record.end_datetime:
                delta = record.end_datetime - record.start_datetime
                record.duration_hours = delta.total_seconds() / 3600.0
                record.duration_minutes = int(delta.total_seconds() / 60)
            else:
                record.duration_hours = 0.0
                record.duration_minutes = 0
    
    @api.depends('duration_hours', 'workcenter_id.costs_hour', 'workcenter_id.real_capacity')
    def _compute_cost_impact(self):
        """Calcular impacto económico de la parada"""
        for record in self:
            if record.duration_hours and record.workcenter_id:
                # Costo por hora operativa perdida
                hourly_cost = record.workcenter_id.costs_hour or 0.0
                
                # Agregar costo de oportunidad (producción perdida)
                if record.workcenter_id.real_capacity:
                    # Asumir margen promedio de $0.50 por unidad
                    AVERAGE_MARGIN = 0.50
                    opportunity_cost = (
                        record.workcenter_id.real_capacity * 
                        record.duration_hours * 
                        AVERAGE_MARGIN
                    )
                else:
                    opportunity_cost = 0.0
                
                record.estimated_cost_loss = (hourly_cost * record.duration_hours) + opportunity_cost
            else:
                record.estimated_cost_loss = 0.0
    
    @api.depends('workcenter_id', 'downtime_type')
    def _compute_is_recurring(self):
        """Verificar si el problema es recurrente"""
        for record in self:
            if record.workcenter_id and record.downtime_type:
                # Buscar problemas similares en los últimos 30 días
                similar_problems = self.search([
                    ('workcenter_id', '=', record.workcenter_id.id),
                    ('downtime_type', '=', record.downtime_type),
                    ('start_datetime', '>=', fields.Datetime.now() - timedelta(days=30)),
                    ('id', '!=', record.id)
                ])
                record.is_recurring = len(similar_problems) >= 2
            else:
                record.is_recurring = False
    
    @api.model
    def create(self, vals):
        """Crear secuencia automática y solicitud de mantenimiento"""
        if vals.get('name', 'DT/') == 'DT/':
            vals['name'] = self.env['ir.sequence'].next_by_code('megastock.machine.downtime') or 'DT/'
        
        record = super(MachineDowntime, self).create(vals)
        
        # Crear solicitud de mantenimiento correctivo automática si es severidad alta o crítica
        if record.severity in ['high', 'critical']:
            record._create_maintenance_request()
        
        return record
    
    def _create_maintenance_request(self):
        """Crear solicitud de mantenimiento correctivo automática"""
        if not self.maintenance_request_id and self.workcenter_id.maintenance_equipment_ids:
            maintenance_request = self.env['maintenance.request'].create({
                'name': f'Correctivo - {self.name}: {self.problem_description[:50]}...',
                'equipment_id': self.workcenter_id.maintenance_equipment_ids[0].id,
                'maintenance_type': 'corrective',
                'priority': '3' if self.severity == 'critical' else '2',
                'description': f"""
Solicitud generada automáticamente por parada no programada.

Problema: {self.problem_description}
Tipo: {dict(self._fields['downtime_type'].selection)[self.downtime_type]}
Severidad: {dict(self._fields['severity'].selection)[self.severity]}
Duración: {self.duration_hours:.2f} horas
Costo estimado: ${self.estimated_cost_loss:.2f}

Referencia: {self.name}
                """,
                'request_date': self.start_datetime,
                'user_id': self.reported_by.user_id.id if self.reported_by.user_id else False,
            })
            self.maintenance_request_id = maintenance_request.id
    
    def action_report(self):
        """Reportar la parada"""
        self.state = 'reported'
        if self.severity in ['high', 'critical']:
            self._create_maintenance_request()
        return True
    
    def action_start_repair(self):
        """Iniciar reparación"""
        self.state = 'in_progress'
        return True
    
    def action_resolve(self):
        """Resolver la parada"""
        if not self.end_datetime:
            self.end_datetime = fields.Datetime.now()
        
        self.state = 'resolved'
        
        # Cambiar estado de la máquina a operativa
        if self.workcenter_id:
            self.workcenter_id.machine_status = 'operational'
        
        # Si es problema recurrente, programar seguimiento
        if self.is_recurring and not self.follow_up_date:
            self.follow_up_required = True
            self.follow_up_date = fields.Date.today() + timedelta(days=7)
        
        return True
    
    def action_cancel(self):
        """Cancelar registro de parada"""
        self.state = 'cancelled'
        return True
    
    def action_create_preventive_maintenance(self):
        """Crear mantenimiento preventivo basado en este problema"""
        if not self.preventive_actions:
            raise models.UserError("Debe especificar las acciones preventivas antes de crear el mantenimiento.")
        
        maintenance_request = self.env['maintenance.request'].create({
            'name': f'Preventivo - Evitar: {self.problem_description[:50]}...',
            'equipment_id': self.workcenter_id.maintenance_equipment_ids[0].id if self.workcenter_id.maintenance_equipment_ids else False,
            'maintenance_type': 'preventive',
            'priority': '1',
            'description': f"""
Mantenimiento preventivo basado en análisis de parada no programada.

Problema a prevenir: {self.problem_description}
Causa raíz: {self.root_cause or 'Por determinar'}
Acciones preventivas: {self.preventive_actions}

Referencia parada: {self.name}
            """,
            'schedule_date': fields.Datetime.now() + timedelta(days=30),
        })
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Mantenimiento Preventivo Creado',
            'res_model': 'maintenance.request',
            'res_id': maintenance_request.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    @api.model
    def get_downtime_statistics(self, date_from, date_to, workcenter_ids=None):
        """Obtener estadísticas de paradas para dashboard"""
        domain = [
            ('start_datetime', '>=', date_from),
            ('start_datetime', '<=', date_to),
            ('state', '=', 'resolved')
        ]
        
        if workcenter_ids:
            domain.append(('workcenter_id', 'in', workcenter_ids))
        
        downtime_records = self.search(domain)
        
        # Agrupar por tipo
        stats_by_type = {}
        for record in downtime_records:
            downtime_type = record.downtime_type
            if downtime_type not in stats_by_type:
                stats_by_type[downtime_type] = {
                    'count': 0,
                    'total_hours': 0.0,
                    'total_cost': 0.0
                }
            stats_by_type[downtime_type]['count'] += 1
            stats_by_type[downtime_type]['total_hours'] += record.duration_hours
            stats_by_type[downtime_type]['total_cost'] += record.estimated_cost_loss
        
        return {
            'total_downtime_hours': sum(r.duration_hours for r in downtime_records),
            'total_cost_impact': sum(r.estimated_cost_loss for r in downtime_records),
            'total_incidents': len(downtime_records),
            'by_type': stats_by_type,
            'recurring_issues': downtime_records.filtered('is_recurring').mapped('name')
        }