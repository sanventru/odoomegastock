# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging
import json

_logger = logging.getLogger(__name__)

class ProductionAlert(models.Model):
    _name = 'megastock.production.alert'
    _description = 'Alertas de Producción MEGASTOCK'
    _order = 'priority desc, create_date desc'
    _rec_name = 'title'

    # Campos básicos
    title = fields.Char('Título', required=True, size=200)
    message = fields.Text('Mensaje', required=True)
    alert_type = fields.Selection([
        ('kpi', 'KPI Crítico'),
        ('capacity', 'Capacidad'),
        ('schedule', 'Cronograma'),
        ('quality', 'Calidad'),
        ('downtime', 'Tiempo Muerto'),
        ('bottleneck', 'Cuello de Botella'),
        ('maintenance', 'Mantenimiento'),
        ('resource', 'Recursos'),
        ('delivery', 'Entregas'),
        ('system', 'Sistema')
    ], string='Tipo de Alerta', required=True, default='system')

    # Prioridad y severidad
    priority = fields.Selection([
        ('1', 'Baja'),
        ('2', 'Media'),
        ('3', 'Alta'),
        ('4', 'Crítica'),
        ('5', 'Emergencia')
    ], string='Prioridad', required=True, default='2')

    severity = fields.Selection([
        ('info', 'Información'),
        ('warning', 'Advertencia'),
        ('error', 'Error'),
        ('critical', 'Crítico')
    ], string='Severidad', required=True, default='info')

    # Estado y fechas
    state = fields.Selection([
        ('active', 'Activa'),
        ('acknowledged', 'Reconocida'),
        ('resolved', 'Resuelta'),
        ('escalated', 'Escalada'),
        ('expired', 'Expirada')
    ], string='Estado', default='active', required=True)

    # Fechas importantes
    detection_date = fields.Datetime('Fecha Detección', required=True, default=fields.Datetime.now)
    acknowledgment_date = fields.Datetime('Fecha Reconocimiento')
    resolution_date = fields.Datetime('Fecha Resolución')
    escalation_date = fields.Datetime('Fecha Escalación')
    expiry_date = fields.Datetime('Fecha Expiración')

    # Escalación automática
    auto_escalate = fields.Boolean('Escalación Automática', default=True)
    escalation_time = fields.Integer('Tiempo para Escalación (minutos)', default=30)
    escalation_count = fields.Integer('Número de Escalaciones', default=0)
    max_escalations = fields.Integer('Máximo Escalaciones', default=3)

    # Relaciones
    workcenter_id = fields.Many2one('mrp.workcenter', 'Centro de Trabajo')
    production_id = fields.Many2one('mrp.production', 'Producción')
    plan_id = fields.Many2one('megastock.production.plan', 'Plan de Producción')
    kpi_id = fields.Many2one('megastock.production.kpi', 'KPI Asociado')
    
    # Línea de producción específica de MEGASTOCK
    production_line = fields.Selection([
        ('papel_periodico', 'Papel Periódico'),
        ('cajas', 'Cajas & Planchas'),
        ('lamina_micro', 'Lámina Micro'),
        ('all', 'Todas las Líneas')
    ], string='Línea de Producción', default='all')

    # Destinatarios y responsables
    responsible_user_id = fields.Many2one('res.users', 'Usuario Responsable')
    acknowledged_by = fields.Many2one('res.users', 'Reconocida por')
    resolved_by = fields.Many2one('res.users', 'Resuelta por')
    
    # Configuración de escalación
    escalation_user_ids = fields.Many2many('res.users', 'alert_escalation_user_rel', 
                                          'alert_id', 'user_id', 
                                          string='Usuarios para Escalación')
    
    # Metadata adicional
    source_model = fields.Char('Modelo Origen', size=100)
    source_id = fields.Integer('ID Origen')
    additional_data = fields.Text('Datos Adicionales JSON')
    
    # Acciones automáticas
    auto_actions = fields.Text('Acciones Automáticas')
    action_taken = fields.Text('Acción Tomada')
    
    # Métricas
    response_time = fields.Float('Tiempo de Respuesta (min)', compute='_compute_response_time', store=True)
    resolution_time = fields.Float('Tiempo de Resolución (min)', compute='_compute_resolution_time', store=True)
    
    # Repetición de alerta
    is_recurring = fields.Boolean('Es Recurrente', default=False)
    recurrence_count = fields.Integer('Contador de Recurrencia', default=0)
    last_occurrence = fields.Datetime('Última Ocurrencia')

    @api.depends('detection_date', 'acknowledgment_date')
    def _compute_response_time(self):
        for alert in self:
            if alert.acknowledgment_date and alert.detection_date:
                delta = alert.acknowledgment_date - alert.detection_date
                alert.response_time = delta.total_seconds() / 60
            else:
                alert.response_time = 0

    @api.depends('detection_date', 'resolution_date')
    def _compute_resolution_time(self):
        for alert in self:
            if alert.resolution_date and alert.detection_date:
                delta = alert.resolution_date - alert.detection_date
                alert.resolution_time = delta.total_seconds() / 60
            else:
                alert.resolution_time = 0

    @api.model
    def create_alert(self, alert_type, title, message, **kwargs):
        """Método helper para crear alertas programáticamente"""
        values = {
            'alert_type': alert_type,
            'title': title,
            'message': message,
            'priority': kwargs.get('priority', '2'),
            'severity': kwargs.get('severity', 'warning'),
            'production_line': kwargs.get('production_line', 'all'),
            'workcenter_id': kwargs.get('workcenter_id'),
            'production_id': kwargs.get('production_id'),
            'plan_id': kwargs.get('plan_id'),
            'kpi_id': kwargs.get('kpi_id'),
            'responsible_user_id': kwargs.get('responsible_user_id'),
            'auto_escalate': kwargs.get('auto_escalate', True),
            'escalation_time': kwargs.get('escalation_time', 30),
            'additional_data': json.dumps(kwargs.get('additional_data', {}))
        }
        
        # Verificar si es una alerta recurrente
        existing_alert = self.search([
            ('alert_type', '=', alert_type),
            ('title', '=', title),
            ('state', 'in', ['active', 'acknowledged']),
            ('workcenter_id', '=', kwargs.get('workcenter_id'))
        ], limit=1)
        
        if existing_alert:
            existing_alert.recurrence_count += 1
            existing_alert.last_occurrence = fields.Datetime.now()
            existing_alert.is_recurring = True
            return existing_alert
        
        alert = self.create(values)
        alert._setup_auto_escalation()
        alert._trigger_immediate_actions()
        return alert

    def _setup_auto_escalation(self):
        """Configura la escalación automática si está habilitada"""
        if self.auto_escalate and self.escalation_time > 0:
            escalation_datetime = self.detection_date + timedelta(minutes=self.escalation_time)
            self.escalation_date = escalation_datetime
            
            # Programar job de escalación
            self.env['ir.cron'].sudo().create({
                'name': f'Escalación Alerta {self.id}',
                'model_id': self.env.ref('megastock_production_planning.model_megastock_production_alert').id,
                'state': 'code',
                'code': f'model.browse({self.id}).escalate_alert()',
                'interval_number': self.escalation_time,
                'interval_type': 'minutes',
                'numbercall': 1,
                'active': True,
                'nextcall': escalation_datetime
            })

    def _trigger_immediate_actions(self):
        """Ejecuta acciones inmediatas basadas en el tipo y severidad de alerta"""
        
        # Notificación inmediata para alertas críticas
        if self.severity in ['error', 'critical'] or self.priority in ['4', '5']:
            self._send_immediate_notification()
        
        # Acciones automáticas por tipo de alerta
        if self.alert_type == 'kpi' and self.severity == 'critical':
            self._handle_critical_kpi()
        elif self.alert_type == 'bottleneck':
            self._handle_bottleneck_alert()
        elif self.alert_type == 'downtime':
            self._handle_downtime_alert()
        elif self.alert_type == 'quality':
            self._handle_quality_alert()

    def _send_immediate_notification(self):
        """Envía notificación inmediata a usuarios relevantes"""
        users_to_notify = []
        
        # Determinar usuarios según el tipo de alerta
        if self.responsible_user_id:
            users_to_notify.append(self.responsible_user_id)
        
        # Supervisores y gerentes de la línea específica
        line_groups = {
            'papel_periodico': 'group_production_supervisor',
            'cajas': 'group_production_supervisor', 
            'lamina_micro': 'group_production_supervisor',
            'all': 'group_production_manager'
        }
        
        group_name = line_groups.get(self.production_line, 'group_production_manager')
        group = self.env.ref(f'megastock_production_planning.{group_name}', raise_if_not_found=False)
        
        if group:
            users_to_notify.extend(group.users)

        # Crear notificaciones
        for user in set(users_to_notify):
            self.env['mail.message'].create({
                'subject': f'🚨 ALERTA {self.severity.upper()}: {self.title}',
                'body': f"""
                <div style="background-color: #f8d7da; padding: 15px; border-radius: 5px;">
                    <h3 style="color: #721c24;">Alerta de Producción MEGASTOCK</h3>
                    <p><strong>Tipo:</strong> {dict(self._fields['alert_type'].selection)[self.alert_type]}</p>
                    <p><strong>Línea:</strong> {dict(self._fields['production_line'].selection)[self.production_line]}</p>
                    <p><strong>Mensaje:</strong> {self.message}</p>
                    <p><strong>Prioridad:</strong> {dict(self._fields['priority'].selection)[self.priority]}</p>
                    <p><strong>Hora:</strong> {self.detection_date.strftime('%d/%m/%Y %H:%M:%S')}</p>
                </div>
                """,
                'message_type': 'notification',
                'author_id': self.env.user.partner_id.id,
                'partner_ids': [(4, user.partner_id.id)]
            })

    def acknowledge_alert(self):
        """Reconoce la alerta"""
        self.ensure_one()
        if self.state == 'active':
            self.write({
                'state': 'acknowledged',
                'acknowledgment_date': fields.Datetime.now(),
                'acknowledged_by': self.env.user.id
            })
            
            # Cancelar escalación automática
            cron_jobs = self.env['ir.cron'].search([
                ('name', 'like', f'Escalación Alerta {self.id}'),
                ('active', '=', True)
            ])
            cron_jobs.write({'active': False})
            
            return True
        return False

    def resolve_alert(self, resolution_note=None):
        """Resuelve la alerta"""
        self.ensure_one()
        if self.state in ['active', 'acknowledged', 'escalated']:
            values = {
                'state': 'resolved',
                'resolution_date': fields.Datetime.now(),
                'resolved_by': self.env.user.id
            }
            
            if resolution_note:
                values['action_taken'] = resolution_note
                
            self.write(values)
            
            # Cancelar escalación automática
            cron_jobs = self.env['ir.cron'].search([
                ('name', 'like', f'Escalación Alerta {self.id}'),
                ('active', '=', True)
            ])
            cron_jobs.write({'active': False})
            
            return True
        return False

    def escalate_alert(self):
        """Escala la alerta al siguiente nivel"""
        self.ensure_one()
        
        if self.state not in ['active', 'acknowledged'] or self.escalation_count >= self.max_escalations:
            return False
            
        self.write({
            'state': 'escalated',
            'escalation_count': self.escalation_count + 1,
            'escalation_date': fields.Datetime.now()
        })
        
        # Enviar notificación de escalación
        self._send_escalation_notification()
        
        # Configurar siguiente escalación si no se ha alcanzado el máximo
        if self.escalation_count < self.max_escalations:
            next_escalation = fields.Datetime.now() + timedelta(minutes=self.escalation_time * 2)
            self.env['ir.cron'].sudo().create({
                'name': f'Escalación Alerta {self.id} - Nivel {self.escalation_count + 1}',
                'model_id': self.env.ref('megastock_production_planning.model_megastock_production_alert').id,
                'state': 'code',
                'code': f'model.browse({self.id}).escalate_alert()',
                'interval_number': self.escalation_time * 2,
                'interval_type': 'minutes',
                'numbercall': 1,
                'active': True,
                'nextcall': next_escalation
            })
        
        return True

    def _send_escalation_notification(self):
        """Envía notificación de escalación"""
        # Determinar usuarios para escalación
        escalation_users = []
        
        if self.escalation_user_ids:
            escalation_users = self.escalation_user_ids
        else:
            # Escalar según nivel de escalación
            if self.escalation_count == 1:
                group = self.env.ref('megastock_production_planning.group_production_supervisor')
            elif self.escalation_count == 2:
                group = self.env.ref('megastock_production_planning.group_production_manager')
            else:
                group = self.env.ref('megastock_production_planning.group_production_admin')
            
            escalation_users = group.users
        
        # Crear notificaciones de escalación
        for user in escalation_users:
            self.env['mail.message'].create({
                'subject': f'🔺 ESCALACIÓN NIVEL {self.escalation_count}: {self.title}',
                'body': f"""
                <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px;">
                    <h3 style="color: #856404;">Alerta Escalada - Requiere Atención Inmediata</h3>
                    <p><strong>Alerta:</strong> {self.title}</p>
                    <p><strong>Nivel de Escalación:</strong> {self.escalation_count} de {self.max_escalations}</p>
                    <p><strong>Tiempo sin resolver:</strong> {self.resolution_time} minutos</p>
                    <p><strong>Línea:</strong> {dict(self._fields['production_line'].selection)[self.production_line]}</p>
                    <p><strong>Mensaje:</strong> {self.message}</p>
                </div>
                """,
                'message_type': 'notification',
                'author_id': self.env.user.partner_id.id,
                'partner_ids': [(4, user.partner_id.id)]
            })

    def _handle_critical_kpi(self):
        """Maneja alertas críticas de KPI"""
        if self.kpi_id:
            # Verificar si se puede tomar acción correctiva automática
            if self.kpi_id.kpi_type == 'oee' and self.kpi_id.value < 70:
                # Alerta crítica de OEE - verificar componentes
                self._trigger_oee_analysis()
            elif self.kpi_id.kpi_type == 'quality' and self.kpi_id.value < 95:
                # Alerta de calidad - pausar producción si es crítico
                self._trigger_quality_stop()

    def _handle_bottleneck_alert(self):
        """Maneja alertas de cuello de botella"""
        if self.workcenter_id:
            # Buscar alternativas de reprogramación
            schedule_model = self.env['megastock.production.schedule']
            schedule_model.auto_rebalance_workcenter(self.workcenter_id.id)

    def _handle_downtime_alert(self):
        """Maneja alertas de tiempo muerto"""
        if self.workcenter_id:
            # Notificar a mantenimiento y verificar disponibilidad
            maintenance_group = self.env.ref('base.group_user')  # Cambiar por grupo de mantenimiento real
            for user in maintenance_group.users:
                self.env['mail.message'].create({
                    'subject': f'Tiempo Muerto Detectado: {self.workcenter_id.name}',
                    'body': f'Centro de trabajo {self.workcenter_id.name} reporta tiempo muerto. Verificar estado.',
                    'message_type': 'notification',
                    'author_id': self.env.user.partner_id.id,
                    'partner_ids': [(4, user.partner_id.id)]
                })

    def _handle_quality_alert(self):
        """Maneja alertas de calidad"""
        if self.production_id and self.severity == 'critical':
            # Para alertas críticas de calidad, considerar pausar la producción
            self.production_id.message_post(
                body=f"Alerta crítica de calidad detectada: {self.message}. Revisar antes de continuar.",
                subject="Alerta de Calidad Crítica"
            )

    def _trigger_oee_analysis(self):
        """Dispara análisis detallado de OEE"""
        if self.kpi_id:
            analysis_data = {
                'alert_id': self.id,
                'kpi_id': self.kpi_id.id,
                'analysis_type': 'oee_breakdown',
                'trigger_time': fields.Datetime.now()
            }
            
            self.additional_data = json.dumps(analysis_data)

    def _trigger_quality_stop(self):
        """Dispara parada por calidad si es necesario"""
        if self.production_id and self.severity == 'critical':
            # En implementación real, esto podría pausar la producción
            self.action_taken = f"Recomendación de parada por calidad crítica en {self.production_id.name}"

    @api.model
    def cleanup_expired_alerts(self):
        """Limpia alertas expiradas automáticamente"""
        expired_alerts = self.search([
            ('state', 'in', ['active', 'acknowledged']),
            ('expiry_date', '<', fields.Datetime.now())
        ])
        
        expired_alerts.write({'state': 'expired'})
        return len(expired_alerts)

    @api.model
    def get_dashboard_alerts(self, production_line='all', limit=10):
        """Obtiene alertas para dashboard"""
        domain = [('state', 'in', ['active', 'acknowledged', 'escalated'])]
        
        if production_line != 'all':
            domain.append(('production_line', 'in', [production_line, 'all']))
        
        alerts = self.search(domain, order='priority desc, detection_date desc', limit=limit)
        
        alert_data = []
        for alert in alerts:
            alert_data.append({
                'id': alert.id,
                'title': alert.title,
                'message': alert.message,
                'alert_type': alert.alert_type,
                'priority': alert.priority,
                'severity': alert.severity,
                'state': alert.state,
                'detection_date': alert.detection_date.strftime('%d/%m/%Y %H:%M') if alert.detection_date else '',
                'production_line': alert.production_line,
                'escalation_count': alert.escalation_count,
                'is_recurring': alert.is_recurring,
                'recurrence_count': alert.recurrence_count
            })
        
        return alert_data

    @api.model
    def get_alert_statistics(self, days=7):
        """Obtiene estadísticas de alertas"""
        from_date = fields.Datetime.now() - timedelta(days=days)
        
        # Contar alertas por tipo
        type_stats = {}
        for alert_type, name in self._fields['alert_type'].selection:
            count = self.search_count([
                ('alert_type', '=', alert_type),
                ('detection_date', '>=', from_date)
            ])
            type_stats[alert_type] = count
        
        # Contar alertas por severidad
        severity_stats = {}
        for severity, name in self._fields['severity'].selection:
            count = self.search_count([
                ('severity', '=', severity),
                ('detection_date', '>=', from_date)
            ])
            severity_stats[severity] = count
        
        # Métricas de resolución
        resolved_alerts = self.search([
            ('state', '=', 'resolved'),
            ('detection_date', '>=', from_date)
        ])
        
        avg_resolution_time = sum(resolved_alerts.mapped('resolution_time')) / len(resolved_alerts) if resolved_alerts else 0
        avg_response_time = sum(resolved_alerts.mapped('response_time')) / len(resolved_alerts) if resolved_alerts else 0
        
        return {
            'type_distribution': type_stats,
            'severity_distribution': severity_stats,
            'total_alerts': sum(type_stats.values()),
            'resolved_alerts': len(resolved_alerts),
            'avg_resolution_time': round(avg_resolution_time, 2),
            'avg_response_time': round(avg_response_time, 2),
            'resolution_rate': (len(resolved_alerts) / sum(type_stats.values()) * 100) if sum(type_stats.values()) > 0 else 0
        }


class AlertEscalationRule(models.Model):
    _name = 'megastock.alert.escalation.rule'
    _description = 'Reglas de Escalación de Alertas'
    _order = 'sequence, id'

    name = fields.Char('Nombre', required=True)
    sequence = fields.Integer('Secuencia', default=10)
    active = fields.Boolean('Activo', default=True)

    # Condiciones
    alert_type = fields.Selection([
        ('kpi', 'KPI Crítico'),
        ('capacity', 'Capacidad'),
        ('schedule', 'Cronograma'),
        ('quality', 'Calidad'),
        ('downtime', 'Tiempo Muerto'),
        ('bottleneck', 'Cuello de Botella'),
        ('maintenance', 'Mantenimiento'),
        ('resource', 'Recursos'),
        ('delivery', 'Entregas'),
        ('system', 'Sistema')
    ], string='Tipo de Alerta')

    severity = fields.Selection([
        ('info', 'Información'),
        ('warning', 'Advertencia'), 
        ('error', 'Error'),
        ('critical', 'Crítico')
    ], string='Severidad Mínima')

    production_line = fields.Selection([
        ('papel_periodico', 'Papel Periódico'),
        ('cajas', 'Cajas & Planchas'),
        ('lamina_micro', 'Lámina Micro'),
        ('all', 'Todas las Líneas')
    ], string='Línea de Producción')

    # Configuración de escalación
    escalation_time = fields.Integer('Tiempo de Escalación (minutos)', required=True, default=30)
    max_escalations = fields.Integer('Máximo Escalaciones', required=True, default=3)
    
    # Destinatarios por nivel de escalación
    level_1_user_ids = fields.Many2many('res.users', 'escalation_rule_level1_rel', 
                                        'rule_id', 'user_id', string='Nivel 1 - Usuarios')
    level_2_user_ids = fields.Many2many('res.users', 'escalation_rule_level2_rel',
                                        'rule_id', 'user_id', string='Nivel 2 - Usuarios')
    level_3_user_ids = fields.Many2many('res.users', 'escalation_rule_level3_rel',
                                        'rule_id', 'user_id', string='Nivel 3 - Usuarios')

    # Acciones automáticas
    auto_actions = fields.Text('Acciones Automáticas (código Python)')

    @api.model
    def get_escalation_config(self, alert):
        """Obtiene configuración de escalación para una alerta específica"""
        rules = self.search([
            ('active', '=', True),
            '|', ('alert_type', '=', alert.alert_type), ('alert_type', '=', False),
            '|', ('severity', '=', alert.severity), ('severity', '=', False),
            '|', ('production_line', '=', alert.production_line), ('production_line', '=', 'all')
        ], order='sequence, id', limit=1)
        
        if rules:
            return {
                'escalation_time': rules.escalation_time,
                'max_escalations': rules.max_escalations,
                'level_1_users': rules.level_1_user_ids.ids,
                'level_2_users': rules.level_2_user_ids.ids,
                'level_3_users': rules.level_3_user_ids.ids,
                'auto_actions': rules.auto_actions
            }
        
        return None