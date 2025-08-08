# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import math
import logging

_logger = logging.getLogger(__name__)

class MrpBomIntelligent(models.Model):
    _inherit = 'mrp.bom'
    
    # Campos inteligentes específicos
    is_intelligent = fields.Boolean(
        string='BOM Inteligente',
        default=False,
        help='Indica si este BOM usa cálculos automáticos inteligentes'
    )
    
    calculation_rules_ids = fields.Many2many(
        'megastock.bom.calculation.rule',
        'bom_calculation_rule_rel',
        'bom_id',
        'rule_id',
        string='Reglas de Cálculo',
        help='Reglas automáticas aplicadas a este BOM'
    )
    
    auto_update_enabled = fields.Boolean(
        string='Actualización Automática',
        default=True,
        help='Permite actualización automática de cantidades basada en especificaciones'
    )
    
    last_calculation_date = fields.Datetime(
        string='Última Actualización Automática',
        readonly=True,
        help='Fecha de la última actualización automática'
    )
    
    # Campos de análisis de costos
    current_total_cost = fields.Float(
        string='Costo Total Actual',
        compute='_compute_current_costs',
        store=True,
        help='Costo total actual basado en precios vigentes'
    )
    
    standard_total_cost = fields.Float(
        string='Costo Total Estándar',
        help='Costo total estándar de referencia'
    )
    
    cost_variance = fields.Float(
        string='Variación de Costo',
        compute='_compute_cost_variance',
        store=True,
        help='Diferencia entre costo actual y estándar'
    )
    
    cost_variance_percentage = fields.Float(
        string='Variación Costo (%)',
        compute='_compute_cost_variance',
        store=True
    )
    
    cost_alert_level = fields.Selection([
        ('normal', 'Normal'),
        ('warning', 'Advertencia'),
        ('critical', 'Crítico')
    ], string='Nivel Alerta Costo', 
       compute='_compute_cost_alert_level',
       store=True)
    
    # Optimización automática
    optimization_opportunities = fields.Text(
        string='Oportunidades de Optimización',
        compute='_compute_optimization_opportunities',
        help='Sugerencias automáticas de optimización'
    )
    
    waste_percentage_actual = fields.Float(
        string='Merma Real (%)',
        compute='_compute_actual_waste',
        store=True,
        help='Porcentaje de merma real vs planificado'
    )
    
    # Sustituciones inteligentes
    has_substitution_rules = fields.Boolean(
        string='Tiene Sustituciones',
        compute='_compute_has_substitutions',
        help='Indica si hay reglas de sustitución configuradas'
    )
    
    alternative_bom_ids = fields.One2many(
        'mrp.bom.alternative',
        'primary_bom_id',
        string='BOM Alternativos',
        help='BOM alternativos según disponibilidad de materiales'
    )
    
    # Planificación automática de compras
    purchase_planning_ids = fields.One2many(
        'megastock.purchase.planning',
        'bom_id',
        string='Planificación de Compras',
        help='Planificación automática de compras basada en este BOM'
    )
    
    @api.depends('bom_line_ids', 'bom_line_ids.product_id.standard_price')
    def _compute_current_costs(self):
        """Calcular costo total actual basado en precios vigentes"""
        for bom in self:
            total_cost = 0.0
            for line in bom.bom_line_ids:
                line_cost = line.product_qty * line.product_id.standard_price
                total_cost += line_cost
            bom.current_total_cost = total_cost
    
    @api.depends('current_total_cost', 'standard_total_cost')
    def _compute_cost_variance(self):
        """Calcular variación de costos"""
        for bom in self:
            if bom.standard_total_cost > 0:
                bom.cost_variance = bom.current_total_cost - bom.standard_total_cost
                bom.cost_variance_percentage = (bom.cost_variance / bom.standard_total_cost) * 100
            else:
                bom.cost_variance = 0.0
                bom.cost_variance_percentage = 0.0
    
    @api.depends('cost_variance_percentage')
    def _compute_cost_alert_level(self):
        """Determinar nivel de alerta por variación de costos"""
        for bom in self:
            variance = abs(bom.cost_variance_percentage)
            if variance < 5:
                bom.cost_alert_level = 'normal'
            elif variance < 15:
                bom.cost_alert_level = 'warning'
            else:
                bom.cost_alert_level = 'critical'
    
    def _compute_optimization_opportunities(self):
        """Identificar oportunidades de optimización automáticamente"""
        for bom in self:
            opportunities = []
            
            # Analizar mermas altas
            if bom.waste_percentage_actual > 8.0:
                opportunities.append("• Merma alta detectada: revisar cálculos y procesos")
            
            # Analizar materiales costosos
            expensive_lines = bom.bom_line_ids.filtered(
                lambda l: l.product_qty * l.product_id.standard_price > bom.current_total_cost * 0.3
            )
            for line in expensive_lines:
                opportunities.append(f"• Material costoso: {line.product_id.name} - evaluar sustitutos")
            
            # Analizar disponibilidad
            low_stock_lines = bom.bom_line_ids.filtered(
                lambda l: l.product_id.qty_available < l.product_qty * 10  # Menos de 10 lotes
            )
            for line in low_stock_lines:
                opportunities.append(f"• Stock bajo: {line.product_id.name} - considerar alternativas")
            
            # Analizar consolidación de proveedores
            suppliers = bom.bom_line_ids.mapped('product_id.seller_ids.name')
            if len(suppliers) > 5:
                opportunities.append("• Múltiples proveedores: evaluar consolidación")
            
            bom.optimization_opportunities = '\n'.join(opportunities) if opportunities else 'No se detectaron oportunidades inmediatas'
    
    def _compute_actual_waste(self):
        """Calcular merma real basada en producciones históricas"""
        for bom in self:
            # Buscar producciones recientes con este BOM
            productions = self.env['mrp.production'].search([
                ('bom_id', '=', bom.id),
                ('state', '=', 'done')
            ], limit=10)
            
            if productions:
                total_planned = sum(productions.mapped('product_qty'))
                total_consumed = 0.0
                
                for production in productions:
                    for move in production.move_raw_ids:
                        total_consumed += move.quantity_done
                
                if total_planned > 0:
                    # Calcular merma promedio
                    theoretical_consumption = sum(
                        line.product_qty * total_planned / bom.product_qty 
                        for line in bom.bom_line_ids
                    )
                    
                    if theoretical_consumption > 0:
                        waste_pct = ((total_consumed - theoretical_consumption) / theoretical_consumption) * 100
                        bom.waste_percentage_actual = max(0, waste_pct)
                    else:
                        bom.waste_percentage_actual = 0.0
                else:
                    bom.waste_percentage_actual = 0.0
            else:
                bom.waste_percentage_actual = 0.0
    
    @api.depends('bom_line_ids.product_id')
    def _compute_has_substitutions(self):
        """Verificar si hay reglas de sustitución disponibles"""
        for bom in self:
            materials = bom.bom_line_ids.mapped('product_id')
            substitution_rules = self.env['megastock.material.substitution.rule'].search([
                ('primary_material_id', 'in', materials.ids),
                ('active', '=', True)
            ])
            bom.has_substitution_rules = bool(substitution_rules)
    
    @api.model
    def create(self, vals):
        """Override create para aplicar reglas automáticas"""
        bom = super(MrpBomIntelligent, self).create(vals)
        
        if vals.get('is_intelligent', False):
            bom._apply_calculation_rules()
            bom._set_standard_cost()
        
        return bom
    
    def write(self, vals):
        """Override write para recalcular si cambian especificaciones"""
        result = super(MrpBomIntelligent, self).write(vals)
        
        # Si cambian dimensiones del producto, recalcular automáticamente
        product_fields = ['length', 'width', 'height']
        if any(field in vals for field in product_fields) and self.is_intelligent:
            self._apply_calculation_rules()
        
        return result
    
    def _apply_calculation_rules(self):
        """Aplicar reglas de cálculo automático"""
        for bom in self:
            if not bom.is_intelligent or not bom.auto_update_enabled:
                continue
            
            # Obtener reglas aplicables por categoría de producto
            applicable_rules = self.env['megastock.bom.calculation.rule'].search([
                ('category_ids', 'in', [bom.product_tmpl_id.categ_id.id]),
                ('active', '=', True)
            ])
            
            # Aplicar cada regla
            for rule in applicable_rules:
                try:
                    bom._apply_single_calculation_rule(rule)
                except Exception as e:
                    _logger.warning(f"Error aplicando regla {rule.name} a BOM {bom.display_name}: {str(e)}")
            
            bom.last_calculation_date = fields.Datetime.now()
            bom.calculation_rules_ids = [(6, 0, applicable_rules.ids)]
    
    def _apply_single_calculation_rule(self, rule):
        """Aplicar una regla específica de cálculo"""
        self.ensure_one()
        
        # Obtener especificaciones del producto
        specs = self._get_product_specifications()
        
        if rule.calculation_type == 'surface_area':
            calculated_area = self._calculate_surface_area(rule, specs)
            self._update_bom_lines_by_area(calculated_area, rule.waste_percentage)
            
        elif rule.calculation_type == 'material_consumption':
            calculated_consumption = self._calculate_material_consumption(rule, specs)
            self._update_material_consumption(rule, calculated_consumption)
            
        elif rule.calculation_type == 'piece_count':
            calculated_pieces = self._calculate_piece_count(rule, specs)
            self._update_piece_count(rule, calculated_pieces)
            
        elif rule.calculation_type == 'variant_calculation':
            self._calculate_variant_adjustments(rule, specs)
    
    def _get_product_specifications(self):
        """Obtener especificaciones del producto para cálculos"""
        product = self.product_tmpl_id
        
        return {
            'length': getattr(product, 'length', 0) or 300,  # Default 300mm
            'width': getattr(product, 'width', 0) or 200,    # Default 200mm
            'height': getattr(product, 'height', 0) or 150,  # Default 150mm
            'surface_area': 0,  # Se calculará
            'quantity': self.product_qty,
            'adhesive_rate': 0.008,  # 8 g/m²
            'layers': 2,  # Corrugado simple
            'coverage_percentage': 0.3,  # 30% cobertura tinta
            'ink_density': 0.015,  # 15 g/m²
        }
    
    def _calculate_surface_area(self, rule, specs):
        """Calcular área de superficie usando la fórmula de la regla"""
        try:
            # Variables disponibles para eval
            variables = {
                'length': specs['length'],
                'width': specs['width'], 
                'height': specs['height'],
                'math': math
            }
            
            # Evaluar fórmula
            area = eval(rule.formula, {"__builtins__": {}}, variables)
            
            # Aplicar factor de merma
            area_with_waste = area * (1 + rule.waste_percentage / 100.0)
            
            return area_with_waste
            
        except Exception as e:
            _logger.error(f"Error calculando área con regla {rule.name}: {str(e)}")
            return 0.0
    
    def _calculate_material_consumption(self, rule, specs):
        """Calcular consumo de materiales específicos"""
        try:
            # Calcular área si no está disponible
            if specs['surface_area'] == 0:
                area_rule = self.env['megastock.bom.calculation.rule'].search([
                    ('calculation_type', '=', 'surface_area'),
                    ('category_ids', 'in', [self.product_tmpl_id.categ_id.id])
                ], limit=1)
                
                if area_rule:
                    specs['surface_area'] = self._calculate_surface_area(area_rule, specs)
            
            # Variables para consumo
            variables = {
                'surface_area': specs['surface_area'],
                'adhesive_rate': specs['adhesive_rate'],
                'layers': specs['layers'],
                'coverage_percentage': specs['coverage_percentage'],
                'ink_density': specs['ink_density'],
                'quantity': specs['quantity']
            }
            
            consumption = eval(rule.formula, {"__builtins__": {}}, variables)
            
            # Aplicar factor de merma
            consumption_with_waste = consumption * (1 + rule.waste_percentage / 100.0)
            
            return consumption_with_waste
            
        except Exception as e:
            _logger.error(f"Error calculando consumo con regla {rule.name}: {str(e)}")
            return 0.0
    
    def _update_bom_lines_by_area(self, calculated_area, waste_percentage):
        """Actualizar líneas BOM basadas en área calculada"""
        # Materiales que se calculan por área (papeles)
        area_materials = self.bom_line_ids.filtered(
            lambda l: l.product_id.categ_id.name in ['Papel KRAFT', 'Papel Medium', 'Papel Liner']
        )
        
        for line in area_materials:
            # Cantidad = área calculada
            new_qty = calculated_area
            
            if abs(line.product_qty - new_qty) > 0.01:  # Solo actualizar si hay diferencia significativa
                line.product_qty = new_qty
                _logger.info(f"BOM {self.display_name}: Actualizada cantidad {line.product_id.name} a {new_qty:.2f} m²")
    
    def _update_material_consumption(self, rule, consumption):
        """Actualizar consumo de materiales específicos"""
        # Identificar material por código de regla
        if rule.code == 'ADHESIVE_CONSUMPTION':
            adhesive_lines = self.bom_line_ids.filtered(
                lambda l: 'adhesivo' in l.product_id.name.lower()
            )
            for line in adhesive_lines:
                line.product_qty = consumption
                
        elif rule.code == 'INK_CONSUMPTION':
            ink_lines = self.bom_line_ids.filtered(
                lambda l: 'tinta' in l.product_id.name.lower()
            )
            for line in ink_lines:
                # Distribuir consumo entre colores disponibles
                line.product_qty = consumption / len(ink_lines) if ink_lines else consumption
    
    def action_recalculate_intelligent(self):
        """Acción manual para recalcular BOM inteligente"""
        if not self.is_intelligent:
            raise UserError("Este BOM no está configurado como inteligente.")
        
        self._apply_calculation_rules()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'BOM Recalculado',
                'message': f'BOM {self.display_name} recalculado automáticamente.',
                'type': 'success',
            }
        }
    
    def action_optimize_bom(self):
        """Lanzar wizard de optimización"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Optimizar BOM',
            'res_model': 'megastock.bom.optimizer.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_bom_id': self.id,
            }
        }
    
    def action_suggest_substitutions(self):
        """Sugerir sustituciones de materiales"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sustituciones Sugeridas',
            'res_model': 'megastock.material.substitution.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_bom_id': self.id,
            }
        }
    
    def action_plan_purchases(self):
        """Generar plan de compras automático"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Planificación de Compras',
            'res_model': 'megastock.purchase.planning.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_bom_id': self.id,
            }
        }
    
    def _set_standard_cost(self):
        """Establecer costo estándar basado en cálculo actual"""
        for bom in self:
            if not bom.standard_total_cost:
                bom.standard_total_cost = bom.current_total_cost
    
    @api.model
    def auto_update_intelligent_boms(self):
        """Actualización automática masiva de BOM inteligentes"""
        intelligent_boms = self.search([
            ('is_intelligent', '=', True),
            ('auto_update_enabled', '=', True),
            ('active', '=', True)
        ])
        
        updated_count = 0
        for bom in intelligent_boms:
            try:
                # Solo actualizar si han pasado más de 24 horas
                if not bom.last_calculation_date or \
                   (fields.Datetime.now() - bom.last_calculation_date).days >= 1:
                    
                    bom._apply_calculation_rules()
                    updated_count += 1
                    
            except Exception as e:
                _logger.error(f"Error actualizando BOM inteligente {bom.display_name}: {str(e)}")
        
        _logger.info(f"Actualizados {updated_count} BOM inteligentes automáticamente")
        return updated_count
    
    def get_intelligent_bom_summary(self):
        """Obtener resumen de BOM inteligente para dashboard"""
        self.ensure_one()
        
        return {
            'name': self.display_name,
            'product_name': self.product_tmpl_id.name,
            'is_intelligent': self.is_intelligent,
            'current_cost': self.current_total_cost,
            'standard_cost': self.standard_total_cost,
            'cost_variance': self.cost_variance,
            'cost_variance_percentage': self.cost_variance_percentage,
            'cost_alert_level': self.cost_alert_level,
            'waste_percentage': self.waste_percentage_actual,
            'has_substitutions': self.has_substitution_rules,
            'last_update': self.last_calculation_date,
            'optimization_opportunities': len(self.optimization_opportunities.split('\n')) if self.optimization_opportunities else 0
        }