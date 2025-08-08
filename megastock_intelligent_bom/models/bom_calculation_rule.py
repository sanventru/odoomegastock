# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError

class BomCalculationRule(models.Model):
    _name = 'megastock.bom.calculation.rule'
    _description = 'Reglas de Cálculo Automático para BOM'
    _order = 'sequence, name'
    
    name = fields.Char(
        string='Nombre',
        required=True,
        help='Nombre descriptivo de la regla'
    )
    
    code = fields.Char(
        string='Código',
        required=True,
        help='Código único para identificar la regla'
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
    
    calculation_type = fields.Selection([
        ('surface_area', 'Cálculo de Área'),
        ('material_consumption', 'Consumo de Material'),
        ('piece_count', 'Conteo de Piezas'),
        ('roll_optimization', 'Optimización de Bobinas'),
        ('variant_calculation', 'Cálculo por Variantes'),
        ('waste_calculation', 'Cálculo de Mermas'),
        ('cost_calculation', 'Cálculo de Costos')
    ], string='Tipo de Cálculo', required=True)
    
    category_ids = fields.Many2many(
        'product.category',
        'calculation_rule_category_rel',
        'rule_id',
        'category_id',
        string='Categorías Aplicables',
        required=True,
        help='Categorías de productos donde aplica esta regla'
    )
    
    formula = fields.Text(
        string='Fórmula de Cálculo',
        required=True,
        help='Fórmula Python para el cálculo. Variables disponibles: length, width, height, quantity, etc.'
    )
    
    description = fields.Text(
        string='Descripción',
        help='Descripción detallada de la regla y su aplicación'
    )
    
    # Parámetros de la regla
    unit_factor = fields.Float(
        string='Factor Unitario',
        default=1.0,
        help='Factor multiplicador aplicado al resultado'
    )
    
    waste_percentage = fields.Float(
        string='Porcentaje de Merma (%)',
        default=0.0,
        help='Porcentaje de merma a agregar al cálculo base'
    )
    
    min_value = fields.Float(
        string='Valor Mínimo',
        default=0.0,
        help='Valor mínimo que puede tomar el resultado'
    )
    
    max_value = fields.Float(
        string='Valor Máximo',
        default=0.0,
        help='Valor máximo que puede tomar el resultado (0 = sin límite)'
    )
    
    # Condiciones de aplicación
    condition_field = fields.Selection([
        ('product_length', 'Longitud Producto'),
        ('product_width', 'Ancho Producto'),
        ('product_height', 'Alto Producto'),
        ('product_weight', 'Peso Producto'),
        ('bom_quantity', 'Cantidad BOM'),
        ('always', 'Siempre')
    ], string='Campo Condición', default='always')
    
    condition_operator = fields.Selection([
        ('>', 'Mayor que'),
        ('>=', 'Mayor o igual'),
        ('<', 'Menor que'),
        ('<=', 'Menor o igual'),
        ('=', 'Igual a'),
        ('!=', 'Diferente de')
    ], string='Operador')
    
    condition_value = fields.Float(
        string='Valor Condición',
        help='Valor para evaluar la condición'
    )
    
    # Configuración avanzada
    apply_to_variants = fields.Boolean(
        string='Aplicar a Variantes',
        default=True,
        help='Aplicar automáticamente a variantes del producto'
    )
    
    update_frequency = fields.Selection([
        ('manual', 'Manual'),
        ('on_change', 'Al Cambiar Especificaciones'),
        ('daily', 'Diario'),
        ('weekly', 'Semanal')
    ], string='Frecuencia Actualización', default='on_change')
    
    # Variables personalizadas
    custom_variables = fields.Text(
        string='Variables Personalizadas',
        help='Variables adicionales en formato JSON: {"variable": "valor"}'
    )
    
    # Historial de uso
    usage_count = fields.Integer(
        string='Veces Aplicada',
        default=0,
        readonly=True
    )
    
    last_applied_date = fields.Datetime(
        string='Última Aplicación',
        readonly=True
    )
    
    @api.constrains('formula')
    def _check_formula_syntax(self):
        """Validar sintaxis de la fórmula"""
        for rule in self:
            if rule.formula:
                try:
                    # Test básico de compilación
                    compile(rule.formula, '<string>', 'eval')
                except SyntaxError:
                    raise ValidationError(f"Error de sintaxis en fórmula de regla '{rule.name}': {rule.formula}")
    
    @api.constrains('code')
    def _check_unique_code(self):
        """Verificar que el código sea único"""
        for rule in self:
            if self.search_count([('code', '=', rule.code), ('id', '!=', rule.id)]) > 0:
                raise ValidationError(f"Ya existe una regla con código '{rule.code}'")
    
    def test_formula(self, test_values=None):
        """Probar la fórmula con valores de prueba"""
        self.ensure_one()
        
        if not test_values:
            test_values = {
                'length': 300,
                'width': 200,
                'height': 150,
                'quantity': 1000,
                'surface_area': 0.156,
                'adhesive_rate': 0.008,
                'layers': 2,
                'coverage_percentage': 0.3,
                'ink_density': 0.015,
            }
        
        try:
            import math
            test_values['math'] = math
            
            result = eval(self.formula, {"__builtins__": {}}, test_values)
            
            # Aplicar factor unitario
            result *= self.unit_factor
            
            # Aplicar merma
            if self.waste_percentage > 0:
                result *= (1 + self.waste_percentage / 100.0)
            
            # Aplicar límites
            if self.min_value > 0:
                result = max(result, self.min_value)
            if self.max_value > 0:
                result = min(result, self.max_value)
            
            return {
                'success': True,
                'result': result,
                'message': f'Fórmula evaluada correctamente. Resultado: {result:.4f}'
            }
            
        except Exception as e:
            return {
                'success': False,
                'result': 0,
                'message': f'Error evaluando fórmula: {str(e)}'
            }
    
    def action_test_formula(self):
        """Acción para probar la fórmula desde la interfaz"""
        test_result = self.test_formula()
        
        message_type = 'success' if test_result['success'] else 'danger'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Resultado Test Fórmula',
                'message': test_result['message'],
                'type': message_type,
            }
        }
    
    def check_condition(self, product_tmpl, bom):
        """Verificar si se cumple la condición para aplicar la regla"""
        if self.condition_field == 'always':
            return True
        
        # Obtener valor del campo
        field_value = 0
        if self.condition_field == 'product_length':
            field_value = getattr(product_tmpl, 'length', 0)
        elif self.condition_field == 'product_width':
            field_value = getattr(product_tmpl, 'width', 0)
        elif self.condition_field == 'product_height':
            field_value = getattr(product_tmpl, 'height', 0)
        elif self.condition_field == 'product_weight':
            field_value = getattr(product_tmpl, 'weight', 0)
        elif self.condition_field == 'bom_quantity':
            field_value = bom.product_qty if bom else 0
        
        # Evaluar condición
        if self.condition_operator == '>':
            return field_value > self.condition_value
        elif self.condition_operator == '>=':
            return field_value >= self.condition_value
        elif self.condition_operator == '<':
            return field_value < self.condition_value
        elif self.condition_operator == '<=':
            return field_value <= self.condition_value
        elif self.condition_operator == '=':
            return field_value == self.condition_value
        elif self.condition_operator == '!=':
            return field_value != self.condition_value
        
        return True
    
    def apply_to_bom(self, bom):
        """Aplicar esta regla a un BOM específico"""
        self.ensure_one()
        
        # Verificar condición
        if not self.check_condition(bom.product_tmpl_id, bom):
            return False
        
        try:
            # Incrementar contador de uso
            self.usage_count += 1
            self.last_applied_date = fields.Datetime.now()
            
            # Aplicar la regla (implementación específica en BOM)
            bom._apply_single_calculation_rule(self)
            
            return True
            
        except Exception as e:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error(f"Error aplicando regla {self.name} a BOM {bom.display_name}: {str(e)}")
            return False
    
    @api.model
    def get_applicable_rules(self, product_category_id, calculation_type=None):
        """Obtener reglas aplicables para una categoría de producto"""
        domain = [
            ('category_ids', 'in', [product_category_id]),
            ('active', '=', True)
        ]
        
        if calculation_type:
            domain.append(('calculation_type', '=', calculation_type))
        
        return self.search(domain, order='sequence')
    
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
    
    @api.model
    def create_formula_wizard(self):
        """Lanzar wizard para crear fórmulas fácilmente"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Asistente de Fórmulas',
            'res_model': 'megastock.formula.wizard',
            'view_mode': 'form',
            'target': 'new',
        }
    
    def get_statistics(self):
        """Obtener estadísticas de uso de la regla"""
        self.ensure_one()
        
        # BOM que usan esta regla
        boms_using_rule = self.env['mrp.bom'].search([
            ('calculation_rules_ids', 'in', [self.id])
        ])
        
        return {
            'rule_name': self.name,
            'usage_count': self.usage_count,
            'last_applied': self.last_applied_date,
            'boms_count': len(boms_using_rule),
            'categories_count': len(self.category_ids),
            'average_applications_per_month': self.usage_count / 12 if self.usage_count else 0
        }