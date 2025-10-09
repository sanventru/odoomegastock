# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, timedelta


class MachineDowntime(models.Model):
    """Modelo básico para registrar paradas de máquinas"""
    _name = 'megastock.machine.downtime'
    _description = 'Paradas de Máquinas MEGASTOCK'
    _order = 'start_time desc'
    
    # Campos básicos
    name = fields.Char(
        string='Referencia',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: self._get_next_reference()
    )
    
    workcenter_id = fields.Many2one(
        'mrp.workcenter',
        string='Centro de Trabajo',
        required=True,
        help='Máquina o centro de trabajo afectado'
    )
    
    start_time = fields.Datetime(
        string='Hora Inicio',
        required=True,
        default=fields.Datetime.now,
        help='Momento en que inició la parada'
    )
    
    end_time = fields.Datetime(
        string='Hora Fin',
        help='Momento en que terminó la parada'
    )
    
    duration_minutes = fields.Float(
        string='Duración (min)',
        compute='_compute_duration',
        store=True,
        help='Duración total de la parada en minutos'
    )
    
    # Estado de la parada
    state = fields.Selection([
        ('in_progress', 'En Progreso'),
        ('resolved', 'Resuelto'),
        ('cancelled', 'Cancelado')
    ], string='Estado', default='in_progress', required=True)
    
    # Categorización básica
    category = fields.Selection([
        ('mechanical', 'Mecánica'),
        ('electrical', 'Eléctrica'),
        ('setup', 'Setup/Cambio'),
        ('material', 'Material/Insumos'),
        ('quality', 'Calidad'),
        ('planned', 'Planificada'),
        ('other', 'Otra')
    ], string='Categoría', required=True, default='mechanical')
    
    # Causas específicas según categoría
    cause = fields.Selection([
        # Mecánicas
        ('mechanical_bearing', 'Rodamientos'),
        ('mechanical_belt', 'Correas/Bandas'),
        ('mechanical_gear', 'Engranajes'),
        ('mechanical_cutting', 'Herramientas de corte'),
        ('mechanical_pressure', 'Problemas de presión'),
        # Eléctricas
        ('electrical_motor', 'Motor eléctrico'),
        ('electrical_sensor', 'Sensores'),
        ('electrical_wiring', 'Cableado'),
        ('electrical_control', 'Panel de control'),
        # Setup específicos MEGASTOCK
        ('setup_troquelado', 'Cambio de troqueles'),
        ('setup_tesaprint', 'Cambio tesaprint'),
        ('setup_rasquetas', 'Cambio rasquetas'),
        ('setup_goma', 'Cambio goma'),
        # Material
        ('material_bobinas', 'Peso bobinas'),
        ('material_adhesivo', 'Adhesivo/Cola'),
        ('material_tinta', 'Tintas impresión'),
        ('material_quality', 'Calidad materia prima'),
        # Calidad
        ('quality_dimensions', 'Dimensiones fuera spec'),
        ('quality_print', 'Calidad impresión'),
        ('quality_adhesion', 'Problemas adhesión'),
        # Otras
        ('other_cleaning', 'Limpieza programada'),
        ('other_training', 'Capacitación operador'),
        ('other_unknown', 'Causa desconocida')
    ], string='Causa Específica', help='Causa detallada de la parada')
    
    description = fields.Text(
        string='Descripción',
        required=True,
        help='Descripción detallada de la parada'
    )
    
    # Información del operador
    operator_name = fields.Char(
        string='Operador',
        help='Nombre del operador que reporta la parada'
    )
    
    # Acciones correctivas
    corrective_action = fields.Text(
        string='Acción Correctiva',
        help='Descripción de la acción tomada para resolver la parada'
    )
    
    @api.model
    def _get_next_reference(self):
        """Generar número secuencial para la parada"""
        last_downtime = self.search([], limit=1, order='id desc')
        if last_downtime and last_downtime.name:
            try:
                last_num = int(last_downtime.name.split('-')[-1])
                return f'PAR-{last_num + 1:04d}'
            except ValueError:
                pass
        return 'PAR-0001'
    
    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        """Calcular duración de la parada"""
        for record in self:
            if record.start_time and record.end_time:
                duration = record.end_time - record.start_time
                record.duration_minutes = duration.total_seconds() / 60.0
            else:
                record.duration_minutes = 0.0
    
    def action_resolve(self):
        """Marcar parada como resuelta"""
        if not self.corrective_action:
            # Abrir un wizard o form para capturar la acción correctiva
            return {
                'type': 'ir.actions.act_window',
                'name': 'Resolver Parada',
                'res_model': 'megastock.machine.downtime',
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
                'context': {'default_state': 'resolved'}
            }
        
        self.write({
            'state': 'resolved',
            'end_time': fields.Datetime.now()
        })
        return True