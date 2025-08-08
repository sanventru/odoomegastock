# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class MaterialSubstitutionRule(models.Model):
    _name = 'megastock.material.substitution.rule'
    _description = 'Reglas de Sustitución Inteligente de Materiales'
    _order = 'priority desc, sequence'
    
    name = fields.Char(
        string='Nombre',
        required=True,
        help='Nombre descriptivo de la regla de sustitución'
    )
    
    code = fields.Char(
        string='Código',
        required=True,
        help='Código único para identificar la regla'
    )
    
    sequence = fields.Integer(
        string='Secuencia',
        default=10,
        help='Orden de evaluación de las reglas'
    )
    
    active = fields.Boolean(
        string='Activo',
        default=True
    )
    
    priority = fields.Selection([
        ('low', 'Baja'),
        ('medium', 'Media'),
        ('high', 'Alta'),
        ('critical', 'Crítica')
    ], string='Prioridad', default='medium', required=True)
    
    # Material principal
    primary_material_id = fields.Many2one(
        'product.product',
        string='Material Principal',
        required=True,
        help='Material que puede ser sustituido'
    )
    
    # Tipo de sustitución
    substitution_type = fields.Selection([
        ('availability', 'Por Disponibilidad'),
        ('cost_optimization', 'Por Optimización de Costos'),
        ('quality_requirement', 'Por Requerimiento de Calidad'),
        ('expiry_approaching', 'Por Proximidad a Vencimiento'),
        ('supplier_issue', 'Por Problema de Proveedor'),
        ('seasonal', 'Por Temporalidad'),
        ('manual', 'Manual')
    ], string='Tipo de Sustitución', required=True)
    
    # Condiciones de activación
    trigger_condition = fields.Selection([
        ('stock_below_minimum', 'Stock Bajo Mínimo'),
        ('stock_unavailable', 'Stock No Disponible'),
        ('cost_variance_above', 'Variación Costo Mayor a'),
        ('expiry_approaching', 'Próximo a Vencer'),
        ('product_specification', 'Especificación Producto'),
        ('supplier_unavailable', 'Proveedor No Disponible'),
        ('always', 'Siempre')
    ], string='Condición de Activación', required=True)
    
    # Parámetros de activación
    min_stock_days = fields.Integer(
        string='Días Mínimos Stock',
        default=7,
        help='Días mínimos de stock para activar sustitución'
    )
    
    cost_variance_threshold = fields.Float(
        string='Umbral Variación Costo (%)',
        default=10.0,
        help='Porcentaje de variación de costo para activar sustitución'
    )
    
    expiry_days_threshold = fields.Integer(
        string='Días Vencimiento',
        default=30,
        help='Días antes del vencimiento para activar sustitución'
    )
    
    # Líneas de sustitución
    substitution_line_ids = fields.One2many(
        'megastock.material.substitution.line',
        'substitution_rule_id',
        string='Materiales Sustitutos',
        help='Lista ordenada de materiales sustitutos'
    )
    
    # Configuración de aprobación
    requires_approval = fields.Boolean(
        string='Requiere Aprobación',
        default=False,
        help='Requiere aprobación manual antes de aplicar sustitución'
    )
    
    approver_ids = fields.Many2many(
        'res.users',
        'substitution_approver_rel',
        'rule_id',
        'user_id',
        string='Aprobadores',
        help='Usuarios que pueden aprobar esta sustitución'
    )
    
    # Restricciones
    max_cost_increase = fields.Float(
        string='Máximo Incremento Costo (%)',
        default=15.0,
        help='Máximo incremento de costo permitido'
    )
    
    max_quality_decrease = fields.Float(
        string='Máxima Reducción Calidad (%)',
        default=5.0,
        help='Máxima reducción de calidad permitida'
    )
    
    # Configuración temporal
    valid_from_date = fields.Date(
        string='Válido Desde',
        help='Fecha desde la cual es válida la regla'
    )
    
    valid_to_date = fields.Date(
        string='Válido Hasta',
        help='Fecha hasta la cual es válida la regla'
    )
    
    # Estadísticas
    application_count = fields.Integer(
        string='Veces Aplicada',
        default=0,
        readonly=True
    )
    
    last_application_date = fields.Datetime(
        string='Última Aplicación',
        readonly=True
    )
    
    success_rate = fields.Float(
        string='Tasa de Éxito (%)',
        compute='_compute_success_rate',
        store=True,
        help='Porcentaje de aplicaciones exitosas'
    )
    
    # Historial de aplicaciones
    application_history_ids = fields.One2many(
        'megastock.substitution.application',
        'rule_id',
        string='Historial de Aplicaciones'
    )
    
    description = fields.Text(
        string='Descripción',
        help='Descripción detallada de la regla y criterios'
    )
    
    @api.depends('application_history_ids', 'application_history_ids.success')
    def _compute_success_rate(self):
        """Calcular tasa de éxito de la regla"""
        for rule in self:
            applications = rule.application_history_ids
            if applications:
                successful = applications.filtered('success')
                rule.success_rate = (len(successful) / len(applications)) * 100
            else:
                rule.success_rate = 0.0
    
    def check_trigger_condition(self, context=None):
        """Verificar si se cumple la condición para activar la regla"""
        self.ensure_one()
        
        if not context:
            context = {}
        
        current_date = datetime.now()
        
        # Verificar validez temporal
        if self.valid_from_date and current_date.date() < self.valid_from_date:
            return False
        if self.valid_to_date and current_date.date() > self.valid_to_date:
            return False
        
        if self.trigger_condition == 'stock_below_minimum':
            return self._check_stock_condition()
            
        elif self.trigger_condition == 'stock_unavailable':
            return self.primary_material_id.qty_available <= 0
            
        elif self.trigger_condition == 'cost_variance_above':
            return self._check_cost_variance()
            
        elif self.trigger_condition == 'expiry_approaching':
            return self._check_expiry_condition()
            
        elif self.trigger_condition == 'product_specification':
            return self._check_product_specification(context.get('product_tmpl_id'))
            
        elif self.trigger_condition == 'supplier_unavailable':
            return self._check_supplier_availability()
            
        elif self.trigger_condition == 'always':
            return True
        
        return False
    
    def _check_stock_condition(self):
        """Verificar condición de stock bajo"""
        material = self.primary_material_id
        
        # Calcular consumo diario promedio
        daily_consumption = self._calculate_daily_consumption(material)
        
        if daily_consumption > 0:
            days_of_stock = material.qty_available / daily_consumption
            return days_of_stock < self.min_stock_days
        
        return material.qty_available <= 0
    
    def _check_cost_variance(self):
        """Verificar variación de costo"""
        material = self.primary_material_id
        
        # Obtener precio histórico (simplificado - podría usar más lógica)
        historical_price = material.standard_price
        current_price = material.list_price or material.standard_price
        
        if historical_price > 0:
            variance = abs((current_price - historical_price) / historical_price * 100)
            return variance > self.cost_variance_threshold
        
        return False
    
    def _check_expiry_condition(self):
        """Verificar proximidad a vencimiento"""
        material = self.primary_material_id
        
        # Buscar lotes próximos a vencer
        expiry_threshold = datetime.now() + timedelta(days=self.expiry_days_threshold)
        
        expiring_lots = self.env['stock.production.lot'].search([
            ('product_id', '=', material.id),
            ('expiration_date', '<=', expiry_threshold),
            ('expiration_date', '>=', datetime.now())
        ])
        
        return bool(expiring_lots)
    
    def _check_product_specification(self, product_tmpl_id):
        """Verificar especificaciones del producto"""
        if not product_tmpl_id:
            return False
        
        product_tmpl = self.env['product.template'].browse(product_tmpl_id)
        
        # Lógica específica por tipo de producto
        if 'microcorrugado' in product_tmpl.categ_id.name.lower():
            # Para microcorrugado, preferir adhesivo PVA
            return 'adhesivo_pva' in self.substitution_line_ids.mapped('substitute_material_id.default_code')
        
        return False
    
    def _check_supplier_availability(self):
        """Verificar disponibilidad del proveedor"""
        material = self.primary_material_id
        
        # Verificar si el proveedor principal está activo
        main_supplier = material.seller_ids.filtered('is_company')[:1]
        if main_supplier:
            return not main_supplier.active
        
        return False
    
    def _calculate_daily_consumption(self, material):
        """Calcular consumo diario promedio del material"""
        # Buscar movimientos de stock de los últimos 30 días
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        stock_moves = self.env['stock.move'].search([
            ('product_id', '=', material.id),
            ('state', '=', 'done'),
            ('date', '>=', thirty_days_ago),
            ('location_id.usage', '=', 'internal'),
            ('location_dest_id.usage', '!=', 'internal')
        ])
        
        total_consumed = sum(stock_moves.mapped('product_uom_qty'))
        return total_consumed / 30 if total_consumed > 0 else 0
    
    def get_best_substitute(self, quantity_needed=0, context=None):
        """Obtener el mejor material sustituto disponible"""
        self.ensure_one()
        
        if not context:
            context = {}
        
        available_substitutes = []
        
        for line in self.substitution_line_ids.sorted('sequence'):
            substitute = line.substitute_material_id
            
            # Verificar disponibilidad
            available_qty = substitute.qty_available
            if available_qty <= 0:
                continue
            
            # Calcular cantidad ajustada
            adjusted_qty = quantity_needed * line.conversion_factor if quantity_needed else 0
            
            # Verificar si hay suficiente cantidad
            if adjusted_qty > 0 and available_qty < adjusted_qty:
                continue
            
            # Verificar restricciones de costo y calidad
            if line.cost_impact > self.max_cost_increase:
                continue
            
            if abs(line.quality_impact) > self.max_quality_decrease and line.quality_impact < 0:
                continue
            
            available_substitutes.append({
                'line': line,
                'substitute': substitute,  
                'available_qty': available_qty,
                'adjusted_qty': adjusted_qty,
                'score': self._calculate_substitute_score(line)
            })
        
        # Ordenar por score (mejor primero)
        if available_substitutes:
            best = sorted(available_substitutes, key=lambda x: x['score'], reverse=True)[0]
            return best['line']
        
        return None
    
    def _calculate_substitute_score(self, substitution_line):
        """Calcular score del sustituto (mayor = mejor)"""
        score = 100  # Score base
        
        # Penalizar incremento de costo
        score -= substitution_line.cost_impact * 2
        
        # Bonificar mejora de calidad, penalizar reducción
        score += substitution_line.quality_impact * 3
        
        # Bonificar disponibilidad
        availability = substitution_line.substitute_material_id.qty_available
        if availability > 1000:
            score += 10
        elif availability > 100:
            score += 5
        
        # Bonificar secuencia (prioridad configurada)
        score += (100 - substitution_line.sequence)
        
        return score
    
    def apply_substitution(self, bom_id, quantity_needed=0, context=None):
        """Aplicar sustitución a un BOM específico"""
        self.ensure_one()
        
        if not self.check_trigger_condition(context):
            return {'success': False, 'message': 'No se cumple la condición para aplicar sustitución'}
        
        best_substitute_line = self.get_best_substitute(quantity_needed, context)
        if not best_substitute_line:
            return {'success': False, 'message': 'No hay sustitutos disponibles'}
        
        bom = self.env['mrp.bom'].browse(bom_id)
        
        # Buscar línea BOM del material principal
        bom_line = bom.bom_line_ids.filtered(
            lambda l: l.product_id == self.primary_material_id
        )
        
        if not bom_line:
            return {'success': False, 'message': 'Material principal no encontrado en BOM'}
        
        # Aplicar sustitución
        try:
            original_product = bom_line.product_id
            original_qty = bom_line.product_qty
            
            # Calcular nueva cantidad
            new_qty = original_qty * best_substitute_line.conversion_factor
            
            # Si requiere aprobación y no está en contexto de aprobación
            if self.requires_approval and not context.get('approved', False):
                return self._create_approval_request(bom, bom_line, best_substitute_line, new_qty)
            
            # Aplicar sustitución
            bom_line.write({
                'product_id': best_substitute_line.substitute_material_id.id,
                'product_qty': new_qty
            })
            
            # Registrar aplicación
            self._record_application(bom, original_product, best_substitute_line, True)
            
            return {
                'success': True,
                'message': f'Sustituto aplicado: {best_substitute_line.substitute_material_id.name}',
                'original_material': original_product.name,
                'substitute_material': best_substitute_line.substitute_material_id.name,
                'conversion_factor': best_substitute_line.conversion_factor,
                'cost_impact': best_substitute_line.cost_impact,
                'quality_impact': best_substitute_line.quality_impact
            }
            
        except Exception as e:
            self._record_application(bom, bom_line.product_id, best_substitute_line, False, str(e))
            return {'success': False, 'message': f'Error aplicando sustitución: {str(e)}'}
    
    def _create_approval_request(self, bom, bom_line, substitute_line, new_qty):
        """Crear solicitud de aprobación"""
        # Crear actividad para aprobadores
        for approver in self.approver_ids:
            bom.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=f'Aprobar Sustitución Material: {self.name}',
                note=f"""
Solicitud de sustitución automática:

Material Original: {bom_line.product_id.name}
Material Sustituto: {substitute_line.substitute_material_id.name}
Cantidad Original: {bom_line.product_qty}
Cantidad Nueva: {new_qty}
Factor Conversión: {substitute_line.conversion_factor}
Impacto Costo: {substitute_line.cost_impact}%
Impacto Calidad: {substitute_line.quality_impact}%

BOM: {bom.display_name}
Regla: {self.name}
                """,
                user_id=approver.id,
            )
        
        return {
            'success': False,
            'message': 'Sustitución enviada para aprobación',
            'requires_approval': True
        }
    
    def _record_application(self, bom, original_material, substitute_line, success, error_message=None):
        """Registrar aplicación de la regla"""
        self.env['megastock.substitution.application'].create({
            'rule_id': self.id,
            'bom_id': bom.id,
            'original_material_id': original_material.id,
            'substitute_material_id': substitute_line.substitute_material_id.id,
            'conversion_factor': substitute_line.conversion_factor,
            'cost_impact': substitute_line.cost_impact,
            'quality_impact': substitute_line.quality_impact,
            'success': success,
            'error_message': error_message,
            'application_date': fields.Datetime.now()
        })
        
        # Actualizar estadísticas
        self.application_count += 1
        self.last_application_date = fields.Datetime.now()
    
    def _trigger_substitution_process(self):
        """Proceso automático de activación de sustitución"""
        self.ensure_one()
        
        # Buscar BOM que usen el material principal
        bom_lines = self.env['mrp.bom.line'].search([
            ('product_id', '=', self.primary_material_id.id)
        ])
        
        for bom_line in bom_lines:
            bom = bom_line.bom_id
            
            # Intentar aplicar sustitución
            result = self.apply_substitution(bom.id, bom_line.product_qty)
            
            if result['success']:
                _logger.info(f"Sustitución automática aplicada en BOM {bom.display_name}: {result['message']}")
            else:
                _logger.warning(f"No se pudo aplicar sustitución en BOM {bom.display_name}: {result['message']}")
    
    @api.model
    def evaluate_all_rules(self):
        """Evaluar todas las reglas activas automáticamente"""
        active_rules = self.search([('active', '=', True)])
        
        evaluated_count = 0
        applied_count = 0
        
        for rule in active_rules:
            try:
                if rule.check_trigger_condition():
                    evaluated_count += 1
                    rule._trigger_substitution_process()
                    applied_count += 1
                    
            except Exception as e:
                _logger.error(f"Error evaluando regla {rule.name}: {str(e)}")
        
        _logger.info(f"Evaluadas {evaluated_count} reglas, aplicadas {applied_count}")
        return {'evaluated': evaluated_count, 'applied': applied_count}


class MaterialSubstitutionLine(models.Model):
    _name = 'megastock.material.substitution.line'
    _description = 'Línea de Sustitución de Material'
    _order = 'sequence'
    
    substitution_rule_id = fields.Many2one(
        'megastock.material.substitution.rule',
        string='Regla de Sustitución',
        required=True,
        ondelete='cascade'
    )
    
    sequence = fields.Integer(
        string='Secuencia',
        default=10,
        help='Orden de preferencia del sustituto'
    )
    
    substitute_material_id = fields.Many2one(
        'product.product',
        string='Material Sustituto',
        required=True,
        help='Material que sustituye al principal'
    )
    
    conversion_factor = fields.Float(
        string='Factor de Conversión',
        default=1.0,
        help='Factor para convertir cantidad (ej: 1.2 = 20% más cantidad)'
    )
    
    cost_impact = fields.Float(
        string='Impacto en Costo (%)',
        help='Porcentaje de variación en costo (positivo = incremento)'
    )
    
    quality_impact = fields.Float(
        string='Impacto en Calidad (%)',
        help='Porcentaje de variación en calidad (positivo = mejora)'
    )
    
    availability_score = fields.Integer(
        string='Score Disponibilidad',
        default=5,
        help='Score de disponibilidad del sustituto (1-10)'
    )
    
    notes = fields.Text(
        string='Notas',
        help='Observaciones sobre la sustitución'
    )
    
    # Restricciones específicas
    min_quantity = fields.Float(
        string='Cantidad Mínima',
        default=0.0,
        help='Cantidad mínima para usar este sustituto'
    )
    
    max_quantity = fields.Float(
        string='Cantidad Máxima',
        default=0.0,
        help='Cantidad máxima para usar este sustituto'
    )


class SubstitutionApplication(models.Model):
    _name = 'megastock.substitution.application'
    _description = 'Historial de Aplicaciones de Sustitución'
    _order = 'application_date desc'
    
    rule_id = fields.Many2one(
        'megastock.material.substitution.rule',
        string='Regla',
        required=True,
        ondelete='cascade'
    )
    
    bom_id = fields.Many2one(
        'mrp.bom',
        string='BOM',
        required=True
    )
    
    original_material_id = fields.Many2one(
        'product.product',
        string='Material Original',
        required=True
    )
    
    substitute_material_id = fields.Many2one(
        'product.product',
        string='Material Sustituto',
        required=True
    )
    
    conversion_factor = fields.Float(
        string='Factor Conversión',
        default=1.0
    )
    
    cost_impact = fields.Float(
        string='Impacto Costo (%)'
    )
    
    quality_impact = fields.Float(
        string='Impacto Calidad (%)'
    )
    
    success = fields.Boolean(
        string='Exitosa',
        default=True
    )
    
    error_message = fields.Text(
        string='Mensaje de Error'
    )
    
    application_date = fields.Datetime(
        string='Fecha Aplicación',
        default=fields.Datetime.now
    )
    
    applied_by = fields.Many2one(
        'res.users',
        string='Aplicado Por',
        default=lambda self: self.env.user
    )