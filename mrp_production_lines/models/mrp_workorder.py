# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    # === INFORMACIÓN DE LÍNEA DE PRODUCCIÓN ===
    production_line = fields.Selection([
        ('papel_periodico', 'Papel Periódico'),
        ('cajas', 'Cajas & Planchas'), 
        ('lamina_micro', 'Lámina Micro Corrugada')
    ], string='Línea de Producción', 
    compute='_compute_production_line', 
    store=True,
    help="Línea de producción basada en el centro de trabajo")

    # === CAMPOS PARA ETIQUETAS ===
    pallet_number = fields.Char(
        'N° de Pallet', 
        help="Número de pallet asignado para trazabilidad"
    )
    
    custom_product_code = fields.Char(
        'Código Producto Personalizado',
        help="Código específico del producto para etiquetas"
    )
    
    operator_name = fields.Char(
        'Operador', 
        help="Nombre del operador responsable de la estación"
    )
    
    shift = fields.Selection([
        ('morning', 'Mañana'), 
        ('afternoon', 'Tarde'), 
        ('night', 'Noche')
    ], 'Turno', help="Turno de trabajo")

    # === CAMPOS TÉCNICOS ESPECÍFICOS ===
    # Para Cajas
    material_type = fields.Char(
        'Material', 
        help="Tipo de material utilizado (específico para línea de cajas)"
    )
    
    test_value = fields.Char(
        'Test', 
        help="Valor de test de resistencia del cartón"
    )
    
    flute_type = fields.Selection([
        ('A', 'Flauta A'), 
        ('B', 'Flauta B'), 
        ('C', 'Flauta C'),
        ('E', 'Flauta E'), 
        ('F', 'Flauta F')
    ], 'Tipo de Flauta', help="Tipo de flauta del cartón corrugado")
    
    factor = fields.Float(
        'Factor', 
        help="Factor de producción específico"
    )

    # Para Papel y Lámina Micro
    grammage = fields.Float(
        'Gramaje (g/m²)', 
        help="Gramaje del papel en gramos por metro cuadrado"
    )
    
    weight = fields.Float(
        'Peso (kg)', 
        help="Peso de bobinas o material"
    )

    # === CAMPOS PARA EMPAQUE ===
    units_per_package = fields.Integer(
        'Cantidad por Paquete',
        help="Número de unidades por paquete"
    )
    
    total_packages = fields.Integer(
        'Cantidad de Bultos',
        help="Número total de bultos/paquetes"
    )
    
    customer_logo = fields.Boolean(
        'Incluir Logotipo Cliente',
        default=False,
        help="Indica si se debe incluir el logotipo del cliente en las etiquetas"
    )

    # === SISTEMA DE CONTROL DE PARADAS ===
    stoppage_ids = fields.One2many(
        'mrp.workorder.stoppage', 
        'workorder_id', 
        'Paradas Registradas'
    )
    
    active_stoppage_id = fields.Many2one(
        'mrp.workorder.stoppage',
        'Parada Activa',
        compute='_compute_active_stoppage',
        help="Parada actualmente en curso (sin hora de fin)"
    )
    
    has_active_stoppage = fields.Boolean(
        'Tiene Parada Activa',
        compute='_compute_active_stoppage',
        help="Indica si hay una parada actualmente activa"
    )
    
    total_stoppage_time = fields.Float(
        'Tiempo Total de Paradas (min)', 
        compute='_compute_stoppage_stats',
        store=True,
        help="Tiempo total de paradas en minutos"
    )
    
    stoppage_count = fields.Integer(
        'Número de Paradas', 
        compute='_compute_stoppage_stats',
        store=True,
        help="Número total de paradas registradas"
    )

    # === CÁLCULOS DE EFICIENCIA ===
    efficiency_percentage = fields.Float(
        'Eficiencia (%)', 
        compute='_compute_efficiency',
        store=True,
        help="Porcentaje de eficiencia considerando paradas"
    )
    
    productive_time = fields.Float(
        'Tiempo Productivo (min)',
        compute='_compute_efficiency',
        store=True,
        help="Tiempo real de producción descontando paradas"
    )

    # === MÉTODOS COMPUTADOS ===
    
    @api.depends('workcenter_id.production_line_type')
    def _compute_production_line(self):
        for record in self:
            record.production_line = record.workcenter_id.production_line_type or False

    @api.depends('stoppage_ids.is_active')
    def _compute_active_stoppage(self):
        for record in self:
            active_stoppage = record.stoppage_ids.filtered('is_active')
            record.active_stoppage_id = active_stoppage[0].id if active_stoppage else False
            record.has_active_stoppage = bool(active_stoppage)

    @api.depends('stoppage_ids.duration_minutes')
    def _compute_stoppage_stats(self):
        for record in self:
            finished_stoppages = record.stoppage_ids.filtered('end_time')
            record.total_stoppage_time = sum(finished_stoppages.mapped('duration_minutes'))
            record.stoppage_count = len(record.stoppage_ids)

    @api.depends('duration', 'duration_expected', 'total_stoppage_time')
    def _compute_efficiency(self):
        for record in self:
            if record.duration and record.duration > 0:
                # Tiempo productivo = tiempo total - tiempo de paradas
                record.productive_time = max(0, record.duration - record.total_stoppage_time)
                
                if record.duration_expected and record.duration_expected > 0:
                    # Eficiencia = tiempo productivo / tiempo esperado * 100
                    record.efficiency_percentage = min(100, (record.productive_time / record.duration_expected) * 100)
                else:
                    record.efficiency_percentage = 0.0
            else:
                record.productive_time = 0.0
                record.efficiency_percentage = 0.0

    # === ACCIONES Y BOTONES ===
    
    def action_register_stoppage(self):
        """Abrir wizard para registrar una nueva parada"""
        if self.has_active_stoppage:
            raise UserError(_('Ya existe una parada activa. Debe finalizar la parada actual antes de registrar una nueva.'))
        
        # Filtrar categorías aplicables según la línea de producción y centro de trabajo
        domain = [
            ('active', '=', True),
            '|', ('production_line', '=', 'all'),
            ('production_line', '=', self.production_line or 'all')
        ]
        
        # Si la categoría tiene centros específicos, filtrar por el centro actual
        domain.append(('workcenter_ids', 'in', [self.workcenter_id.id, False]))
        
        return {
            'name': _('Registrar Parada'),
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.workorder.stoppage',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_workorder_id': self.id,
                'default_start_time': fields.Datetime.now(),
            },
            'domain': domain,
        }

    def action_end_active_stoppage(self):
        """Finalizar la parada activa"""
        if not self.has_active_stoppage:
            raise UserError(_('No hay paradas activas para finalizar.'))
        
        self.active_stoppage_id.action_end_stoppage()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_view_stoppages(self):
        """Ver todas las paradas de esta orden de trabajo"""
        action = self.env.ref('mrp_production_lines.action_mrp_workorder_stoppage').read()[0]
        action['domain'] = [('workorder_id', '=', self.id)]
        action['context'] = {
            'default_workorder_id': self.id,
            'search_default_workorder_id': self.id,
        }
        return action

    def action_print_label(self):
        """Imprimir etiqueta con información específica de la línea"""
        # Esta acción puede ser expandida para generar diferentes tipos de etiquetas
        # según la línea de producción
        return {
            'type': 'ir.actions.report',
            'report_name': 'mrp_production_lines.workorder_label_report',
            'report_type': 'qweb-pdf',
            'data': {'ids': [self.id]},
            'context': self.env.context,
        }

    def action_efficiency_analysis(self):
        """Mostrar análisis de eficiencia detallado"""
        return {
            'name': _('Análisis de Eficiencia'),
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.workorder',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('mrp_production_lines.view_mrp_workorder_efficiency_form').id,
            'target': 'new',
        }

    # === VALIDACIONES ===
    
    @api.constrains('pallet_number')
    def _check_pallet_number_unique(self):
        """Validar que el número de pallet sea único por producción"""
        for record in self:
            if record.pallet_number:
                existing = self.search([
                    ('production_id', '=', record.production_id.id),
                    ('pallet_number', '=', record.pallet_number),
                    ('id', '!=', record.id)
                ])
                if existing:
                    raise UserError(_(
                        'El número de pallet "%s" ya está siendo usado en otra orden de trabajo de la misma producción.'
                    ) % record.pallet_number)

    # === OVERRIDE DE MÉTODOS ESTÁNDAR ===
    
    def button_start(self):
        """Override para validaciones adicionales al iniciar"""
        res = super().button_start()
        
        # Finalizar cualquier parada activa al iniciar trabajo
        if self.has_active_stoppage:
            self.active_stoppage_id.action_end_stoppage()
            
        return res

    def button_finish(self):
        """Override para validaciones adicionales al finalizar"""
        # Finalizar paradas activas antes de completar
        if self.has_active_stoppage:
            self.active_stoppage_id.action_end_stoppage()
            
        return super().button_finish()