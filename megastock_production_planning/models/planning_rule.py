# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class PlanningRule(models.Model):
    _name = 'megastock.planning.rule'
    _description = 'Reglas de Planificación de Producción'  
    _order = 'sequence, priority desc'
    
    name = fields.Char(
        string='Nombre de la Regla',
        required=True,
        help='Nombre descriptivo de la regla'
    )
    
    code = fields.Char(
        string='Código',
        required=True,
        help='Código único de identificación'
    )
    
    sequence = fields.Integer(
        string='Secuencia',
        default=10,
        help='Orden de aplicación de las reglas'
    )
    
    active = fields.Boolean(
        string='Activo',
        default=True
    )
    
    # === TIPO Y CATEGORÍA ===
    rule_type = fields.Selection([
        ('priority', 'Regla de Prioridad'),
        ('sequencing', 'Regla de Secuenciación'),
        ('capacity', 'Regla de Capacidad'),
        ('material', 'Regla de Materiales'),
        ('setup', 'Regla de Setup'),
        ('quality', 'Regla de Calidad'),
        ('cost', 'Regla de Optimización de Costos')
    ], string='Tipo de Regla', required=True)
    
    priority = fields.Selection([
        ('low', 'Baja'),
        ('medium', 'Media'), 
        ('high', 'Alta'),
        ('critical', 'Crítica')
    ], string='Prioridad', default='medium', required=True)
    
    # === APLICABILIDAD ===
    production_line_ids = fields.Many2many(
        'mrp.workcenter',
        'planning_rule_workcenter_rel',
        'rule_id',
        'workcenter_id',
        string='Líneas de Producción',
        help='Líneas donde aplica esta regla'
    )
    
    product_category_ids = fields.Many2many(
        'product.category',
        'planning_rule_category_rel',
        'rule_id',
        'category_id',
        string='Categorías de Productos',
        help='Categorías de productos afectadas'
    )
    
    customer_ids = fields.Many2many(
        'res.partner',
        'planning_rule_customer_rel',
        'rule_id',
        'customer_id',
        string='Clientes Específicos',
        help='Clientes a los que aplica la regla'
    )
    
    # === CONDICIONES ===
    condition_field = fields.Selection([
        ('quantity', 'Cantidad del Pedido'),
        ('due_date', 'Fecha de Entrega'),
        ('customer_priority', 'Prioridad del Cliente'),
        ('product_type', 'Tipo de Producto'),
        ('stock_level', 'Nivel de Stock'),
        ('setup_time', 'Tiempo de Setup'),
        ('material_availability', 'Disponibilidad Material'),
        ('workcenter_load', 'Carga Centro Trabajo'),
        ('always', 'Siempre')
    ], string='Campo Condición', default='always')
    
    condition_operator = fields.Selection([
        ('=', 'Igual a'),
        ('!=', 'Diferente de'),
        ('>', 'Mayor que'),
        ('>=', 'Mayor o igual'),
        ('<', 'Menor que'),
        ('<=', 'Menor o igual'),
        ('in', 'Dentro de'),
        ('not_in', 'No está en')
    ], string='Operador')
    
    condition_value = fields.Char(
        string='Valor de Condición',
        help='Valor para evaluar la condición'
    )
    
    # === ACCIONES ===
    action_type = fields.Selection([
        ('set_priority', 'Establecer Prioridad'),
        ('assign_workcenter', 'Asignar Centro de Trabajo'),
        ('adjust_quantity', 'Ajustar Cantidad'),
        ('set_schedule', 'Establecer Programa'),
        ('require_approval', 'Requiere Aprobación'),
        ('block_production', 'Bloquear Producción'),
        ('send_alert', 'Enviar Alerta'),
        ('optimize_sequence', 'Optimizar Secuencia')
    ], string='Tipo de Acción', required=True)
    
    action_value = fields.Char(
        string='Valor de Acción',
        help='Valor o parámetro para la acción'
    )
    
    # === CONFIGURACIÓN ESPECÍFICA ===
    
    # Para reglas de prioridad
    priority_boost = fields.Float(
        string='Incremento de Prioridad',
        default=0.0,
        help='Cantidad a incrementar la prioridad'
    )
    
    # Para reglas de secuenciación
    sequence_method = fields.Selection([
        ('fifo', 'Primero en Entrar, Primero en Salir'),
        ('lifo', 'Último en Entrar, Primero en Salir'),
        ('spt', 'Tiempo de Procesamiento Más Corto'),
        ('edd', 'Fecha de Entrega Más Próxima'),
        ('cr', 'Ratio Crítico'),
        ('custom', 'Personalizado')
    ], string='Método de Secuenciación')
    
    # Para reglas de setup
    setup_time_minutes = fields.Float(
        string='Tiempo de Setup (min)',
        default=0.0,
        help='Tiempo adicional de setup en minutos'
    )
    
    setup_cost = fields.Float(
        string='Costo de Setup',
        default=0.0,
        help='Costo adicional por setup'
    )
    
    # Para reglas de capacidad
    capacity_multiplier = fields.Float(
        string='Multiplicador de Capacidad',
        default=1.0,
        help='Factor para ajustar capacidad disponible'
    )
    
    # === CONFIGURACIÓN TEMPORAL ===
    date_from = fields.Date(
        string='Válido Desde',
        help='Fecha desde cuando es válida la regla'
    )
    
    date_to = fields.Date(
        string='Válido Hasta',
        help='Fecha hasta cuando es válida la regla'
    )
    
    time_from = fields.Float(
        string='Hora Desde',
        help='Hora del día desde cuando aplica (0-23.99)'
    )
    
    time_to = fields.Float(
        string='Hora Hasta',
        help='Hora del día hasta cuando aplica (0-23.99)'
    )
    
    weekdays = fields.Selection([
        ('all', 'Todos los días'),
        ('weekdays', 'Solo días laborales'),
        ('weekends', 'Solo fines de semana'),
        ('custom', 'Días específicos')
    ], string='Días de la Semana', default='all')
    
    custom_weekdays = fields.Char(
        string='Días Específicos',
        help='Días separados por coma (1=Lunes, 7=Domingo)'
    )
    
    # === ESTADÍSTICAS ===
    application_count = fields.Integer(
        string='Veces Aplicada',
        default=0,
        readonly=True
    )
    
    last_application_date = fields.Datetime(
        string='Última Aplicación',
        readonly=True
    )
    
    success_count = fields.Integer(
        string='Aplicaciones Exitosas',
        default=0,
        readonly=True
    )
    
    success_rate = fields.Float(
        string='Tasa de Éxito (%)',
        compute='_compute_success_rate',
        store=True
    )
    
    description = fields.Text(
        string='Descripción',
        help='Descripción detallada de la regla y su propósito'
    )
    
    # === MÉTODOS COMPUTADOS ===
    
    @api.depends('application_count', 'success_count')
    def _compute_success_rate(self):
        """Calcular tasa de éxito"""
        for rule in self:
            if rule.application_count > 0:
                rule.success_rate = (rule.success_count / rule.application_count) * 100
            else:
                rule.success_rate = 0.0
    
    # === VALIDACIONES ===
    
    @api.constrains('code')
    def _check_unique_code(self):
        """Verificar que el código sea único"""
        for rule in self:
            if self.search_count([('code', '=', rule.code), ('id', '!=', rule.id)]) > 0:
                raise ValidationError(f"Ya existe una regla con código '{rule.code}'")
    
    @api.constrains('time_from', 'time_to')
    def _check_time_range(self):
        """Validar rango de horas"""
        for rule in self:
            if rule.time_from < 0 or rule.time_from > 23.99:
                raise ValidationError("La hora desde debe estar entre 0 y 23.99")
            if rule.time_to < 0 or rule.time_to > 23.99:
                raise ValidationError("La hora hasta debe estar entre 0 y 23.99")
    
    @api.constrains('date_from', 'date_to')
    def _check_date_range(self):
        """Validar rango de fechas"""
        for rule in self:
            if rule.date_from and rule.date_to and rule.date_from > rule.date_to:
                raise ValidationError("La fecha desde no puede ser posterior a la fecha hasta")
    
    # === MÉTODOS DE APLICACIÓN ===
    
    def check_applicability(self, context):
        """Verificar si la regla es aplicable en el contexto dado"""
        self.ensure_one()
        
        # Verificar si la regla está activa
        if not self.active:
            return False
        
        # Verificar validez temporal
        if not self._check_time_validity():
            return False
        
        # Verificar aplicabilidad por línea de producción
        if self.production_line_ids and context.get('workcenter_id'):
            if context['workcenter_id'] not in self.production_line_ids.ids:
                return False
        
        # Verificar aplicabilidad por categoría de producto
        if self.product_category_ids and context.get('product_id'):
            product = self.env['product.product'].browse(context['product_id'])
            if product.categ_id.id not in self.product_category_ids.ids:
                return False
        
        # Verificar aplicabilidad por cliente
        if self.customer_ids and context.get('customer_id'):
            if context['customer_id'] not in self.customer_ids.ids:
                return False
        
        # Verificar condición específica
        if not self._evaluate_condition(context):
            return False
        
        return True
    
    def _check_time_validity(self):
        """Verificar validez temporal de la regla"""
        now = fields.Datetime.now()
        today = now.date()
        current_time = now.hour + now.minute / 60.0
        current_weekday = now.weekday() + 1  # 1=Lunes, 7=Domingo
        
        # Verificar rango de fechas
        if self.date_from and today < self.date_from:
            return False
        if self.date_to and today > self.date_to:
            return False
        
        # Verificar rango de horas
        if self.time_from and current_time < self.time_from:
            return False
        if self.time_to and current_time > self.time_to:
            return False
        
        # Verificar días de la semana
        if self.weekdays == 'weekdays' and current_weekday > 5:  # Sábado y domingo
            return False
        elif self.weekdays == 'weekends' and current_weekday <= 5:
            return False
        elif self.weekdays == 'custom' and self.custom_weekdays:
            allowed_days = [int(d.strip()) for d in self.custom_weekdays.split(',')]
            if current_weekday not in allowed_days:
                return False
        
        return True
    
    def _evaluate_condition(self, context):
        """Evaluar condición de la regla"""
        if self.condition_field == 'always':
            return True
        
        # Obtener valor del contexto
        field_value = context.get(self.condition_field)
        condition_value = self._convert_condition_value()
        
        if field_value is None:
            return False
        
        # Evaluar operador
        try:
            if self.condition_operator == '=':
                return field_value == condition_value
            elif self.condition_operator == '!=':
                return field_value != condition_value
            elif self.condition_operator == '>':
                return field_value > condition_value
            elif self.condition_operator == '>=':
                return field_value >= condition_value
            elif self.condition_operator == '<':
                return field_value < condition_value
            elif self.condition_operator == '<=':
                return field_value <= condition_value
            elif self.condition_operator == 'in':
                return field_value in condition_value
            elif self.condition_operator == 'not_in':
                return field_value not in condition_value
        except (TypeError, ValueError):
            _logger.warning(f"Error evaluando condición en regla {self.code}: {field_value} {self.condition_operator} {condition_value}")
            return False
        
        return False
    
    def _convert_condition_value(self):
        """Convertir valor de condición al tipo apropiado"""
        if not self.condition_value:
            return None
        
        try:
            # Intentar convertir a número
            if '.' in self.condition_value:
                return float(self.condition_value)
            else:
                return int(self.condition_value)
        except ValueError:
            # Si no es número, dejarlo como string o lista
            if ',' in self.condition_value:
                return [v.strip() for v in self.condition_value.split(',')]
            else:
                return self.condition_value
    
    def apply_rule(self, context):
        """Aplicar la regla en el contexto dado"""
        self.ensure_one()
        
        if not self.check_applicability(context):
            return {'applied': False, 'reason': 'Rule not applicable'}
        
        try:
            result = self._execute_action(context)
            
            # Registrar aplicación exitosa
            self.application_count += 1
            if result.get('success', True):
                self.success_count += 1
            self.last_application_date = fields.Datetime.now()
            
            _logger.info(f"Regla {self.code} aplicada exitosamente: {result}")
            
            return {
                'applied': True,
                'result': result,
                'rule_code': self.code,
                'rule_name': self.name
            }
            
        except Exception as e:
            # Registrar aplicación fallida
            self.application_count += 1
            self.last_application_date = fields.Datetime.now()
            
            _logger.error(f"Error aplicando regla {self.code}: {str(e)}")
            
            return {
                'applied': False,
                'error': str(e),
                'rule_code': self.code
            }
    
    def _execute_action(self, context):
        """Ejecutar la acción de la regla"""
        if self.action_type == 'set_priority':
            return self._action_set_priority(context)
        elif self.action_type == 'assign_workcenter':
            return self._action_assign_workcenter(context)
        elif self.action_type == 'adjust_quantity':
            return self._action_adjust_quantity(context)
        elif self.action_type == 'set_schedule':
            return self._action_set_schedule(context)
        elif self.action_type == 'require_approval':
            return self._action_require_approval(context)
        elif self.action_type == 'block_production':
            return self._action_block_production(context)
        elif self.action_type == 'send_alert':
            return self._action_send_alert(context)
        elif self.action_type == 'optimize_sequence':
            return self._action_optimize_sequence(context)
        else:
            return {'success': False, 'message': f'Acción no implementada: {self.action_type}'}
    
    def _action_set_priority(self, context):
        """Acción: Establecer prioridad"""
        if 'plan_line' in context:
            plan_line = context['plan_line']
            original_priority = plan_line.priority_score
            plan_line.priority_score += self.priority_boost
            
            return {
                'success': True,
                'message': f'Prioridad ajustada de {original_priority} a {plan_line.priority_score}',
                'priority_change': self.priority_boost
            }
        
        return {'success': False, 'message': 'No se encontró línea del plan en el contexto'}
    
    def _action_assign_workcenter(self, context):
        """Acción: Asignar centro de trabajo"""
        if 'plan_line' in context and self.action_value:
            workcenter = self.env['mrp.workcenter'].search([
                ('name', '=', self.action_value)
            ], limit=1)
            
            if workcenter:
                plan_line = context['plan_line']
                plan_line.workcenter_id = workcenter.id
                
                return {
                    'success': True,
                    'message': f'Asignado centro de trabajo: {workcenter.name}',
                    'workcenter_id': workcenter.id
                }
        
        return {'success': False, 'message': 'No se pudo asignar centro de trabajo'}
    
    def _action_adjust_quantity(self, context):
        """Acción: Ajustar cantidad"""
        if 'plan_line' in context and self.action_value:
            plan_line = context['plan_line']
            original_qty = plan_line.planned_quantity
            
            try:
                if self.action_value.startswith('*'):
                    # Multiplicador
                    multiplier = float(self.action_value[1:])
                    plan_line.planned_quantity *= multiplier
                elif self.action_value.startswith('+'):
                    # Suma
                    addition = float(self.action_value[1:])
                    plan_line.planned_quantity += addition
                elif self.action_value.startswith('-'):
                    # Resta
                    subtraction = float(self.action_value[1:])
                    plan_line.planned_quantity = max(0, plan_line.planned_quantity - subtraction)
                else:
                    # Valor absoluto
                    plan_line.planned_quantity = float(self.action_value)
                
                return {
                    'success': True,
                    'message': f'Cantidad ajustada de {original_qty} a {plan_line.planned_quantity}',
                    'quantity_change': plan_line.planned_quantity - original_qty
                }
                
            except ValueError:
                return {'success': False, 'message': f'Valor de ajuste inválido: {self.action_value}'}
        
        return {'success': False, 'message': 'No se pudo ajustar cantidad'}
    
    def _action_set_schedule(self, context):
        """Acción: Establecer programa"""
        # Implementar lógica de programación específica
        return {'success': True, 'message': 'Programa establecido'}
    
    def _action_require_approval(self, context):
        """Acción: Requiere aprobación"""
        if 'plan_line' in context:
            # Marcar línea como requiere aprobación
            # En implementación completa, esto crearía una actividad o notificación
            return {'success': True, 'message': 'Marcado para aprobación'}
        
        return {'success': False, 'message': 'No se pudo marcar para aprobación'}
    
    def _action_block_production(self, context):
        """Acción: Bloquear producción"""
        if 'plan_line' in context:
            plan_line = context['plan_line']
            plan_line.state = 'cancelled'
            plan_line.notes = f"Bloqueado por regla: {self.name}"
            
            return {'success': True, 'message': 'Producción bloqueada'}
        
        return {'success': False, 'message': 'No se pudo bloquear producción'}
    
    def _action_send_alert(self, context):
        """Acción: Enviar alerta"""
        # Crear actividad o notificación
        if 'plan_line' in context:
            plan_line = context['plan_line']
            plan_line.plan_id.message_post(
                body=f"Alerta de regla {self.name}: {self.action_value or 'Revisión requerida'}",
                subject=f"Alerta de Planificación - {self.name}"
            )
            
            return {'success': True, 'message': 'Alerta enviada'}
        
        return {'success': False, 'message': 'No se pudo enviar alerta'}
    
    def _action_optimize_sequence(self, context):
        """Acción: Optimizar secuencia"""
        # Implementar algoritmo de optimización de secuencia
        return {'success': True, 'message': 'Secuencia optimizada'}
    
    # === MÉTODOS DE UTILIDAD ===
    
    @api.model
    def apply_rules_to_plan(self, plan):
        """Aplicar todas las reglas aplicables a un plan"""
        applicable_rules = self.search([('active', '=', True)], order='sequence, id')
        
        results = []
        
        for line in plan.plan_line_ids:
            context = {
                'plan_line': line,
                'product_id': line.product_id.id,
                'quantity': line.planned_quantity,
                'workcenter_id': line.workcenter_id.id if line.workcenter_id else None,
                'customer_id': None,  # Se podría obtener de la orden de venta
                'due_date': line.suggested_end_date,
                'stock_level': line.product_id.qty_available,
            }
            
            line_results = []
            for rule in applicable_rules:
                result = rule.apply_rule(context)
                if result['applied']:
                    line_results.append(result)
            
            if line_results:
                results.append({
                    'line_id': line.id,
                    'product_name': line.product_id.name,
                    'rules_applied': line_results
                })
        
        return results
    
    def duplicate_rule(self):
        """Duplicar regla con nuevo código"""
        self.ensure_one()
        
        new_code = f"{self.code}_COPY"
        counter = 1
        while self.search([('code', '=', new_code)]):
            new_code = f"{self.code}_COPY_{counter}"
            counter += 1
        
        return self.copy({
            'name': f"{self.name} (Copia)",
            'code': new_code,
            'active': False  # Desactivar copia para revisión
        })
    
    def action_test_rule(self):
        """Probar regla con datos de ejemplo"""
        test_context = {
            'product_id': 1,
            'quantity': 1000,
            'workcenter_id': 1,
            'customer_id': 1,
            'due_date': fields.Datetime.now() + timedelta(days=7),
            'stock_level': 500,
        }
        
        result = self.apply_rule(test_context)
        
        message_type = 'success' if result['applied'] else 'warning'
        message = f"Resultado del test:\n{result}"
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Test de Regla',
                'message': message,
                'type': message_type,
                'sticky': True,
            }
        }