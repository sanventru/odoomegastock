# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class MrpWorkorderStoppage(models.Model):
    _name = 'mrp.workorder.stoppage'
    _description = 'Paradas de Órdenes de Trabajo'
    _order = 'start_time desc'
    _rec_name = 'display_name'

    display_name = fields.Char('Nombre', compute='_compute_display_name', store=True)
    
    workorder_id = fields.Many2one(
        'mrp.workorder', 
        'Orden de Trabajo', 
        required=True, 
        ondelete='cascade',
        index=True
    )
    
    stoppage_category_id = fields.Many2one(
        'mrp.stoppage.category', 
        'Categoría de Parada', 
        required=True,
        domain="[('active', '=', True)]"
    )
    
    start_time = fields.Datetime('Hora Inicio', required=True, default=fields.Datetime.now)
    end_time = fields.Datetime('Hora Fin')
    
    duration_minutes = fields.Float(
        'Duración (min)', 
        compute='_compute_duration', 
        store=True,
        help="Duración de la parada en minutos"
    )
    
    is_active = fields.Boolean(
        'Parada Activa', 
        compute='_compute_is_active', 
        store=True,
        help="Indica si la parada está actualmente activa (sin hora de fin)"
    )
    
    notes = fields.Text('Observaciones')
    
    operator_id = fields.Many2one(
        'hr.employee', 
        'Operador que Reporta',
        help="Empleado que reportó la parada"
    )
    
    # Campos relacionados para facilitar búsquedas y reportes
    workcenter_id = fields.Many2one(
        'mrp.workcenter', 
        'Centro de Trabajo',
        related='workorder_id.workcenter_id', 
        store=True,
        readonly=True
    )
    
    production_id = fields.Many2one(
        'mrp.production',
        'Orden de Producción',
        related='workorder_id.production_id',
        store=True,
        readonly=True
    )
    
    production_line = fields.Selection(
        related='stoppage_category_id.production_line',
        string='Línea de Producción',
        store=True,
        readonly=True
    )
    
    color = fields.Integer(related='stoppage_category_id.color', readonly=True)
    
    company_id = fields.Many2one(
        'res.company',
        related='workorder_id.company_id',
        store=True,
        readonly=True
    )

    @api.depends('stoppage_category_id.name', 'start_time', 'duration_minutes')
    def _compute_display_name(self):
        for record in self:
            if record.stoppage_category_id and record.start_time:
                duration_str = f" ({record.duration_minutes:.0f} min)" if record.duration_minutes else " (En curso)"
                record.display_name = f"{record.stoppage_category_id.name} - {record.start_time.strftime('%H:%M')}{duration_str}"
            else:
                record.display_name = "Nueva Parada"

    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for record in self:
            if record.start_time and record.end_time:
                delta = record.end_time - record.start_time
                record.duration_minutes = delta.total_seconds() / 60.0
            else:
                record.duration_minutes = 0.0

    @api.depends('end_time')
    def _compute_is_active(self):
        for record in self:
            record.is_active = not bool(record.end_time)

    @api.constrains('start_time', 'end_time')
    def _check_time_sequence(self):
        for record in self:
            if record.start_time and record.end_time:
                if record.end_time <= record.start_time:
                    raise ValidationError(_('La hora de fin debe ser posterior a la hora de inicio.'))
                
                # Verificar que la duración no sea excesiva (más de 24 horas)
                if record.duration_minutes > 1440:  # 24 * 60
                    raise ValidationError(_('La duración de la parada no puede exceder 24 horas.'))

    @api.constrains('stoppage_category_id', 'workcenter_id')
    def _check_category_workcenter_compatibility(self):
        """Verificar que la categoría de parada sea aplicable al centro de trabajo"""
        for record in self:
            if (record.stoppage_category_id.workcenter_ids and 
                record.workcenter_id not in record.stoppage_category_id.workcenter_ids):
                raise ValidationError(_(
                    'La categoría de parada "%s" no está configurada para el centro de trabajo "%s".'
                ) % (record.stoppage_category_id.name, record.workcenter_id.name))

    def action_end_stoppage(self):
        """Finalizar la parada activa"""
        if not self.end_time:
            self.end_time = fields.Datetime.now()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Parada Finalizada'),
                    'message': _('La parada ha sido finalizada con una duración de %.0f minutos.') % self.duration_minutes,
                    'type': 'success',
                }
            }
        else:
            raise ValidationError(_('Esta parada ya ha sido finalizada.'))

    def action_extend_stoppage(self):
        """Extender una parada finalizada (quitar hora de fin)"""
        if self.end_time:
            self.end_time = False
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Parada Extendida'),
                    'message': _('La parada ha sido reactivada.'),
                    'type': 'info',
                }
            }
        else:
            raise ValidationError(_('Esta parada ya está activa.'))

    @api.model
    def create(self, vals):
        """Override create para validaciones adicionales"""
        # Si no se proporciona operador, usar el usuario actual si es empleado
        if not vals.get('operator_id'):
            employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
            if employee:
                vals['operator_id'] = employee.id
        
        return super().create(vals)