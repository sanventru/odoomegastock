# -*- coding: utf-8 -*-

from odoo import api, fields, models


class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'

    production_line_type = fields.Selection([
        ('papel_periodico', 'Papel Periódico'),
        ('cajas', 'Cajas & Planchas'),
        ('lamina_micro', 'Lámina Micro Corrugada')
    ], 'Tipo de Línea de Producción', 
    help="Especifica a qué línea de producción pertenece este centro de trabajo")

    # Estadísticas de paradas
    total_stoppages = fields.Integer(
        'Total de Paradas', 
        compute='_compute_stoppage_stats',
        help="Número total de paradas registradas en este centro"
    )
    
    total_stoppage_time = fields.Float(
        'Tiempo Total de Paradas (hrs)', 
        compute='_compute_stoppage_stats',
        help="Tiempo total de paradas en horas"
    )
    
    avg_stoppage_duration = fields.Float(
        'Duración Promedio de Paradas (min)', 
        compute='_compute_stoppage_stats',
        help="Duración promedio de paradas en minutos"
    )

    @api.depends('name')
    def _compute_stoppage_stats(self):
        """Calcular estadísticas de paradas para este centro de trabajo"""
        for record in self:
            stoppages = self.env['mrp.workorder.stoppage'].search([
                ('workcenter_id', '=', record.id),
                ('end_time', '!=', False)  # Solo paradas finalizadas
            ])
            
            record.total_stoppages = len(stoppages)
            total_minutes = sum(stoppages.mapped('duration_minutes'))
            record.total_stoppage_time = total_minutes / 60.0  # Convertir a horas
            record.avg_stoppage_duration = total_minutes / len(stoppages) if stoppages else 0.0

    def action_view_stoppages(self):
        """Abrir vista de paradas para este centro de trabajo"""
        action = self.env.ref('mrp_production_lines.action_mrp_workorder_stoppage').read()[0]
        action['domain'] = [('workcenter_id', '=', self.id)]
        action['context'] = {
            'default_workcenter_id': self.id,
            'search_default_workcenter_id': self.id,
        }
        return action