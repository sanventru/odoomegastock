# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class MrpStoppageCategory(models.Model):
    _name = 'mrp.stoppage.category'
    _description = 'Categorías de Paradas de Producción'
    _rec_name = 'name'
    _order = 'sequence, name'

    name = fields.Char('Motivo de Parada', required=True, translate=True)
    code = fields.Char('Código', required=True, size=10)
    sequence = fields.Integer('Secuencia', default=10)
    
    production_line = fields.Selection([
        ('all', 'Todas las Líneas'),
        ('papel_periodico', 'Papel Periódico'),
        ('cajas', 'Cajas & Planchas'),
        ('lamina_micro', 'Lámina Micro Corrugada')
    ], 'Líneas Aplicables', required=True, default='all')
    
    workcenter_ids = fields.Many2many(
        'mrp.workcenter', 
        'mrp_stoppage_category_workcenter_rel',
        'category_id', 'workcenter_id',
        'Centros de Trabajo Aplicables',
        help="Si se deja vacío, aplica a todos los centros de trabajo"
    )
    
    color = fields.Integer('Color', default=1, help="Color para reportes y vistas kanban")
    active = fields.Boolean('Activo', default=True)
    
    description = fields.Text('Descripción')
    
    # Estadísticas
    stoppage_count = fields.Integer('Número de Paradas', compute='_compute_stoppage_stats')
    total_duration = fields.Float('Duración Total (min)', compute='_compute_stoppage_stats')
    
    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'El código debe ser único!'),
    ]
    
    @api.depends('name')
    def _compute_stoppage_stats(self):
        """Calcular estadísticas de paradas para esta categoría"""
        for record in self:
            stoppages = self.env['mrp.workorder.stoppage'].search([
                ('stoppage_category_id', '=', record.id)
            ])
            record.stoppage_count = len(stoppages)
            record.total_duration = sum(stoppages.mapped('duration_minutes'))
    
    @api.constrains('production_line', 'workcenter_ids')
    def _check_workcenter_line_consistency(self):
        """Validar que los centros de trabajo sean consistentes con la línea seleccionada"""
        for record in self:
            if record.production_line != 'all' and record.workcenter_ids:
                inconsistent_workcenters = record.workcenter_ids.filtered(
                    lambda w: w.production_line_type and w.production_line_type != record.production_line
                )
                if inconsistent_workcenters:
                    raise ValidationError(_(
                        'Los centros de trabajo %s no pertenecen a la línea de producción %s'
                    ) % (', '.join(inconsistent_workcenters.mapped('name')), 
                         dict(self._fields['production_line'].selection)[record.production_line]))