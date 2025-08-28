# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime

class WorkOrder(models.Model):
    _name = 'megastock.work.order'
    _description = 'Orden de Trabajo MEGASTOCK'
    _order = 'fecha_creacion desc, numero_orden'
    _rec_name = 'numero_orden'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Campos principales
    numero_orden = fields.Char(string='Número de Orden', required=True, copy=False, readonly=True, index=True, default=lambda self: self._get_next_sequence())
    fecha_creacion = fields.Datetime(string='Fecha de Creación', default=fields.Datetime.now, readonly=True)
    fecha_programada = fields.Date(string='Fecha Programada')
    fecha_inicio = fields.Datetime(string='Fecha de Inicio')
    fecha_fin = fields.Datetime(string='Fecha de Finalización')
    
    # Estado de la orden de trabajo
    estado = fields.Selection([
        ('borrador', 'Borrador'),
        ('programada', 'Programada'),
        ('en_proceso', 'En Proceso'),
        ('pausada', 'Pausada'),
        ('completada', 'Completada'),
        ('cancelada', 'Cancelada'),
    ], string='Estado', default='borrador', required=True, tracking=True)
    
    # Información del grupo de planificación
    grupo_planificacion = fields.Char(string='Grupo de Planificación', required=True, index=True)
    tipo_combinacion = fields.Selection([
        ('individual', 'Individual'),
        ('dupla', 'Dupla'),
        ('tripla', 'Tripla'),
    ], string='Tipo de Combinación', required=True)
    
    # Especificaciones técnicas
    bobina_utilizada = fields.Float(string='Bobina Utilizada (mm)', required=True)
    ancho_utilizado = fields.Float(string='Ancho Utilizado (mm)', required=True)
    sobrante = fields.Float(string='Sobrante (mm)')
    eficiencia = fields.Float(string='Eficiencia (%)')
    metros_lineales_totales = fields.Float(string='Metros Lineales Totales')
    cortes_totales = fields.Integer(string='Cortes Totales')
    
    # Relación con órdenes de producción
    production_order_ids = fields.One2many('megastock.production.order', 'work_order_id', string='Órdenes de Producción')
    cantidad_ordenes = fields.Integer(string='Cantidad de Órdenes', compute='_compute_cantidad_ordenes', store=True)
    
    # Campos de seguimiento
    operador = fields.Many2one('res.users', string='Operador Asignado')
    maquina = fields.Char(string='Máquina')
    turno = fields.Selection([
        ('manana', 'Mañana'),
        ('tarde', 'Tarde'),
        ('noche', 'Noche'),
    ], string='Turno')
    
    # Observaciones y notas
    observaciones = fields.Text(string='Observaciones')
    notas_produccion = fields.Text(string='Notas de Producción')
    
    # Campos calculados
    duracion_estimada = fields.Float(string='Duración Estimada (horas)', compute='_compute_duracion_estimada', store=True)
    duracion_real = fields.Float(string='Duración Real (horas)', compute='_compute_duracion_real', store=True)
    progreso = fields.Float(string='Progreso (%)', compute='_compute_progreso', store=True)
    
    @api.model
    def _get_next_sequence(self):
        """Genera el siguiente número secuencial para la orden de trabajo"""
        last_order = self.search([], order='numero_orden desc', limit=1)
        if last_order and last_order.numero_orden:
            try:
                # Extraer el número de la secuencia (formato: OT-YYYY-NNNN)
                parts = last_order.numero_orden.split('-')
                if len(parts) >= 3:
                    year = datetime.now().year
                    last_year = int(parts[1])
                    last_number = int(parts[2])
                    
                    if year == last_year:
                        next_number = last_number + 1
                    else:
                        next_number = 1
                        
                    return f"OT-{year}-{next_number:04d}"
            except (ValueError, IndexError):
                pass
        
        # Si no hay órdenes previas o hay error, empezar desde 1
        year = datetime.now().year
        return f"OT-{year}-0001"
    
    @api.depends('production_order_ids')
    def _compute_cantidad_ordenes(self):
        for record in self:
            record.cantidad_ordenes = len(record.production_order_ids)
    
    @api.depends('metros_lineales_totales', 'tipo_combinacion')
    def _compute_duracion_estimada(self):
        """Calcula duración estimada basada en metros lineales y tipo de combinación"""
        for record in self:
            if record.metros_lineales_totales:
                # Velocidad base: 100 metros/hora
                velocidad_base = 100
                
                # Ajustar velocidad según tipo de combinación
                if record.tipo_combinacion == 'individual':
                    velocidad = velocidad_base * 1.2  # Más rápido para individuales
                elif record.tipo_combinacion == 'dupla':
                    velocidad = velocidad_base
                else:  # tripla
                    velocidad = velocidad_base * 0.8  # Más lento para triplas
                
                record.duracion_estimada = record.metros_lineales_totales / velocidad
            else:
                record.duracion_estimada = 0.0
    
    @api.depends('fecha_inicio', 'fecha_fin')
    def _compute_duracion_real(self):
        for record in self:
            if record.fecha_inicio and record.fecha_fin:
                delta = record.fecha_fin - record.fecha_inicio
                record.duracion_real = delta.total_seconds() / 3600  # Convertir a horas
            else:
                record.duracion_real = 0.0
    
    @api.depends('estado', 'production_order_ids.estado')
    def _compute_progreso(self):
        for record in self:
            if not record.production_order_ids:
                record.progreso = 0.0
                continue
            
            if record.estado == 'completada':
                record.progreso = 100.0
            elif record.estado in ['borrador', 'programada']:
                record.progreso = 0.0
            else:
                # Calcular progreso basado en órdenes completadas
                total_ordenes = len(record.production_order_ids)
                ordenes_completadas = len(record.production_order_ids.filtered(lambda o: o.estado == 'entregado'))
                record.progreso = (ordenes_completadas / total_ordenes) * 100 if total_ordenes > 0 else 0.0
    
    def name_get(self):
        result = []
        for record in self:
            name = f"{record.numero_orden}"
            if record.grupo_planificacion:
                name += f" - {record.grupo_planificacion}"
            if record.tipo_combinacion:
                name += f" ({record.tipo_combinacion.title()})"
            result.append((record.id, name))
        return result
    
    def action_programar(self):
        """Acción para programar la orden de trabajo"""
        self.write({'estado': 'programada'})
        return True
    
    def action_iniciar(self):
        """Acción para iniciar la orden de trabajo"""
        self.write({
            'estado': 'en_proceso',
            'fecha_inicio': fields.Datetime.now()
        })
        return True
    
    def action_pausar(self):
        """Acción para pausar la orden de trabajo"""
        self.write({'estado': 'pausada'})
        return True
    
    def action_completar(self):
        """Acción para completar la orden de trabajo"""
        self.write({
            'estado': 'completada',
            'fecha_fin': fields.Datetime.now()
        })
        # Actualizar estado de órdenes de producción relacionadas
        self.production_order_ids.write({'estado': 'entregado'})
        return True
    
    def action_cancelar(self):
        """Acción para cancelar la orden de trabajo"""
        self.write({'estado': 'cancelada'})
        return True
