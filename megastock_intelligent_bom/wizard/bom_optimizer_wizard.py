# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError

class BomOptimizerWizard(models.TransientModel):
    _name = 'megastock.bom.optimizer.wizard'
    _description = 'Asistente de Optimización BOM'
    
    bom_id = fields.Many2one(
        'mrp.bom',
        string='BOM a Optimizar',
        required=True,
        help='BOM que será optimizado'
    )
    
    optimization_type = fields.Selection([
        ('cost', 'Optimización de Costos'),
        ('waste', 'Reducción de Mermas'),
        ('supplier', 'Consolidación Proveedores'),
        ('quality', 'Mejora de Calidad'),
        ('all', 'Optimización Integral')
    ], string='Tipo de Optimización', default='all', required=True)
    
    target_cost_reduction = fields.Float(
        string='Meta Reducción Costo (%)',
        default=10.0,
        help='Porcentaje objetivo de reducción de costos'
    )
    
    max_quality_impact = fields.Float(
        string='Máximo Impacto Calidad (%)',
        default=5.0,
        help='Máximo impacto negativo permitido en calidad'
    )
    
    apply_substitutions = fields.Boolean(
        string='Aplicar Sustituciones',
        default=True,
        help='Aplicar sustituciones de materiales automáticamente'
    )
    
    recalculate_quantities = fields.Boolean(
        string='Recalcular Cantidades',
        default=True,
        help='Recalcular cantidades usando reglas inteligentes'
    )
    
    # Resultados de la optimización
    optimization_summary = fields.Text(
        string='Resumen Optimización',
        readonly=True,
        help='Resumen de optimizaciones aplicadas'
    )
    
    potential_savings = fields.Float(
        string='Ahorros Potenciales',
        readonly=True,
        help='Ahorros potenciales calculados'
    )
    
    def action_analyze_optimization(self):
        """Analizar oportunidades de optimización"""
        self.ensure_one()
        
        if not self.bom_id:
            raise UserError("Debe seleccionar un BOM válido.")
        
        summary = []
        total_savings = 0.0
        
        # Analizar por tipo de optimización
        if self.optimization_type in ['cost', 'all']:
            cost_analysis = self._analyze_cost_optimization()
            summary.extend(cost_analysis['suggestions'])
            total_savings += cost_analysis['savings']
        
        if self.optimization_type in ['waste', 'all']:
            waste_analysis = self._analyze_waste_reduction()
            summary.extend(waste_analysis['suggestions'])
            total_savings += waste_analysis['savings']
        
        if self.optimization_type in ['supplier', 'all']:
            supplier_analysis = self._analyze_supplier_consolidation()
            summary.extend(supplier_analysis['suggestions'])
            total_savings += supplier_analysis['savings']
        
        if self.optimization_type in ['quality', 'all']:
            quality_analysis = self._analyze_quality_improvements()
            summary.extend(quality_analysis['suggestions'])
        
        # Actualizar resultados
        self.optimization_summary = '\n'.join(summary) if summary else 'No se encontraron oportunidades de optimización'
        self.potential_savings = total_savings
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'analysis_completed': True}
        }
    
    def action_apply_optimization(self):
        """Aplicar optimizaciones al BOM"""
        self.ensure_one()
        
        if not self.optimization_summary:
            raise UserError("Debe analizar primero las optimizaciones disponibles.")
        
        changes_made = 0
        
        # Aplicar sustituciones si está habilitado
        if self.apply_substitutions:
            changes_made += self._apply_material_substitutions()
        
        # Recalcular cantidades si está habilitado
        if self.recalculate_quantities:
            changes_made += self._recalculate_bom_quantities()
        
        # Registrar optimización
        self._create_optimization_record(changes_made)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Optimización Completada',
                'message': f'Se aplicaron {changes_made} optimizaciones al BOM.',
                'type': 'success',
            }
        }
    
    def _analyze_cost_optimization(self):
        """Analizar oportunidades de optimización de costos"""
        suggestions = []
        savings = 0.0
        
        # Analizar materiales más costosos
        expensive_lines = self.bom_id.bom_line_ids.sorted(
            key=lambda l: l.product_qty * l.product_id.standard_price, reverse=True
        )[:3]  # Top 3 más costosos
        
        for line in expensive_lines:
            line_cost = line.product_qty * line.product_id.standard_price
            
            # Buscar sustitutos más económicos
            substitution_rules = self.env['megastock.material.substitution.rule'].search([
                ('primary_material_id', '=', line.product_id.id),
                ('substitution_type', '=', 'cost_optimization'),
                ('active', '=', True)
            ])
            
            for rule in substitution_rules:
                best_substitute = rule.get_best_substitute()
                if best_substitute and best_substitute.cost_impact < 0:  # Reducción de costo
                    potential_saving = abs(best_substitute.cost_impact / 100.0) * line_cost
                    savings += potential_saving
                    suggestions.append(
                        f"• Sustituir {line.product_id.name} por {best_substitute.substitute_material_id.name} "
                        f"- Ahorro: ${potential_saving:.2f}"
                    )
        
        return {'suggestions': suggestions, 'savings': savings}
    
    def _analyze_waste_reduction(self):
        """Analizar oportunidades de reducción de mermas"""
        suggestions = []
        savings = 0.0
        
        # Verificar merma actual vs objetivo
        if hasattr(self.bom_id, 'waste_percentage_actual') and self.bom_id.waste_percentage_actual > 5.0:
            excess_waste = self.bom_id.waste_percentage_actual - 5.0
            potential_saving = self.bom_id.current_total_cost * (excess_waste / 100.0)
            savings += potential_saving
            
            suggestions.append(
                f"• Reducir merma del {self.bom_id.waste_percentage_actual:.1f}% al 5.0% "
                f"- Ahorro potencial: ${potential_saving:.2f}"
            )
        
        # Analizar líneas con alta merma
        for line in self.bom_id.bom_line_ids:
            if hasattr(line, 'calculation_rule_id') and line.calculation_rule_id:
                rule = line.calculation_rule_id
                if rule.waste_percentage > 6.0:  # Merma alta
                    suggestions.append(
                        f"• Revisar fórmula de {line.product_id.name} - Merma configurada: {rule.waste_percentage}%"
                    )
        
        return {'suggestions': suggestions, 'savings': savings}
    
    def _analyze_supplier_consolidation(self):
        """Analizar consolidación de proveedores"""
        suggestions = []
        savings = 0.0
        
        # Obtener proveedores únicos
        suppliers = set()
        for line in self.bom_id.bom_line_ids:
            for seller in line.product_id.seller_ids:
                if seller.name.is_company:
                    suppliers.add(seller.name)
        
        if len(suppliers) > 3:
            # Sugerir consolidación
            potential_saving = self.bom_id.current_total_cost * 0.05  # 5% ahorro por consolidación
            savings += potential_saving
            
            suggestions.append(
                f"• Consolidar {len(suppliers)} proveedores en 2-3 principales "
                f"- Ahorro estimado: ${potential_saving:.2f}"
            )
        
        return {'suggestions': suggestions, 'savings': savings}
    
    def _analyze_quality_improvements(self):
        """Analizar mejoras de calidad"""
        suggestions = []
        
        # Buscar oportunidades de mejora de calidad
        for line in self.bom_id.bom_line_ids:
            substitution_rules = self.env['megastock.material.substitution.rule'].search([
                ('primary_material_id', '=', line.product_id.id),
                ('substitution_type', '=', 'quality_requirement'),
                ('active', '=', True)
            ])
            
            for rule in substitution_rules:
                best_substitute = rule.get_best_substitute()
                if best_substitute and best_substitute.quality_impact > 0:
                    suggestions.append(
                        f"• Mejorar calidad de {line.product_id.name} con {best_substitute.substitute_material_id.name} "
                        f"- Mejora: +{best_substitute.quality_impact}%"
                    )
        
        return {'suggestions': suggestions, 'savings': 0.0}
    
    def _apply_material_substitutions(self):
        """Aplicar sustituciones de materiales"""
        changes = 0
        
        for line in self.bom_id.bom_line_ids:
            substitution_rules = self.env['megastock.material.substitution.rule'].search([
                ('primary_material_id', '=', line.product_id.id),
                ('active', '=', True)
            ])
            
            for rule in substitution_rules:
                if rule.check_trigger_condition():
                    result = rule.apply_substitution(self.bom_id.id, line.product_qty)
                    if result.get('success'):
                        changes += 1
        
        return changes
    
    def _recalculate_bom_quantities(self):
        """Recalcular cantidades del BOM"""
        if hasattr(self.bom_id, '_apply_calculation_rules'):
            self.bom_id._apply_calculation_rules()
            return 1  # Una recalculación completa
        return 0
    
    def _create_optimization_record(self, changes_made):
        """Crear registro de optimización"""
        self.env['megastock.bom.optimization.history'].create({
            'bom_id': self.bom_id.id,
            'optimization_type': self.optimization_type,
            'changes_applied': changes_made,
            'potential_savings': self.potential_savings,
            'optimization_summary': self.optimization_summary,
            'applied_date': fields.Datetime.now(),
            'applied_by': self.env.user.id,
        })


class BomOptimizationHistory(models.Model):
    _name = 'megastock.bom.optimization.history'
    _description = 'Historial de Optimizaciones BOM'
    _order = 'applied_date desc'
    
    bom_id = fields.Many2one(
        'mrp.bom',
        string='BOM',
        required=True,
        ondelete='cascade'
    )
    
    optimization_type = fields.Selection([
        ('cost', 'Optimización de Costos'),
        ('waste', 'Reducción de Mermas'),
        ('supplier', 'Consolidación Proveedores'),
        ('quality', 'Mejora de Calidad'),
        ('all', 'Optimización Integral')
    ], string='Tipo', required=True)
    
    changes_applied = fields.Integer(
        string='Cambios Aplicados',
        help='Número de cambios aplicados'
    )
    
    potential_savings = fields.Float(
        string='Ahorros Potenciales',
        help='Ahorros estimados de la optimización'
    )
    
    optimization_summary = fields.Text(
        string='Resumen',
        help='Resumen de la optimización'
    )
    
    applied_date = fields.Datetime(
        string='Fecha Aplicación',
        default=fields.Datetime.now
    )
    
    applied_by = fields.Many2one(
        'res.users',
        string='Aplicado Por',
        default=lambda self: self.env.user
    )