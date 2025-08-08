# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import logging
import json

_logger = logging.getLogger(__name__)

class AlertAutomation(models.Model):
    _name = 'megastock.alert.automation'
    _description = 'Automatización de Alertas'
    _order = 'sequence, name'

    name = fields.Char('Nombre', required=True)
    sequence = fields.Integer('Secuencia', default=10)
    active = fields.Boolean('Activo', default=True)
    description = fields.Text('Descripción')

    # Configuración del trigger
    trigger_model = fields.Selection([
        ('megastock.production.kpi', 'KPIs de Producción'),
        ('mrp.production', 'Órdenes de Producción'),
        ('megastock.work.queue', 'Colas de Trabajo'),
        ('megastock.capacity.planning', 'Planificación de Capacidad'),
        ('mrp.workcenter', 'Centros de Trabajo'),
        ('megastock.production.schedule', 'Cronogramas')
    ], string='Modelo Trigger', required=True)

    trigger_condition = fields.Text('Condición del Trigger', required=True,
                                   help="Condición Python que debe evaluarse como True para disparar la alerta")
    
    # Configuración de la alerta
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
    ], string='Tipo de Alerta', required=True)

    alert_priority = fields.Selection([
        ('1', 'Baja'),
        ('2', 'Media'),
        ('3', 'Alta'),
        ('4', 'Crítica'),
        ('5', 'Emergencia')
    ], string='Prioridad', required=True, default='2')

    alert_severity = fields.Selection([
        ('info', 'Información'),
        ('warning', 'Advertencia'),
        ('error', 'Error'),
        ('critical', 'Crítico')
    ], string='Severidad', required=True, default='warning')

    # Plantillas de mensaje
    alert_title_template = fields.Char('Plantilla Título', required=True,
                                      help="Usar ${field_name} para valores dinámicos")
    alert_message_template = fields.Text('Plantilla Mensaje', required=True,
                                        help="Usar ${field_name} para valores dinámicos")

    # Configuración de repetición
    prevent_duplicates = fields.Boolean('Prevenir Duplicados', default=True)
    duplicate_window = fields.Integer('Ventana Anti-duplicados (minutos)', default=15)
    max_alerts_per_hour = fields.Integer('Máximo Alertas por Hora', default=5)

    # Acciones automáticas
    auto_escalate = fields.Boolean('Escalación Automática', default=True)
    escalation_time = fields.Integer('Tiempo para Escalación (minutos)', default=30)
    
    auto_action_code = fields.Text('Código de Acción Automática',
                                  help="Código Python a ejecutar cuando se dispara la alerta")

    # Filtros adicionales
    line_filter = fields.Selection([
        ('papel_periodico', 'Papel Periódico'),
        ('cajas', 'Cajas & Planchas'),
        ('lamina_micro', 'Lámina Micro'),
        ('all', 'Todas las Líneas')
    ], string='Filtro por Línea', default='all')

    # Horarios de activación
    only_working_hours = fields.Boolean('Solo Horario Laboral', default=False)
    working_hours_start = fields.Float('Hora Inicio', default=6.0)
    working_hours_end = fields.Float('Hora Fin', default=22.0)

    # Estadísticas
    trigger_count = fields.Integer('Veces Disparado', default=0, readonly=True)
    last_triggered = fields.Datetime('Último Disparo', readonly=True)
    alerts_created = fields.Integer('Alertas Creadas', default=0, readonly=True)

    @api.model
    def evaluate_triggers(self, model_name, record_ids=None):
        """Evalúa todos los triggers para un modelo específico"""
        if not record_ids:
            return
            
        # Buscar reglas activas para este modelo
        rules = self.search([
            ('active', '=', True),
            ('trigger_model', '=', model_name)
        ])
        
        for rule in rules:
            try:
                rule._evaluate_rule(record_ids)
            except Exception as e:
                _logger.error(f"Error evaluando regla {rule.name}: {str(e)}")

    def _evaluate_rule(self, record_ids):
        """Evalúa una regla específica contra registros dados"""
        self.ensure_one()
        
        # Verificar horario laboral si está configurado
        if self.only_working_hours and not self._is_working_hours():
            return
        
        # Verificar límite de alertas por hora
        if not self._check_hourly_limit():
            return
        
        # Obtener registros del modelo
        model = self.env[self.trigger_model]
        records = model.browse(record_ids)
        
        for record in records:
            try:
                # Evaluar condición
                if self._evaluate_condition(record):
                    # Verificar duplicados si está habilitado
                    if self.prevent_duplicates and self._check_duplicate(record):
                        continue
                    
                    # Crear alerta
                    self._create_alert(record)
                    
            except Exception as e:
                _logger.error(f"Error procesando registro {record.id} en regla {self.name}: {str(e)}")

    def _evaluate_condition(self, record):
        """Evalúa la condición del trigger contra un registro"""
        try:
            # Crear contexto local para la evaluación
            local_context = {
                'record': record,
                'env': self.env,
                'datetime': datetime,
                'timedelta': timedelta,
                'fields': fields,
            }
            
            # Evaluar condición
            result = eval(self.trigger_condition, {"__builtins__": {}}, local_context)
            return bool(result)
            
        except Exception as e:
            _logger.error(f"Error evaluando condición en regla {self.name}: {str(e)}")
            return False

    def _create_alert(self, record):
        """Crea una alerta basada en el registro que disparó la regla"""
        try:
            # Generar título y mensaje dinámico
            title = self._render_template(self.alert_title_template, record)
            message = self._render_template(self.alert_message_template, record)
            
            # Determinar línea de producción
            production_line = self._get_production_line(record)
            
            # Preparar datos adicionales
            additional_data = {
                'automation_rule_id': self.id,
                'trigger_record_model': record._name,
                'trigger_record_id': record.id,
                'evaluation_time': fields.Datetime.now().isoformat()
            }
            
            # Crear alerta
            alert_values = {
                'title': title,
                'message': message,
                'alert_type': self.alert_type,
                'priority': self.alert_priority,
                'severity': self.alert_severity,
                'production_line': production_line,
                'auto_escalate': self.auto_escalate,
                'escalation_time': self.escalation_time,
                'additional_data': json.dumps(additional_data),
                'source_model': record._name,
                'source_id': record.id
            }
            
            # Relacionar con registros específicos si es posible
            if hasattr(record, 'workcenter_id') and record.workcenter_id:
                alert_values['workcenter_id'] = record.workcenter_id.id
            
            if hasattr(record, 'production_id') and record.production_id:
                alert_values['production_id'] = record.production_id.id
            
            if record._name == 'megastock.production.kpi':
                alert_values['kpi_id'] = record.id
            
            alert = self.env['megastock.production.alert'].create_alert(
                alert_type=self.alert_type,
                title=title,
                message=message,
                **alert_values
            )
            
            # Ejecutar acción automática si está configurada
            if self.auto_action_code:
                self._execute_auto_action(record, alert)
            
            # Actualizar estadísticas
            self.write({
                'trigger_count': self.trigger_count + 1,
                'last_triggered': fields.Datetime.now(),
                'alerts_created': self.alerts_created + 1
            })
            
            return alert
            
        except Exception as e:
            _logger.error(f"Error creando alerta en regla {self.name}: {str(e)}")
            return None

    def _render_template(self, template, record):
        """Renderiza plantilla con valores dinámicos del registro"""
        try:
            # Reemplazar placeholders ${field_name} con valores del registro
            rendered = template
            
            # Buscar todos los placeholders
            import re
            placeholders = re.findall(r'\$\{([^}]+)\}', template)
            
            for placeholder in placeholders:
                try:
                    # Evaluar el placeholder en el contexto del registro
                    value = eval(f'record.{placeholder}', {"record": record})
                    rendered = rendered.replace(f'${{{placeholder}}}', str(value))
                except:
                    # Si no se puede evaluar, mantener el placeholder
                    pass
            
            return rendered
            
        except Exception as e:
            _logger.error(f"Error renderizando plantilla: {str(e)}")
            return template

    def _get_production_line(self, record):
        """Determina la línea de producción del registro"""
        if self.line_filter != 'all':
            return self.line_filter
        
        # Intentar determinar automáticamente
        if hasattr(record, 'production_line'):
            return record.production_line
        
        if hasattr(record, 'workcenter_id') and record.workcenter_id:
            # Lógica para determinar línea basada en centro de trabajo
            workcenter_name = record.workcenter_id.name.lower()
            if 'papel' in workcenter_name or 'periodico' in workcenter_name:
                return 'papel_periodico'
            elif 'caja' in workcenter_name or 'plancha' in workcenter_name:
                return 'cajas'
            elif 'micro' in workcenter_name or 'lamina' in workcenter_name:
                return 'lamina_micro'
        
        return 'all'

    def _check_duplicate(self, record):
        """Verifica si ya existe una alerta similar reciente"""
        if not self.prevent_duplicates:
            return False
        
        cutoff_time = fields.Datetime.now() - timedelta(minutes=self.duplicate_window)
        
        existing_alert = self.env['megastock.production.alert'].search([
            ('alert_type', '=', self.alert_type),
            ('source_model', '=', record._name),
            ('source_id', '=', record.id),
            ('detection_date', '>=', cutoff_time),
            ('state', 'in', ['active', 'acknowledged'])
        ], limit=1)
        
        return bool(existing_alert)

    def _check_hourly_limit(self):
        """Verifica el límite de alertas por hora"""
        if self.max_alerts_per_hour <= 0:
            return True
        
        hour_ago = fields.Datetime.now() - timedelta(hours=1)
        
        recent_alerts = self.env['megastock.production.alert'].search_count([
            ('create_date', '>=', hour_ago),
            ('additional_data', 'like', f'"automation_rule_id": {self.id}')
        ])
        
        return recent_alerts < self.max_alerts_per_hour

    def _is_working_hours(self):
        """Verifica si está en horario laboral"""
        if not self.only_working_hours:
            return True
        
        current_time = datetime.now()
        current_hour = current_time.hour + current_time.minute / 60.0
        
        return self.working_hours_start <= current_hour <= self.working_hours_end

    def _execute_auto_action(self, record, alert):
        """Ejecuta acción automática configurada"""
        try:
            if not self.auto_action_code:
                return
            
            local_context = {
                'record': record,
                'alert': alert,
                'env': self.env,
                'datetime': datetime,
                'timedelta': timedelta,
                '_logger': _logger
            }
            
            exec(self.auto_action_code, {"__builtins__": {}}, local_context)
            
        except Exception as e:
            _logger.error(f"Error ejecutando acción automática en regla {self.name}: {str(e)}")

    @api.model
    def create_default_rules(self):
        """Crea reglas de automatización por defecto para MEGASTOCK"""
        default_rules = [
            {
                'name': 'OEE Crítico - Debajo del 70%',
                'trigger_model': 'megastock.production.kpi',
                'trigger_condition': "record.kpi_type == 'oee' and record.value < 70",
                'alert_type': 'kpi',
                'alert_priority': '4',
                'alert_severity': 'critical',
                'alert_title_template': 'OEE Crítico: ${value}% en ${workcenter_id.name}',
                'alert_message_template': 'El OEE ha caído a ${value}% en ${workcenter_id.name}, por debajo del umbral crítico de 70%. Revisar disponibilidad, performance y calidad.',
                'sequence': 10
            },
            {
                'name': 'Cola de Trabajo Saturada',
                'trigger_model': 'megastock.work.queue',
                'trigger_condition': "record.current_items_count > 100",
                'alert_type': 'capacity',
                'alert_priority': '3',
                'alert_severity': 'warning',
                'alert_title_template': 'Cola Saturada: ${name}',
                'alert_message_template': 'La cola ${name} tiene ${current_items_count} items pendientes, excediendo el límite recomendado.',
                'sequence': 20
            },
            {
                'name': 'Producción Retrasada',
                'trigger_model': 'mrp.production',
                'trigger_condition': "record.date_planned_start < datetime.now() and record.state not in ['done', 'cancel']",
                'alert_type': 'schedule',
                'alert_priority': '3',
                'alert_severity': 'warning',
                'alert_title_template': 'Producción Retrasada: ${name}',
                'alert_message_template': 'La orden de producción ${name} programada para ${date_planned_start} está retrasada.',
                'sequence': 30
            },
            {
                'name': 'Calidad Baja - Debajo del 95%',
                'trigger_model': 'megastock.production.kpi',
                'trigger_condition': "record.kpi_type == 'quality' and record.value < 95",
                'alert_type': 'quality',
                'alert_priority': '4',
                'alert_severity': 'error',
                'alert_title_template': 'Calidad Baja: ${value}% en ${workcenter_id.name}',
                'alert_message_template': 'La calidad ha bajado a ${value}% en ${workcenter_id.name}. Revisar procesos y materiales.',
                'sequence': 40
            },
            {
                'name': 'Utilización Capacidad Alta',
                'trigger_model': 'megastock.capacity.planning',
                'trigger_condition': "record.utilization_rate > 95",
                'alert_type': 'capacity',
                'alert_priority': '3',
                'alert_severity': 'warning',
                'alert_title_template': 'Capacidad al Límite: ${utilization_rate}%',
                'alert_message_template': 'La utilización de capacidad está al ${utilization_rate}%, cerca del límite máximo.',
                'sequence': 50
            }
        ]
        
        for rule_data in default_rules:
            existing = self.search([('name', '=', rule_data['name'])], limit=1)
            if not existing:
                self.create(rule_data)
        
        return True


class AlertNotificationChannel(models.Model):
    _name = 'megastock.alert.notification.channel'
    _description = 'Canales de Notificación de Alertas'

    name = fields.Char('Nombre', required=True)
    active = fields.Boolean('Activo', default=True)
    channel_type = fields.Selection([
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Notificación Push'),
        ('webhook', 'Webhook'),
        ('internal', 'Mensaje Interno Odoo')
    ], string='Tipo de Canal', required=True)

    # Configuración por tipo
    email_template_id = fields.Many2one('mail.template', 'Plantilla Email')
    webhook_url = fields.Char('URL Webhook')
    webhook_headers = fields.Text('Headers HTTP (JSON)')
    
    # Filtros de activación
    alert_types = fields.Selection([
        ('all', 'Todos los Tipos'),
        ('specific', 'Tipos Específicos')
    ], string='Tipos de Alerta', default='all')
    
    specific_alert_types = fields.Many2many('megastock.production.alert', 
                                           string='Tipos Específicos')
    
    min_priority = fields.Selection([
        ('1', 'Baja'),
        ('2', 'Media'),
        ('3', 'Alta'),
        ('4', 'Crítica'),
        ('5', 'Emergencia')
    ], string='Prioridad Mínima', default='2')

    # Usuarios destinatarios
    user_ids = fields.Many2many('res.users', string='Usuarios')
    
    def send_notification(self, alert):
        """Envía notificación por el canal configurado"""
        self.ensure_one()
        
        if not self.active:
            return False
        
        # Verificar filtros
        if not self._should_notify(alert):
            return False
        
        try:
            if self.channel_type == 'email':
                return self._send_email(alert)
            elif self.channel_type == 'sms':
                return self._send_sms(alert)
            elif self.channel_type == 'webhook':
                return self._send_webhook(alert)
            elif self.channel_type == 'internal':
                return self._send_internal(alert)
            
        except Exception as e:
            _logger.error(f"Error enviando notificación por canal {self.name}: {str(e)}")
            return False
        
        return True

    def _should_notify(self, alert):
        """Verifica si debe notificar para esta alerta"""
        # Verificar prioridad mínima
        if int(alert.priority) < int(self.min_priority):
            return False
        
        # Verificar tipos específicos si está configurado
        if self.alert_types == 'specific':
            if alert.alert_type not in self.specific_alert_types.mapped('alert_type'):
                return False
        
        return True

    def _send_email(self, alert):
        """Envía notificación por email"""
        if not self.email_template_id or not self.user_ids:
            return False
        
        for user in self.user_ids:
            if user.email:
                self.email_template_id.send_mail(
                    alert.id, 
                    email_to=user.email,
                    force_send=True
                )
        return True

    def _send_internal(self, alert):
        """Envía mensaje interno de Odoo"""
        for user in self.user_ids:
            self.env['mail.message'].create({
                'subject': f'Alerta: {alert.title}',
                'body': alert.message,
                'message_type': 'notification',
                'author_id': self.env.user.partner_id.id,
                'partner_ids': [(4, user.partner_id.id)]
            })
        return True

    def _send_webhook(self, alert):
        """Envía notificación por webhook"""
        if not self.webhook_url:
            return False
        
        import requests
        import json
        
        payload = {
            'alert_id': alert.id,
            'title': alert.title,
            'message': alert.message,
            'type': alert.alert_type,
            'priority': alert.priority,
            'severity': alert.severity,
            'detection_date': alert.detection_date.isoformat() if alert.detection_date else None,
            'production_line': alert.production_line
        }
        
        headers = {'Content-Type': 'application/json'}
        if self.webhook_headers:
            try:
                additional_headers = json.loads(self.webhook_headers)
                headers.update(additional_headers)
            except:
                pass
        
        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            return response.status_code == 200
        except:
            return False

    def _send_sms(self, alert):
        """Envía notificación por SMS (placeholder para integración futura)"""
        # Implementar integración con proveedor SMS
        _logger.info(f"SMS notification placeholder for alert {alert.id}")
        return True