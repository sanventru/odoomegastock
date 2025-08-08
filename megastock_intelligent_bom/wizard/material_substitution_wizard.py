# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError

class MaterialSubstitutionWizard(models.TransientModel):
    _name = 'megastock.material.substitution.wizard'
    _description = 'Asistente de Sustitución de Materiales'
    
    bom_id = fields.Many2one(
        'mrp.bom',
        string='BOM',
        required=True,
        help='BOM donde se aplicarán sustituciones'
    )
    
    substitution_mode = fields.Selection([
        ('automatic', 'Automático por Reglas'),
        ('manual', 'Selección Manual'),
        ('emergency', 'Sustitución de Emergencia')
    ], string='Modo de Sustitución', default='automatic', required=True)
    
    trigger_reason = fields.Selection([
        ('stock_shortage', 'Falta de Stock'),
        ('cost_increase', 'Incremento de Costo'),
        ('quality_requirement', 'Requerimiento de Calidad'),
        ('supplier_issue', 'Problema Proveedor'),
        ('expiry_approaching', 'Próximo Vencimiento'),
        ('optimization', 'Optimización')
    ], string='Razón de Sustitución', required=True)
    
    max_cost_increase = fields.Float(
        string='Máximo Incremento Costo (%)',
        default=15.0,
        help='Máximo incremento de costo permitido'
    )
    
    min_quality_level = fields.Float(
        string='Nivel Mínimo Calidad (%)',
        default=95.0,
        help='Nivel mínimo de calidad aceptable'
    )
    
    auto_apply = fields.Boolean(
        string='Aplicar Automáticamente',
        default=False,
        help='Aplicar sustituciones automáticamente sin confirmación'
    )
    
    # Líneas de sustitución sugeridas
    substitution_line_ids = fields.One2many(
        'megastock.material.substitution.wizard.line',
        'wizard_id',
        string='Sustituciones Sugeridas'
    )
    
    total_impact_cost = fields.Float(
        string='Impacto Total Costo',
        compute='_compute_total_impact',
        help='Impacto total en costo'
    )
    
    total_impact_quality = fields.Float(
        string='Impacto Total Calidad',
        compute='_compute_total_impact',
        help='Impacto total en calidad'
    )
    
    @api.depends('substitution_line_ids.cost_impact', 'substitution_line_ids.quality_impact')
    def _compute_total_impact(self):
        """Calcular impacto total"""
        for wizard in self:
            wizard.total_impact_cost = sum(wizard.substitution_line_ids.mapped('cost_impact'))
            wizard.total_impact_quality = sum(wizard.substitution_line_ids.mapped('quality_impact')) / len(wizard.substitution_line_ids) if wizard.substitution_line_ids else 0.0
    
    def action_find_substitutions(self):
        """Buscar sustituciones disponibles"""
        self.ensure_one()
        
        if not self.bom_id:
            raise UserError("Debe seleccionar un BOM válido.")
        
        # Limpiar líneas existentes
        self.substitution_line_ids.unlink()
        
        substitutions_found = []
        
        # Buscar sustituciones por cada material del BOM
        for bom_line in self.bom_id.bom_line_ids:
            material_substitutions = self._find_material_substitutions(bom_line)
            substitutions_found.extend(material_substitutions)
        
        # Crear líneas de sustitución
        for substitution in substitutions_found:
            self.env['megastock.material.substitution.wizard.line'].create({
                'wizard_id': self.id,
                'bom_line_id': substitution['bom_line_id'],
                'original_material_id': substitution['original_material_id'],
                'substitute_material_id': substitution['substitute_material_id'],
                'substitution_rule_id': substitution['rule_id'],
                'conversion_factor': substitution['conversion_factor'],
                'cost_impact': substitution['cost_impact'],
                'quality_impact': substitution['quality_impact'],
                'availability_score': substitution['availability_score'],
                'recommended': substitution['recommended'],
                'notes': substitution['notes']
            })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'substitutions_found': len(substitutions_found)}
        }
    
    def _find_material_substitutions(self, bom_line):
        """Buscar sustituciones para un material específico"""
        substitutions = []
        
        # Buscar reglas de sustitución
        substitution_rules = self.env['megastock.material.substitution.rule'].search([
            ('primary_material_id', '=', bom_line.product_id.id),
            ('active', '=', True)
        ])
        
        for rule in substitution_rules:
            # Verificar si la regla aplica según la razón
            if self._rule_matches_reason(rule):
                # Obtener mejor sustituto
                best_substitute = rule.get_best_substitute(bom_line.product_qty)
                
                if best_substitute:
                    # Verificar restricciones
                    if (best_substitute.cost_impact <= self.max_cost_increase and
                        (100 + best_substitute.quality_impact) >= self.min_quality_level):
                        
                        substitutions.append({
                            'bom_line_id': bom_line.id,
                            'original_material_id': bom_line.product_id.id,
                            'substitute_material_id': best_substitute.substitute_material_id.id,
                            'rule_id': rule.id,
                            'conversion_factor': best_substitute.conversion_factor,
                            'cost_impact': best_substitute.cost_impact,
                            'quality_impact': best_substitute.quality_impact,
                            'availability_score': best_substitute.availability_score,
                            'recommended': True,
                            'notes': f"Regla: {rule.name}"
                        })
        
        return substitutions
    
    def _rule_matches_reason(self, rule):
        """Verificar si la regla coincide con la razón de sustitución"""
        reason_mapping = {
            'stock_shortage': ['availability', 'stock_below_minimum', 'stock_unavailable'],
            'cost_increase': ['cost_optimization', 'cost_variance_above'],
            'quality_requirement': ['quality_requirement'],
            'supplier_issue': ['supplier_issue', 'supplier_unavailable'],
            'expiry_approaching': ['expiry_approaching'],
            'optimization': ['cost_optimization', 'quality_requirement']
        }
        
        applicable_triggers = reason_mapping.get(self.trigger_reason, [])
        return rule.trigger_condition in applicable_triggers or rule.substitution_type in applicable_triggers
    
    def action_apply_substitutions(self):
        """Aplicar sustituciones seleccionadas"""
        self.ensure_one()
        
        selected_lines = self.substitution_line_ids.filtered('selected')
        
        if not selected_lines:
            raise UserError("Debe seleccionar al menos una sustitución para aplicar.")
        
        applied_count = 0
        errors = []
        
        for line in selected_lines:
            try:
                result = line.substitution_rule_id.apply_substitution(
                    self.bom_id.id, 
                    line.bom_line_id.product_qty,
                    context={'approved': True}  # Pre-aprobado desde wizard
                )
                
                if result.get('success'):
                    applied_count += 1
                else:
                    errors.append(f"{line.original_material_id.name}: {result.get('message', 'Error desconocido')}")
                    
            except Exception as e:
                errors.append(f"{line.original_material_id.name}: {str(e)}")
        
        # Mostrar resultado
        message = f"Se aplicaron {applied_count} sustituciones exitosamente."
        if errors:
            message += f"\n\nErrores:\n" + "\n".join(errors)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Sustituciones Aplicadas',
                'message': message,
                'type': 'success' if applied_count > 0 else 'warning',
                'sticky': True,
            }
        }
    
    def action_apply_all_recommended(self):
        """Aplicar todas las sustituciones recomendadas"""
        recommended_lines = self.substitution_line_ids.filtered('recommended')
        
        for line in recommended_lines:
            line.selected = True
        
        return self.action_apply_substitutions()


class MaterialSubstitutionWizardLine(models.TransientModel):
    _name = 'megastock.material.substitution.wizard.line'
    _description = 'Línea de Sustitución Material'
    _order = 'recommended desc, availability_score desc'
    
    wizard_id = fields.Many2one(
        'megastock.material.substitution.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade'
    )
    
    selected = fields.Boolean(
        string='Seleccionar',
        default=False,
        help='Seleccionar esta sustitución para aplicar'
    )
    
    bom_line_id = fields.Many2one(
        'mrp.bom.line',
        string='Línea BOM',
        required=True,
        help='Línea BOM que será modificada'
    )
    
    original_material_id = fields.Many2one(
        'product.product',
        string='Material Original',
        required=True,
        help='Material actual en el BOM'
    )
    
    substitute_material_id = fields.Many2one(
        'product.product',
        string='Material Sustituto',
        required=True,
        help='Material sugerido como sustituto'
    )
    
    substitution_rule_id = fields.Many2one(
        'megastock.material.substitution.rule',
        string='Regla',
        required=True,
        help='Regla que sugiere esta sustitución'
    )
    
    conversion_factor = fields.Float(
        string='Factor Conversión',
        default=1.0,
        help='Factor para convertir cantidades'
    )
    
    cost_impact = fields.Float(
        string='Impacto Costo (%)',
        help='Porcentaje de variación en costo'
    )
    
    quality_impact = fields.Float(
        string='Impacto Calidad (%)',
        help='Porcentaje de variación en calidad'
    )
    
    availability_score = fields.Integer(
        string='Score Disponibilidad',
        help='Score de disponibilidad (1-10)'
    )
    
    current_stock = fields.Float(
        string='Stock Actual',
        related='substitute_material_id.qty_available',
        help='Stock actual del sustituto'
    )
    
    recommended = fields.Boolean(
        string='Recomendado',
        default=False,
        help='Sustitución recomendada por el sistema'
    )
    
    notes = fields.Text(
        string='Notas',
        help='Observaciones sobre la sustitución'
    )
    
    @api.onchange('selected')
    def _onchange_selected(self):
        """Auto-marcar recomendado si se selecciona"""
        if self.selected and not self.recommended:
            self.recommended = True