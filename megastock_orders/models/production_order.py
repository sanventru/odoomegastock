# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime
import math

class ProductionOrder(models.Model):
    _name = 'megastock.production.order'
    _description = 'Orden de Producción MEGASTOCK'
    _order = 'fecha_pedido_cliente desc, orden_produccion'
    _rec_name = 'orden_produccion'

    # Campos principales del pedido
    orden_produccion = fields.Char(string='Orden de Producción', index=True)
    fecha_pedido_cliente = fields.Date(string='Fecha Pedido Cliente')
    flauta = fields.Char(string='Flauta')
    cliente = fields.Char(string='Cliente', required=True, index=True)
    pedido = fields.Char(string='Pedido')
    codigo = fields.Char(string='Código', index=True)
    descripcion = fields.Text(string='Descripción')
    
    # Dimensiones y cantidades
    largo = fields.Float(string='Largo (mm)')
    ancho = fields.Float(string='Ancho (mm)')
    alto = fields.Float(string='Alto (mm)')
    cantidad = fields.Integer(string='Cantidad')
    cavidad = fields.Integer(string='Cavidad')

    # Información del producto (extraída del CSV)
    tipo_producto = fields.Selection([
        ('cajas', 'CAJAS'),
        ('laminas', 'LAMINAS'),
        ('planchas', 'PLANCHAS')
    ], string='Tipo Producto', help='Tipo de producto extraído del CSV')

    sustrato = fields.Selection([
        ('kk', 'K/K'),
        ('km', 'K/M'),
        ('mk', 'M/K'),
        ('mm', 'M/M')
    ], string='Sustrato', help='Tipo de sustrato extraído del CSV')

    troquel = fields.Selection([
        ('si', 'SI'),
        ('no', 'NO')
    ], string='Troquel', help='Indica si el producto requiere troquel')

    # Dimensiones rayado
    largo_rayado = fields.Float(
        string='Largo Rayado (mm)',
        compute='_compute_largo_rayado',
        store=True,
        help='Dimensión largo rayado: alto + 2'
    )
    ancho_rayado = fields.Float(
        string='Ancho Rayado (mm)',
        compute='_compute_ancho_rayado',
        store=True,
        help='Dimensión ancho rayado: ancho_calculado - (alto_rayado * 2)'
    )
    alto_rayado = fields.Float(
        string='Alto Rayado (mm)',
        compute='_compute_alto_rayado',
        store=True,
        help='Dimensión alto rayado: alto + 2'
    )

    # Campos calculados para trimado
    largo_calculado = fields.Float(
        string='Largo Calculado (mm)',
        compute='_compute_largo_calculado',
        store=True,
        help='Largo real: 2*alto + largo + 8'
    )

    ancho_calculado = fields.Float(
        string='Ancho Calculado (mm)',
        compute='_compute_ancho_calculado',
        store=True,
        help='Ancho real: 2*alto + ancho + 14'
    )

    cantidad_ajustada = fields.Float(
        string='Cantidad Ajustada',
        compute='_compute_cantidad_ajustada',
        store=True,
        help='Cantidad optimizada según cavidad: ceil(cantidad/cavidad) * cavidad'
    )

    metros_lineales_calculados = fields.Float(
        string='Metros Lineales Calculados',
        compute='_compute_metros_lineales_calculados',
        store=True,
        help='Metros lineales: ((cantidad_ajustada * largo_calculado) / cavidad) / 1000'
    )

    peso_lamina_calculado = fields.Float(
        string='Peso Lámina Calculado (kg)',
        compute='_compute_peso_lamina_calculado',
        store=True,
        help='Peso de la lámina: metros_lineales_calculados * ancho_calculado * gramaje_total / 1000000'
    )

    peso_consumo_li = fields.Float(
        string='Peso Consumo LI (kg)',
        compute='_compute_peso_consumo_li',
        store=True,
        help='Consumo Liner Interno: metros_lineales * ancho_calculado * gramaje_li / 1000000'
    )

    peso_consumo_cm = fields.Float(
        string='Peso Consumo CM (kg)',
        compute='_compute_peso_consumo_cm',
        store=True,
        help='Consumo Corrugado Medium: metros_lineales * ancho_calculado * gramaje_cm / 1000000'
    )

    peso_consumo_le = fields.Float(
        string='Peso Consumo LE (kg)',
        compute='_compute_peso_consumo_le',
        store=True,
        help='Consumo Liner Externo: metros_lineales * ancho_calculado * gramaje_le / 1000000'
    )

    cumplimiento_calculado = fields.Selection([
        ('a_tiempo', 'A Tiempo'),
        ('retrasado', 'Retrasado'),
        ('adelantado', 'Adelantado'),
        ('pendiente', 'Pendiente')
    ], string='Cumplimiento Calculado',
       compute='_compute_cumplimiento_calculado',
       store=True,
       help='Cumplimiento calculado basado en fechas de producción y entrega')

    # Fechas y estado
    fecha_entrega_cliente = fields.Date(string='Fecha Entrega Cliente')
    fecha_produccion = fields.Date(string='Fecha Producción')
    estado = fields.Selection([
        ('pendiente', 'Pendiente'),
        ('ot', 'OT'),
        ('planchas', 'Planchas'),
        ('entregado', 'Entregado'),
        ('proceso', 'En Proceso'),
    ], string='Estado', default='pendiente')
    cumplimiento = fields.Char(string='Cumplimiento')
    
    # Especificaciones de materiales - Liner Interno
    liner_interno_proveedor = fields.Char(string='Liner Interno - Proveedor')
    liner_interno_ancho = fields.Float(string='Liner Interno - Ancho')
    liner_interno_gm = fields.Float(string='Liner Interno - GM')
    liner_interno_tipo = fields.Char(string='Liner Interno - Tipo')
    
    # Especificaciones de materiales - Medium
    medium_proveedor = fields.Char(string='Medium - Proveedor')
    medium_ancho = fields.Float(string='Medium - Ancho')
    medium_gm = fields.Float(string='Medium - GM')
    medium_tipo = fields.Char(string='Medium - Tipo')
    
    # Especificaciones de materiales - Liner Externo
    liner_externo_proveedor = fields.Char(string='Liner Externo - Proveedor')
    liner_externo_ancho = fields.Float(string='Liner Externo - Ancho')
    liner_externo_gm = fields.Float(string='Liner Externo - GM')
    liner_externo_tipo = fields.Char(string='Liner Externo - Tipo')
    
    # Cortes y medidas
    cortes = fields.Integer(string='Cortes', compute='_compute_cortes', store=True)
    metros_lineales = fields.Float(string='Metros Lineales', compute='_compute_metros_lineales', store=True)
    
    # Cantidades de material
    cantidad_liner_interno = fields.Float(string='Cantidad Liner Interno', compute='_compute_cantidad_liner_interno', store=True)
    cantidad_medium = fields.Float(string='Cantidad Medium', compute='_compute_cantidad_medium', store=True)
    cantidad_liner_externo = fields.Float(string='Cantidad Liner Externo', compute='_compute_cantidad_liner_externo', store=True)
    
    # Troquel y especificaciones técnicas
    numero_troquel = fields.Char(string='Número de Troquel', compute='_compute_numero_troquel', store=True)
    ect_minimo = fields.Float(string='ECT Mínimo')
    ect_real = fields.Float(string='ECT Real')
    peso = fields.Float(string='Peso')
    
    # Cantidad entregada
    cantidad_entregada = fields.Integer(string='Cantidad Entregada')
    
    # Campos de planificación
    grupo_planificacion = fields.Char(string='Grupo de Planificación', help='Grupo asignado por el algoritmo de optimización')
    tipo_combinacion = fields.Selection([
        ('individual', 'Individual'),
        ('dupla', 'Dupla'),
    ], string='Tipo de Combinación', default='individual')
    ancho_utilizado = fields.Float(string='Ancho Utilizado (mm)', help='Ancho total utilizado en la bobina', group_operator='max')
    bobina_utilizada = fields.Float(string='Bobina Utilizada (mm)', help='Ancho de bobina utilizada', group_operator='max')
    sobrante = fields.Float(string='Sobrante (mm)', help='Material sobrante después del corte')
    eficiencia = fields.Float(string='Eficiencia (%)', help='Porcentaje de eficiencia del material calculado con algoritmo avanzado', group_operator='avg')
    metros_lineales_planificados = fields.Float(string='Metros Lineales Planificados', help='Metros lineales calculados para la planificación')
    cortes_planificados = fields.Integer(string='Cortes Planificados', help='Total de cortes calculados en la planificación')
    cantidad_planificada = fields.Integer(string='Cantidad Planificada', help='Cantidad que se producirá según la planificación: cortes_planificados * cavidad_efectiva')
    cavidad_optimizada = fields.Integer(string='Cavidad Optimizada', help='Multiplicador de cavidad óptimo encontrado por el algoritmo de optimización', group_operator='max')
    
    # Test calculado automáticamente desde descripción del producto
    test_name = fields.Char(
        string='TEST',
        compute='_compute_test_from_description',
        store=True,
        help='Test extraído automáticamente de la descripción del producto'
    )

    test_id = fields.Many2one(
        'megastock.paper.recipe',
        string='Test/Receta',
        compute='_compute_test_id_from_name',
        store=True,
        help='Relación con test de resistencia y receta de papel'
    )

    # Relación con orden de trabajo
    work_order_id = fields.Many2one('megastock.work.order', string='Orden de Trabajo')
    
    # Campos calculados
    area_total = fields.Float(string='Área Total (m²)', compute='_compute_area_total', store=True)
    porcentaje_cumplimiento = fields.Float(string='% Cumplimiento', compute='_compute_porcentaje_cumplimiento', store=True)
    
    @api.depends('largo', 'ancho', 'cantidad')
    def _compute_area_total(self):
        for record in self:
            if record.largo and record.ancho and record.cantidad:
                # Convertir de mm² a m²
                area_unitaria = (record.largo * record.ancho) / 1000000
                record.area_total = area_unitaria * record.cantidad
            else:
                record.area_total = 0.0
    
    @api.depends('cantidad', 'cantidad_entregada')
    def _compute_porcentaje_cumplimiento(self):
        for record in self:
            if record.cantidad and record.cantidad > 0:
                record.porcentaje_cumplimiento = (record.cantidad_entregada / record.cantidad) * 100
            else:
                record.porcentaje_cumplimiento = 0.0

    @api.depends('descripcion')
    def _compute_test_from_description(self):
        """Extrae el número de test de la descripción del producto"""
        import re
        for record in self:
            test_name = ''
            if record.descripcion:
                # Buscar patrones como "TEST 200", "Test 150", etc.
                match = re.search(r'TEST\s+(\d+)', record.descripcion.upper())
                if match:
                    test_number = match.group(1)
                    test_name = test_number  # Solo el número, sin "Test"
            record.test_name = test_name

    @api.depends('test_name')
    def _compute_test_id_from_name(self):
        """Busca la relación con el test basado en test_name"""
        for record in self:
            test_id = False
            if record.test_name:
                try:
                    # Buscar el test en megastock.paper.recipe si existe
                    if 'megastock.paper.recipe' in self.env:
                        # Convertir número a formato "Test XXX" para búsqueda
                        test_search_name = f"Test {record.test_name}"
                        test = self.env['megastock.paper.recipe'].search([
                            ('test_name', '=', test_search_name)
                        ], limit=1)
                        if test:
                            test_id = test.id
                except KeyError:
                    # Modelo no existe aún, mantener test_id como False
                    pass
            record.test_id = test_id

    def action_recalcular_test(self):
        """Acción para recalcular test desde interfaz"""
        for record in self:
            record._compute_test_from_description()
        return True

    @api.depends('alto')
    def _compute_largo_rayado(self):
        """Calcula largo rayado según fórmula: alto + 2"""
        for record in self:
            if record.alto:
                record.largo_rayado = record.alto + 2
            else:
                record.largo_rayado = 2.0  # Valor por defecto si alto es 0

    @api.depends('alto')
    def _compute_alto_rayado(self):
        """Calcula alto rayado según fórmula: alto + 2"""
        for record in self:
            if record.alto:
                record.alto_rayado = record.alto + 2
            else:
                record.alto_rayado = 2.0  # Valor por defecto si alto es 0

    @api.depends('ancho_calculado', 'alto_rayado')
    def _compute_ancho_rayado(self):
        """Calcula ancho rayado según fórmula: ancho_calculado - (alto_rayado * 2)"""
        for record in self:
            if record.ancho_calculado and record.alto_rayado:
                record.ancho_rayado = record.ancho_calculado - (record.alto_rayado * 2)
            else:
                record.ancho_rayado = 0.0

    @api.depends('largo', 'alto')
    def _compute_largo_calculado(self):
        """Calcula largo real según fórmula: 2*alto + largo + 8"""
        for record in self:
            if record.largo and record.alto:
                record.largo_calculado = (2 * record.alto) + record.largo + 8
            else:
                record.largo_calculado = record.largo or 0

    @api.depends('ancho', 'alto', 'troquel')
    def _compute_ancho_calculado(self):
        """Calcula ancho real según fórmula: 2*alto + ancho + 14 + (2 si troquel=SI)"""
        for record in self:
            if record.ancho and record.alto:
                base_ancho = (2 * record.alto) + record.ancho + 14
                # Agregar 2mm si troquel = 'si'
                troquel_extra = 2 if record.troquel == 'si' else 0
                record.ancho_calculado = base_ancho + troquel_extra
            else:
                record.ancho_calculado = record.ancho or 0

    @api.depends('cantidad', 'cavidad')
    def _compute_cantidad_ajustada(self):
        """Optimiza cantidad según cavidad: ceil(cantidad/cavidad) * cavidad"""
        for record in self:
            if record.cantidad and record.cavidad and record.cavidad > 0:
                cortes_necesarios = math.ceil(record.cantidad / record.cavidad)
                record.cantidad_ajustada = cortes_necesarios * record.cavidad
            else:
                record.cantidad_ajustada = record.cantidad or 0

    @api.depends('cantidad_ajustada', 'largo_calculado', 'cavidad')
    def _compute_metros_lineales_calculados(self):
        """Calcula metros lineales: ((cantidad_ajustada * largo_calculado) / cavidad) / 1000"""
        for record in self:
            if record.cantidad_ajustada and record.largo_calculado and record.cavidad and record.cavidad > 0:
                metros = ((record.cantidad_ajustada * record.largo_calculado) / record.cavidad) / 1000
                record.metros_lineales_calculados = metros
            else:
                record.metros_lineales_calculados = 0

    @api.depends('largo_calculado', 'ancho_calculado', 'test_name')
    def _compute_peso_lamina_calculado(self):
        """Calcula peso usando motor de cálculo"""
        calculator = self.env['megastock.weight.calculator']
        for record in self:
            if record.largo_calculado and record.ancho_calculado and record.test_name:
                try:
                    # Convertir test_name a float (ej: "275" -> 275.0)
                    test_value = float(record.test_name) if record.test_name else 200.0
                    record.peso_lamina_calculado = calculator.calculate_sheet_weight(
                        record.largo_calculado,
                        record.ancho_calculado,
                        test_value
                    )
                except (ValueError, TypeError):
                    # Si no se puede convertir, usar valor por defecto
                    record.peso_lamina_calculado = calculator.calculate_sheet_weight(
                        record.largo_calculado,
                        record.ancho_calculado,
                        200.0
                    )
            else:
                record.peso_lamina_calculado = 0

    @api.depends('metros_lineales_calculados', 'ancho_calculado', 'liner_interno_gm')
    def _compute_peso_consumo_li(self):
        """Calcula consumo de Liner Interno: metros_lineales * ancho_calculado * gramaje_li / 1000000"""
        for record in self:
            if record.metros_lineales_calculados and record.ancho_calculado and record.liner_interno_gm:
                peso = (record.metros_lineales_calculados * record.ancho_calculado * record.liner_interno_gm) / 1000000
                record.peso_consumo_li = peso
            else:
                record.peso_consumo_li = 0

    @api.depends('metros_lineales_calculados', 'ancho_calculado', 'medium_gm')
    def _compute_peso_consumo_cm(self):
        """Calcula consumo de Corrugado Medium: metros_lineales * ancho_calculado * gramaje_cm / 1000000"""
        for record in self:
            if record.metros_lineales_calculados and record.ancho_calculado and record.medium_gm:
                peso = (record.metros_lineales_calculados * record.ancho_calculado * record.medium_gm) / 1000000
                record.peso_consumo_cm = peso
            else:
                record.peso_consumo_cm = 0

    @api.depends('metros_lineales_calculados', 'ancho_calculado', 'liner_externo_gm')
    def _compute_peso_consumo_le(self):
        """Calcula consumo de Liner Externo: metros_lineales * ancho_calculado * gramaje_le / 1000000"""
        for record in self:
            if record.metros_lineales_calculados and record.ancho_calculado and record.liner_externo_gm:
                peso = (record.metros_lineales_calculados * record.ancho_calculado * record.liner_externo_gm) / 1000000
                record.peso_consumo_le = peso
            else:
                record.peso_consumo_le = 0

    @api.depends('fecha_produccion', 'fecha_entrega_cliente', 'estado')
    def _compute_cumplimiento_calculado(self):
        """Calcula cumplimiento basado en fechas de producción y entrega"""
        from datetime import date
        for record in self:
            if not record.fecha_entrega_cliente:
                record.cumplimiento_calculado = 'pendiente'
            elif record.estado == 'entregado':
                if record.fecha_produccion:
                    if record.fecha_produccion <= record.fecha_entrega_cliente:
                        record.cumplimiento_calculado = 'a_tiempo'
                    else:
                        record.cumplimiento_calculado = 'retrasado'
                else:
                    record.cumplimiento_calculado = 'a_tiempo'  # Entregado sin fecha de producción
            elif record.estado in ['pendiente', 'ot', 'proceso', 'planchas']:
                today = date.today()
                if today <= record.fecha_entrega_cliente:
                    record.cumplimiento_calculado = 'pendiente'
                else:
                    record.cumplimiento_calculado = 'retrasado'
            else:
                record.cumplimiento_calculado = 'pendiente'

    @api.depends('cantidad', 'cavidad')
    def _compute_cortes(self):
        for record in self:
            if record.cavidad and record.cavidad > 0:
                record.cortes = int(record.cantidad / record.cavidad)
            else:
                record.cortes = 0
    
    @api.depends('cortes', 'largo')
    def _compute_metros_lineales(self):
        for record in self:
            if record.cortes and record.largo:
                record.metros_lineales = (record.cortes * record.largo) / 1000
            else:
                record.metros_lineales = 0.0
    
    @api.onchange('cantidad', 'cavidad')
    def _onchange_cantidad_cavidad(self):
        """Actualizar cortes cuando cambie cantidad o cavidad"""
        if self.cavidad and self.cavidad > 0:
            self.cortes = int(self.cantidad / self.cavidad)
        else:
            self.cortes = 0
    
    @api.depends('liner_interno_ancho', 'liner_interno_gm', 'metros_lineales')
    def _compute_cantidad_liner_interno(self):
        for record in self:
            if record.liner_interno_ancho and record.liner_interno_gm and record.metros_lineales:
                record.cantidad_liner_interno = (record.liner_interno_ancho * record.liner_interno_gm) * (record.metros_lineales / 1000000)
            else:
                record.cantidad_liner_interno = 0.0
    
    @api.depends('medium_ancho', 'medium_gm', 'metros_lineales')
    def _compute_cantidad_medium(self):
        for record in self:
            if record.medium_ancho and record.medium_gm and record.metros_lineales:
                record.cantidad_medium = (record.medium_ancho * record.medium_gm) * (record.metros_lineales / 1000000) * 1.45
            else:
                record.cantidad_medium = 0.0
    
    @api.depends('liner_externo_ancho', 'liner_externo_gm', 'metros_lineales')
    def _compute_cantidad_liner_externo(self):
        for record in self:
            if record.liner_externo_ancho and record.liner_externo_gm and record.metros_lineales:
                record.cantidad_liner_externo = (record.liner_externo_ancho * record.liner_externo_gm) * (record.metros_lineales / 1000000)
            else:
                record.cantidad_liner_externo = 0.0
    
    @api.onchange('cortes', 'largo')
    def _onchange_cortes_largo(self):
        """Actualizar metros lineales cuando cambie cortes o largo"""
        if self.cortes and self.largo:
            self.metros_lineales = (self.cortes * self.largo) / 1000
        else:
            self.metros_lineales = 0.0
    
    @api.onchange('liner_interno_ancho', 'liner_interno_gm', 'metros_lineales')
    def _onchange_liner_interno(self):
        """Actualizar cantidad liner interno cuando cambien sus parámetros"""
        if self.liner_interno_ancho and self.liner_interno_gm and self.metros_lineales:
            self.cantidad_liner_interno = (self.liner_interno_ancho * self.liner_interno_gm) * (self.metros_lineales / 1000000)
        else:
            self.cantidad_liner_interno = 0.0
    
    @api.onchange('medium_ancho', 'medium_gm', 'metros_lineales')
    def _onchange_medium(self):
        """Actualizar cantidad medium cuando cambien sus parámetros"""
        if self.medium_ancho and self.medium_gm and self.metros_lineales:
            self.cantidad_medium = (self.medium_ancho * self.medium_gm) * (self.metros_lineales / 1000000) * 1.45
        else:
            self.cantidad_medium = 0.0
    
    @api.depends('codigo')
    def _compute_numero_troquel(self):
        for record in self:
            if record.codigo:
                product = self.env['product.template'].search([
                    ('default_code', '=', record.codigo)
                ], limit=1)
                if product and 'numero_troquel' in product._fields:
                    record.numero_troquel = product.numero_troquel or ''
                else:
                    record.numero_troquel = ''
            else:
                record.numero_troquel = ''
    
    @api.onchange('liner_externo_ancho', 'liner_externo_gm', 'metros_lineales')
    def _onchange_liner_externo(self):
        """Actualizar cantidad liner externo cuando cambien sus parámetros"""
        if self.liner_externo_ancho and self.liner_externo_gm and self.metros_lineales:
            self.cantidad_liner_externo = (self.liner_externo_ancho * self.liner_externo_gm) * (self.metros_lineales / 1000000)
        else:
            self.cantidad_liner_externo = 0.0
    
    @api.onchange('codigo')
    def _onchange_codigo(self):
        """Actualizar numero_troquel cuando cambie el código"""
        if self.codigo:
            product = self.env['product.template'].search([
                ('default_code', '=', self.codigo)
            ], limit=1)
            if product and 'numero_troquel' in product._fields:
                self.numero_troquel = product.numero_troquel or ''
            else:
                self.numero_troquel = ''
        else:
            self.numero_troquel = ''
    
    def name_get(self):
        result = []
        for record in self:
            if record.orden_produccion:
                name = f"{record.orden_produccion} - {record.cliente}"
            else:
                name = f"{record.cliente}"
            if record.descripcion:
                name += f" ({record.descripcion[:50]}...)" if len(record.descripcion) > 50 else f" ({record.descripcion})"
            result.append((record.id, name))
        return result

    def action_planificar_ordenes(self):
        """Acción para planificar órdenes pendientes optimizando el uso de material"""
        # Buscar todas las órdenes pendientes
        ordenes_pendientes = self.search([('estado', '=', 'pendiente')])
        
        if not ordenes_pendientes:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Sin órdenes pendientes',
                    'message': 'No hay órdenes pendientes para planificar.',
                    'type': 'warning',
                }
            }
        
        # Ejecutar algoritmo de optimización
        resultado = self._optimizar_ordenes(ordenes_pendientes)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Planificación completada',
                'message': f'Se han planificado {len(ordenes_pendientes)} órdenes en {resultado["grupos"]} grupos. Eficiencia promedio: {resultado["eficiencia_promedio"]:.1f}%',
                'type': 'success',
            }
        }

    def _optimizar_ordenes(self, ordenes, test_principal=None, cavidad_limite=1, bobina_unica=False):
        """Algoritmo de optimización basado en el archivo Excel de trimado

        Args:
            ordenes: Recordset de órdenes a optimizar
            test_principal: Número de test principal para la producción
            cavidad_limite: Límite superior para multiplicar ancho_calculado (default: 1)
            bobina_unica: Si True, todos los grupos usan una sola bobina (default: False)
        """
        from odoo.exceptions import UserError

        # Obtener anchos de bobina disponibles desde la configuración
        Bobina = self.env['megastock.bobina']
        bobinas_disponibles = Bobina.get_bobinas_activas()

        # Si no hay bobinas configuradas, mostrar error
        if not bobinas_disponibles:
            raise UserError(
                "No hay bobinas activas configuradas. "
                "Ve a Configuración > Bobinas y configura al menos una bobina activa."
            )

        # ESTRATEGIA 1: BOBINA ÚNICA - Todos los grupos usan la misma bobina
        if bobina_unica:
            mejor_bobina = None
            menor_desperdicio_total = float('inf')
            mejores_grupos = None

            for bobina_candidata in bobinas_disponibles:
                # Optimizar todas las órdenes usando solo esta bobina
                grupos_con_esta_bobina = []
                ordenes_procesadas = set()
                grupo_counter = 1
                desperdicio_total = 0

                for orden in ordenes:
                    if orden.id in ordenes_procesadas:
                        continue

                    # Buscar mejor combinación SOLO con esta bobina específica
                    mejor_combinacion = self._encontrar_mejor_combinacion(
                        orden, ordenes, ordenes_procesadas, [bobina_candidata], cavidad_limite
                    )

                    if mejor_combinacion:
                        grupos_con_esta_bobina.append(mejor_combinacion)
                        desperdicio_total += mejor_combinacion['sobrante']

                        # Marcar órdenes como procesadas
                        for orden_comb_data in mejor_combinacion['ordenes']:
                            ordenes_procesadas.add(orden_comb_data['orden'].id)

                        grupo_counter += 1
                    else:
                        # CRÍTICO: Si una orden no cabe en esta bobina, penalizar mucho
                        # Esto asegura que bobinas pequeñas no sean elegidas si no procesan todas las órdenes
                        desperdicio_total += 999999  # Penalización enorme

                # Verificar si esta bobina es mejor que las anteriores
                # Solo si procesa TODAS las órdenes (sin penalización)
                if desperdicio_total < menor_desperdicio_total:
                    menor_desperdicio_total = desperdicio_total
                    mejor_bobina = bobina_candidata
                    mejores_grupos = grupos_con_esta_bobina

            # Aplicar los mejores grupos encontrados
            if mejores_grupos:
                for idx, grupo in enumerate(mejores_grupos, start=1):
                    self._aplicar_combinacion(grupo, idx)

            # Calcular estadísticas
            eficiencia_total = sum(grupo['eficiencia'] for grupo in mejores_grupos) if mejores_grupos else 0
            eficiencia_promedio = eficiencia_total / len(mejores_grupos) if mejores_grupos else 0

            return {
                'grupos': len(mejores_grupos) if mejores_grupos else 0,
                'eficiencia_promedio': eficiencia_promedio,
                'bobina_optima': mejor_bobina,
                'desperdicio_total': menor_desperdicio_total
            }

        # ESTRATEGIA 2: BOBINAS MÚLTIPLES - Cada grupo elige su mejor bobina
        else:
            grupos_optimizados = []
            ordenes_procesadas = set()
            grupo_counter = 1

            for orden in ordenes:
                if orden.id in ordenes_procesadas:
                    continue

                # Buscar mejor combinación considerando TODAS las bobinas disponibles
                # La función _encontrar_mejor_combinacion ya elige la bobina óptima para este grupo
                mejor_combinacion = self._encontrar_mejor_combinacion(
                    orden, ordenes, ordenes_procesadas, bobinas_disponibles, cavidad_limite
                )

                if mejor_combinacion:
                    grupos_optimizados.append(mejor_combinacion)

                    # Marcar órdenes como procesadas
                    for orden_comb_data in mejor_combinacion['ordenes']:
                        ordenes_procesadas.add(orden_comb_data['orden'].id)

                    grupo_counter += 1

            # Aplicar los grupos encontrados
            if grupos_optimizados:
                for idx, grupo in enumerate(grupos_optimizados, start=1):
                    self._aplicar_combinacion(grupo, idx)

            # Calcular estadísticas
            eficiencia_total = sum(grupo['eficiencia'] for grupo in grupos_optimizados) if grupos_optimizados else 0
            eficiencia_promedio = eficiencia_total / len(grupos_optimizados) if grupos_optimizados else 0
            desperdicio_total = sum(grupo['sobrante'] for grupo in grupos_optimizados) if grupos_optimizados else 0

            return {
                'grupos': len(grupos_optimizados) if grupos_optimizados else 0,
                'eficiencia_promedio': eficiencia_promedio,
                'desperdicio_total': desperdicio_total
            }

    def _encontrar_mejor_combinacion(self, orden_principal, todas_ordenes, procesadas, bobinas, cavidad_limite=1):
        """Encuentra la mejor combinación para una orden principal

        Args:
            orden_principal: Orden principal a optimizar
            todas_ordenes: Todas las órdenes disponibles
            procesadas: Set de IDs de órdenes ya procesadas
            bobinas: Lista de anchos de bobinas disponibles
            cavidad_limite: Límite superior para multiplicar ancho_calculado
        """
        mejor_combinacion = None
        menor_sobrante = float('inf')  # Criterio único: minimizar sobrante

        # Margen de seguridad para cortes (30mm)
        MARGEN_SEGURIDAD = 30

        # Probar combinaciones individuales con diferentes multiplicadores de cavidad
        for multiplicador in range(1, cavidad_limite + 1):
            ancho_util = orden_principal.ancho_calculado * multiplicador

            for bobina in bobinas:
                if ancho_util <= (bobina - MARGEN_SEGURIDAD):
                    # Crear datos de orden con multiplicador
                    orden_data = [{
                        'orden': orden_principal,
                        'multiplicador': multiplicador,
                        'ancho_efectivo': ancho_util
                    }]

                    resultado = self._calcular_eficiencia_real_con_cavidad(orden_data, bobina)

                    # Criterio simple: menor sobrante gana
                    if resultado['sobrante'] < menor_sobrante:
                        menor_sobrante = resultado['sobrante']
                        mejor_combinacion = {
                            'ordenes': orden_data,
                            'tipo': 'individual',
                            'bobina': bobina,
                            'ancho_utilizado': ancho_util,
                            'sobrante': resultado['sobrante'],
                            'eficiencia': resultado['eficiencia'],
                            'metros_lineales': resultado['metros_lineales'],
                            'cortes_totales': resultado['cortes_totales']
                        }

        # Probar duplas con diferentes multiplicadores de cavidad para cada orden
        for orden2 in todas_ordenes:
            if orden2.id == orden_principal.id or orden2.id in procesadas:
                continue

            # Probar todas las combinaciones de multiplicadores para ambas órdenes
            for mult1 in range(1, cavidad_limite + 1):
                for mult2 in range(1, cavidad_limite + 1):
                    ancho1 = orden_principal.ancho_calculado * mult1
                    ancho2 = orden2.ancho_calculado * mult2
                    ancho_total = ancho1 + ancho2

                    for bobina in bobinas:
                        if ancho_total <= (bobina - MARGEN_SEGURIDAD):
                            # Crear datos de órdenes con multiplicadores
                            ordenes_data = [
                                {
                                    'orden': orden_principal,
                                    'multiplicador': mult1,
                                    'ancho_efectivo': ancho1
                                },
                                {
                                    'orden': orden2,
                                    'multiplicador': mult2,
                                    'ancho_efectivo': ancho2
                                }
                            ]

                            resultado = self._calcular_eficiencia_real_con_cavidad(ordenes_data, bobina)

                            # Criterio simple: menor sobrante gana
                            if resultado['sobrante'] < menor_sobrante:
                                menor_sobrante = resultado['sobrante']
                                mejor_combinacion = {
                                    'ordenes': ordenes_data,
                                    'tipo': 'dupla',
                                    'bobina': bobina,
                                    'ancho_utilizado': ancho_total,
                                    'sobrante': resultado['sobrante'],
                                    'eficiencia': resultado['eficiencia'],
                                    'metros_lineales': resultado['metros_lineales'],
                                    'cortes_totales': resultado['cortes_totales']
                                }

        # Las triplas no son posibles debido a limitaciones de las máquinas corrugadoras
        # que solo tienen máximo 2 cuchillas

        return mejor_combinacion

    def _calcular_eficiencia_real_con_cavidad(self, ordenes_data, bobina_ancho):
        """Calcula la eficiencia y sobrante para una combinación de órdenes

        Args:
            ordenes_data: Lista de diccionarios con estructura:
                         [{'orden': record, 'multiplicador': int, 'ancho_efectivo': float}, ...]
            bobina_ancho: Ancho de la bobina en mm

        Returns:
            dict con eficiencia, sobrante, metros_lineales, cortes_totales
        """
        # Calcular totales usando anchos efectivos (ancho_calculado * multiplicador)
        ancho_total_utilizado = sum(data['ancho_efectivo'] for data in ordenes_data)

        # Verificar que las órdenes caben en la bobina
        if ancho_total_utilizado > bobina_ancho:
            return {
                'eficiencia': 0,
                'sobrante': bobina_ancho,
                'metros_lineales': 0,
                'cortes_totales': 0
            }

        # NUEVA FÓRMULA DE SOBRANTE:
        # Distribuir equitativamente la bobina entre las órdenes del grupo
        # sobrante_individual = ((bobina - 30) / num_ordenes) - ancho_calculado
        # sobrante_grupo = suma de todos los sobrantes individuales

        MARGEN_SEGURIDAD = 30
        num_ordenes = len(ordenes_data)
        espacio_por_orden = (bobina_ancho - MARGEN_SEGURIDAD) / num_ordenes

        sobrante_ancho = 0
        for data in ordenes_data:
            # ancho_efectivo ya incluye el multiplicador
            sobrante_individual = espacio_por_orden - data['ancho_efectivo']
            sobrante_ancho += sobrante_individual

        # Calcular eficiencia: porcentaje de bobina utilizado
        eficiencia = (ancho_total_utilizado / bobina_ancho) * 100

        # Calcular metros lineales y cortes totales
        metros_lineales = 0
        cortes_totales = 0

        for data in ordenes_data:
            orden = data['orden']
            multiplicador = data['multiplicador']

            if orden.cavidad and orden.cavidad > 0:
                # La cavidad efectiva se multiplica por el multiplicador
                cavidad_efectiva = orden.cavidad * multiplicador
                cortes_necesarios = orden.cantidad / cavidad_efectiva
                metros_por_orden = (cortes_necesarios * orden.largo_calculado) / 1000  # mm a metros
                metros_lineales += metros_por_orden
                cortes_totales += cortes_necesarios

        return {
            'eficiencia': eficiencia,
            'sobrante': sobrante_ancho,
            'metros_lineales': metros_lineales,
            'cortes_totales': cortes_totales
        }

    def _calcular_eficiencia_real(self, ordenes, bobina_ancho):
        """Calcula la eficiencia real basada en el algoritmo del Excel de trimado"""
        # Calcular totales de las órdenes usando ancho_calculado
        ancho_total_utilizado = sum(orden.ancho_calculado for orden in ordenes)
        cantidad_total = sum(orden.cantidad for orden in ordenes)
        cortes_totales = sum(orden.cortes for orden in ordenes)

        # Verificar que las órdenes caben en la bobina
        if ancho_total_utilizado > bobina_ancho:
            return {
                'eficiencia': 0,
                'sobrante': bobina_ancho,
                'metros_lineales': 0,
                'cortes_totales': 0
            }

        # Calcular sobrante en ancho
        sobrante_ancho = bobina_ancho - ancho_total_utilizado

        # Calcular metros lineales necesarios usando largo_calculado
        # Basado en la fórmula del Excel: cantidad / cavidad * largo_calculado (convertido a metros)
        metros_lineales = 0
        for orden in ordenes:
            if orden.cavidad and orden.cavidad > 0:
                cortes_necesarios = orden.cantidad / orden.cavidad
                metros_por_orden = (cortes_necesarios * orden.largo_calculado) / 1000  # mm a metros
                metros_lineales += metros_por_orden

        # Calcular eficiencia base (aprovechamiento de la bobina)
        eficiencia_base = (ancho_total_utilizado / bobina_ancho) * 100

        # Aplicar ajustes aditivos (no multiplicativos)
        eficiencia_final = eficiencia_base

        # Eficiencia base sin bonificaciones artificiales
        # Fórmula correcta según especificaciones: (ANCHO_TOTAL_UTILIZADO / BOBINA_UTILIZADA) * 100

        # Factor 2: Bonus por cavidades múltiples
        for orden in ordenes:
            if orden.cavidad and orden.cavidad > 1:
                eficiencia_final += min((orden.cavidad - 1) * 2, 10)  # Max +10%

        # Factor 3: Penalización por sobrante excesivo
        porcentaje_sobrante = (sobrante_ancho / bobina_ancho) * 100
        if porcentaje_sobrante > 30:  # Si el sobrante es > 30%
            penalizacion = (porcentaje_sobrante - 30) * 0.5
            eficiencia_final -= penalizacion

        # Limitar entre 0 y 100
        eficiencia_final = max(0, min(100, eficiencia_final))

        return {
            'eficiencia': eficiencia_final,
            'sobrante': sobrante_ancho,
            'metros_lineales': metros_lineales,
            'cortes_totales': cortes_totales
        }

    def _aplicar_combinacion(self, combinacion, grupo_id):
        """Aplica la combinación encontrada a las órdenes

        Args:
            combinacion: dict con la estructura de la combinación óptima
            grupo_id: ID del grupo de planificación
        """
        grupo_nombre = f"GRUPO-{grupo_id:03d}"

        # Calcular sobrante individual para cada orden
        MARGEN_SEGURIDAD = 30
        num_ordenes = len(combinacion['ordenes'])
        espacio_por_orden = (combinacion['bobina'] - MARGEN_SEGURIDAD) / num_ordenes

        for orden_data in combinacion['ordenes']:
            orden = orden_data['orden']
            multiplicador = orden_data.get('multiplicador', 1)
            ancho_efectivo = orden_data.get('ancho_efectivo', orden.ancho_calculado)

            # Calcular sobrante individual de esta orden
            sobrante_individual = espacio_por_orden - ancho_efectivo

            # Calcular valores de planificación según especificaciones:
            # cavidad_efectiva = cavidad * multiplicador
            cavidad_efectiva = orden.cavidad * multiplicador if orden.cavidad else multiplicador

            # 1. cortes_planificados = cantidad / cavidad_efectiva
            cortes_planificados = int(orden.cantidad / cavidad_efectiva) if cavidad_efectiva > 0 else 0

            # 2. cantidad_planificada = cortes_planificados * cavidad_efectiva
            cantidad_planificada = cortes_planificados * cavidad_efectiva

            # 3. metros_lineales_planificados = ((cantidad_planificada * largo_calculado) / cavidad_efectiva) / 1000
            metros_lineales_planificados = 0
            if cavidad_efectiva > 0 and orden.largo_calculado:
                metros_lineales_planificados = ((cantidad_planificada * orden.largo_calculado) / cavidad_efectiva) / 1000

            orden.write({
                'grupo_planificacion': grupo_nombre,
                'tipo_combinacion': combinacion['tipo'],
                'ancho_utilizado': combinacion['ancho_utilizado'],
                'bobina_utilizada': combinacion['bobina'],
                'sobrante': sobrante_individual,  # Sobrante individual, no del grupo
                'eficiencia': combinacion['eficiencia'],
                'metros_lineales_planificados': metros_lineales_planificados,
                'cortes_planificados': cortes_planificados,
                'cantidad_planificada': cantidad_planificada,
                # Guardar el multiplicador de cavidad óptimo
                'cavidad_optimizada': multiplicador,
            })

    def action_generar_ordenes_trabajo(self):
        """Acción para abrir wizard de generación de órdenes de trabajo"""
        # Abrir el wizard para que el usuario especifique si requiere doblez
        return {
            'type': 'ir.actions.act_window',
            'name': 'Generar Órdenes de Trabajo',
            'res_model': 'megastock.generar.ordenes.wizard',
            'view_mode': 'form',
            'target': 'new',
        }

    def action_resetear_agrupaciones(self):
        """Resetea las agrupaciones de las órdenes seleccionadas para poder replanificar"""
        # Verificar que haya órdenes seleccionadas
        if not self:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Sin órdenes seleccionadas',
                    'message': 'Selecciona las órdenes que deseas resetear.',
                    'type': 'warning',
                }
            }

        # Filtrar órdenes que están planificadas pero NO tienen orden de trabajo
        ordenes_reseteable = self.filtered(lambda r: r.grupo_planificacion and not r.work_order_id)

        if not ordenes_reseteable:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Sin órdenes válidas',
                    'message': 'Solo se pueden resetear órdenes planificadas que NO tengan orden de trabajo asignada.',
                    'type': 'warning',
                }
            }

        # Resetear campos de planificación y estado
        ordenes_reseteable.write({
            'grupo_planificacion': False,
            'tipo_combinacion': 'individual',
            'ancho_utilizado': 0,
            'bobina_utilizada': 0,
            'sobrante': 0,
            'eficiencia': 0,
            'metros_lineales_planificados': 0,
            'cortes_planificados': 0,
            'cantidad_planificada': 0,
            'cavidad_optimizada': 0,
            'estado': 'pendiente',  # Volver a estado pendiente
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Agrupaciones reseteadas',
                'message': f'Se han reseteado {len(ordenes_reseteable)} órdenes. Ahora están listas para planificar nuevamente.',
                'type': 'success',
            }
        }
