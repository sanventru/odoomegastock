# -*- coding: utf-8 -*-
#calculos
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

    over_superior = fields.Float(string='Over Superior', help='Valor de over superior')
    over_inferior = fields.Float(string='Over Inferior', help='Valor de over inferior')

    solapa = fields.Float(
        string='Solapa (mm)',
        compute='_compute_solapa',
        store=True,
        help='Solapa calculada: (ancho / 2) + compensación de ancho de la flauta'
    )

    a1 = fields.Float(
        string='A1 (mm)',
        compute='_compute_a1',
        store=True,
        help='A1 calculado: (ancho / 2) + (over_superior / 2) + compensación de ancho de la flauta'
    )

    a2 = fields.Float(
        string='A2 (mm)',
        compute='_compute_a2',
        store=True,
        help='A2 calculado: alto + compensación de alto de la flauta'
    )

    a3 = fields.Float(
        string='A3 (mm)',
        compute='_compute_a3',
        store=True,
        help='A3 calculado: (ancho / 2) + (over_superior / 2) + compensación de ancho de la flauta'
    )

    # Índices de flauta
    alto_indice_flauta = fields.Float(
        string='Alto (Índice Flauta) (mm)',
        compute='_compute_alto_indice_flauta',
        store=True,
        help='Alto del pedido + compensación de alto de la flauta'
    )

    ancho_indice_flauta = fields.Float(
        string='Ancho (Índice Flauta) (mm)',
        compute='_compute_ancho_indice_flauta',
        store=True,
        help='Ancho del pedido + compensación de ancho de la flauta'
    )

    largo_indice_flauta = fields.Float(
        string='Largo (Índice Flauta) (mm)',
        compute='_compute_largo_indice_flauta',
        store=True,
        help='Largo del pedido + compensación de largo de la flauta'
    )

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
    faltante = fields.Integer(string='Faltante', compute='_compute_faltante', store=True, help='Cantidad faltante: cantidad solicitada - cantidad planificada')

    # Campos para manejo de pedidos temporales en replanificación
    es_temporal = fields.Boolean(string='Es Temporal', default=False, help='Indica si este pedido es temporal creado para replanificar faltantes >= 500')
    pedido_original_id = fields.Many2one('megastock.production.order', string='Pedido Original', help='Referencia al pedido original del cual este temporal proviene')

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
    
    @api.depends('largo_indice_flauta', 'ancho_indice_flauta', 'cantidad')
    def _compute_area_total(self):
        for record in self:
            if record.largo_indice_flauta and record.ancho_indice_flauta and record.cantidad:
                # Convertir de mm² a m²
                area_unitaria = (record.largo_indice_flauta * record.ancho_indice_flauta) / 1000000
                # SIN redondeo (descomentar si NO se requiere redondeo):
                # record.area_total = area_unitaria * record.cantidad
                # CON redondeo (comentar si NO se requiere redondeo):
                record.area_total = round(area_unitaria * record.cantidad)
            else:
                record.area_total = 0.0
    
    @api.depends('cantidad', 'cantidad_entregada')
    def _compute_porcentaje_cumplimiento(self):
        for record in self:
            if record.cantidad and record.cantidad > 0:
                # SIN redondeo (descomentar si NO se requiere redondeo):
                # record.porcentaje_cumplimiento = (record.cantidad_entregada / record.cantidad) * 100
                # CON redondeo (comentar si NO se requiere redondeo):
                record.porcentaje_cumplimiento = round((record.cantidad_entregada / record.cantidad) * 100)
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

    @api.depends('alto_indice_flauta')
    def _compute_largo_rayado(self):
        """Calcula largo rayado según fórmula: alto_indice_flauta + 2"""
        for record in self:
            if record.alto_indice_flauta:
                record.largo_rayado = record.alto_indice_flauta + 2
            else:
                record.largo_rayado = 2.0  # Valor por defecto si alto_indice_flauta es 0

    @api.depends('alto_indice_flauta')
    def _compute_alto_rayado(self):
        """Calcula alto rayado según fórmula: alto_indice_flauta + 2"""
        for record in self:
            if record.alto_indice_flauta:
                record.alto_rayado = record.alto_indice_flauta + 2
            else:
                record.alto_rayado = 2.0  # Valor por defecto si alto_indice_flauta es 0

    @api.depends('ancho_calculado', 'alto_rayado')
    def _compute_ancho_rayado(self):
        """Calcula ancho rayado según fórmula: ancho_calculado - (alto_rayado * 2)"""
        for record in self:
            if record.ancho_calculado and record.alto_rayado:
                record.ancho_rayado = record.ancho_calculado - (record.alto_rayado * 2)
            else:
                record.ancho_rayado = 0.0

    @api.depends('largo_indice_flauta', 'alto_indice_flauta')
    def _compute_largo_calculado(self):
        """Calcula largo real según fórmula: 2*alto_indice_flauta + largo_indice_flauta + 8"""
        for record in self:
            if record.largo_indice_flauta and record.alto_indice_flauta:
                record.largo_calculado = (2 * record.alto_indice_flauta) + record.largo_indice_flauta + 8
            else:
                record.largo_calculado = record.largo_indice_flauta or 0

    @api.depends('ancho_indice_flauta', 'alto_indice_flauta', 'troquel')
    def _compute_ancho_calculado(self):
        """Calcula ancho real según fórmula: 2*alto_indice_flauta + ancho_indice_flauta + 14 + (2 si troquel=SI)"""
        for record in self:
            if record.ancho_indice_flauta and record.alto_indice_flauta:
                base_ancho = (2 * record.alto_indice_flauta) + record.ancho_indice_flauta + 14
                # Agregar 2mm si troquel = 'si'
                troquel_extra = 2 if record.troquel == 'si' else 0
                #record.ancho_calculado = base_ancho + troquel_extra
                record.ancho_calculado = base_ancho
            else:
                record.ancho_calculado = record.ancho_indice_flauta or 0

    @api.depends('ancho', 'flauta')
    def _compute_solapa(self):
        """Calcula solapa: (ancho / 2) + compensación de ancho de la flauta"""
        for record in self:
            solapa = 0.0
            if record.ancho:
                # Calcular base: ancho / 2
                solapa = record.ancho / 2

                # Buscar compensación de la flauta
                if record.flauta:
                    flauta_obj = self.env['megastock.flauta'].search([
                        ('codigo', '=', record.flauta.upper().strip())
                    ], limit=1)

                    if flauta_obj:
                        solapa += flauta_obj.compensacion_ancho

            record.solapa = solapa

    @api.depends('ancho', 'over_superior', 'flauta')
    def _compute_a1(self):
        """Calcula A1: (ancho / 2) + (over_superior / 2) + compensación de ancho de la flauta"""
        for record in self:
            a1 = 0.0

            # Calcular: (ancho / 2) + (over_superior / 2)
            if record.ancho:
                a1 += record.ancho / 2

            if record.over_superior:
                a1 += record.over_superior / 2

            # Buscar y sumar compensación de la flauta
            if record.flauta:
                flauta_obj = self.env['megastock.flauta'].search([
                    ('codigo', '=', record.flauta.upper().strip())
                ], limit=1)

                if flauta_obj:
                    a1 += flauta_obj.compensacion_ancho

            record.a1 = a1

    @api.depends('alto', 'flauta')
    def _compute_a2(self):
        """Calcula A2: alto + compensación de alto de la flauta"""
        for record in self:
            a2 = 0.0

            # Calcular base: alto
            if record.alto:
                a2 = record.alto

            # Buscar y sumar compensación de alto de la flauta
            if record.flauta:
                flauta_obj = self.env['megastock.flauta'].search([
                    ('codigo', '=', record.flauta.upper().strip())
                ], limit=1)

                if flauta_obj:
                    a2 += flauta_obj.compensacion_alto

            record.a2 = a2

    @api.depends('ancho', 'over_superior', 'flauta')
    def _compute_a3(self):
        """Calcula A3: (ancho / 2) + (over_superior / 2) + compensación de ancho de la flauta (igual que A1)"""
        for record in self:
            a3 = 0.0

            # Calcular: (ancho / 2) + (over_superior / 2)
            if record.ancho:
                a3 += record.ancho / 2

            if record.over_superior:
                a3 += record.over_superior / 2

            # Buscar y sumar compensación de la flauta
            if record.flauta:
                flauta_obj = self.env['megastock.flauta'].search([
                    ('codigo', '=', record.flauta.upper().strip())
                ], limit=1)

                if flauta_obj:
                    a3 += flauta_obj.compensacion_ancho

            record.a3 = a3

    @api.depends('alto', 'flauta')
    def _compute_alto_indice_flauta(self):
        """Calcula Alto (Índice Flauta): alto + compensación de alto de la flauta"""
        for record in self:
            alto_indice = 0.0

            # Calcular base: alto
            if record.alto:
                alto_indice = record.alto

            # Buscar y sumar compensación de alto de la flauta
            if record.flauta:
                flauta_obj = self.env['megastock.flauta'].search([
                    ('codigo', '=', record.flauta.upper().strip())
                ], limit=1)

                if flauta_obj:
                    alto_indice += flauta_obj.compensacion_alto

            record.alto_indice_flauta = alto_indice

    @api.depends('ancho', 'flauta')
    def _compute_ancho_indice_flauta(self):
        """Calcula Ancho (Índice Flauta): ancho + compensación de ancho de la flauta"""
        for record in self:
            ancho_indice = 0.0

            # Calcular base: ancho
            if record.ancho:
                ancho_indice = record.ancho

            # Buscar y sumar compensación de ancho de la flauta
            if record.flauta:
                flauta_obj = self.env['megastock.flauta'].search([
                    ('codigo', '=', record.flauta.upper().strip())
                ], limit=1)

                if flauta_obj:
                    ancho_indice += flauta_obj.compensacion_ancho

            record.ancho_indice_flauta = ancho_indice

    @api.depends('largo', 'flauta')
    def _compute_largo_indice_flauta(self):
        """Calcula Largo (Índice Flauta): largo + compensación de largo de la flauta"""
        for record in self:
            largo_indice = 0.0

            # Calcular base: largo
            if record.largo:
                largo_indice = record.largo

            # Buscar y sumar compensación de largo de la flauta
            if record.flauta:
                flauta_obj = self.env['megastock.flauta'].search([
                    ('codigo', '=', record.flauta.upper().strip())
                ], limit=1)

                if flauta_obj:
                    largo_indice += flauta_obj.compensacion_largo

            record.largo_indice_flauta = largo_indice

    @api.depends('cantidad', 'cantidad_planificada')
    def _compute_faltante(self):
        """Calcula el faltante: cantidad solicitada - cantidad planificada"""
        for record in self:
            record.faltante = (record.cantidad or 0) - (record.cantidad_planificada or 0)

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
    
    @api.depends('cortes', 'largo_indice_flauta')
    def _compute_metros_lineales(self):
        for record in self:
            if record.cortes and record.largo_indice_flauta:
                # SIN redondeo (descomentar si NO se requiere redondeo):
                # record.metros_lineales = (record.cortes * record.largo_indice_flauta) / 1000
                # CON redondeo (comentar si NO se requiere redondeo):
                record.metros_lineales = round((record.cortes * record.largo_indice_flauta) / 1000)
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
                # SIN redondeo (descomentar si NO se requiere redondeo):
                # record.cantidad_liner_interno = (record.liner_interno_ancho * record.liner_interno_gm) * (record.metros_lineales / 1000000)
                # CON redondeo (comentar si NO se requiere redondeo):
                record.cantidad_liner_interno = round((record.liner_interno_ancho * record.liner_interno_gm) * (record.metros_lineales / 1000000))
            else:
                record.cantidad_liner_interno = 0.0
    
    @api.depends('medium_ancho', 'medium_gm', 'metros_lineales')
    def _compute_cantidad_medium(self):
        for record in self:
            if record.medium_ancho and record.medium_gm and record.metros_lineales:
                # SIN redondeo (descomentar si NO se requiere redondeo):
                # record.cantidad_medium = (record.medium_ancho * record.medium_gm) * (record.metros_lineales / 1000000) * 1.45
                # CON redondeo (comentar si NO se requiere redondeo):
                record.cantidad_medium = round((record.medium_ancho * record.medium_gm) * (record.metros_lineales / 1000000) * 1.45)
            else:
                record.cantidad_medium = 0.0
    
    @api.depends('liner_externo_ancho', 'liner_externo_gm', 'metros_lineales')
    def _compute_cantidad_liner_externo(self):
        for record in self:
            if record.liner_externo_ancho and record.liner_externo_gm and record.metros_lineales:
                # SIN redondeo (descomentar si NO se requiere redondeo):
                # record.cantidad_liner_externo = (record.liner_externo_ancho * record.liner_externo_gm) * (record.metros_lineales / 1000000)
                # CON redondeo (comentar si NO se requiere redondeo):
                record.cantidad_liner_externo = round((record.liner_externo_ancho * record.liner_externo_gm) * (record.metros_lineales / 1000000))
            else:
                record.cantidad_liner_externo = 0.0
    
    @api.onchange('cortes', 'largo_indice_flauta')
    def _onchange_cortes_largo(self):
        """Actualizar metros lineales cuando cambie cortes o largo_indice_flauta"""
        if self.cortes and self.largo_indice_flauta:
            self.metros_lineales = (self.cortes * self.largo_indice_flauta) / 1000
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

    def _crear_pedido_temporal(self, orden_original, faltante):
        """Crea un pedido temporal para replanificar un faltante >= 500

        Args:
            orden_original: Pedido original del cual proviene el faltante
            faltante: Cantidad faltante a planificar

        Returns:
            Nuevo pedido temporal creado
        """
        return self.create({
            'orden_produccion': f"{orden_original.orden_produccion}-TEMP-{faltante}",
            'cliente': orden_original.cliente,
            'codigo': orden_original.codigo,
            'descripcion': f"TEMPORAL - {orden_original.descripcion}",
            'pedido': orden_original.pedido,
            'largo': orden_original.largo,
            'ancho': orden_original.ancho,
            'alto': orden_original.alto,
            'cantidad': faltante,
            'cavidad': orden_original.cavidad,
            'flauta': orden_original.flauta,
            'troquel': orden_original.troquel,
            'tipo_producto': orden_original.tipo_producto,
            'sustrato': orden_original.sustrato,
            'over_superior': orden_original.over_superior,
            'over_inferior': orden_original.over_inferior,
            'fecha_pedido_cliente': orden_original.fecha_pedido_cliente,
            'fecha_entrega_cliente': orden_original.fecha_entrega_cliente,
            'fecha_produccion': orden_original.fecha_produccion,
            'estado': 'pendiente',
            'es_temporal': True,
            'pedido_original_id': orden_original.id,
        })

    def _resetear_planificacion(self, ordenes):
        """Resetea todos los campos de planificación de las órdenes

        Args:
            ordenes: Recordset de órdenes a resetear
        """
        ordenes.write({
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
        })

    def _eliminar_pedidos_temporales(self, pedidos_temporales):
        """Elimina pedidos temporales del sistema

        Args:
            pedidos_temporales: Recordset de pedidos temporales a eliminar
        """
        if pedidos_temporales:
            pedidos_temporales.unlink()

    def _optimizar_ordenes(self, ordenes, test_principal=None, cavidad_limite=1, bobina_unica=False, bobinas_disponibles=None):
        """Algoritmo de optimización basado en el archivo Excel de trimado con validación iterativa de faltantes

        Args:
            ordenes: Recordset de órdenes a optimizar
            test_principal: Número de test principal para la producción
            cavidad_limite: Límite superior para multiplicar ancho_calculado (default: 1)
            bobina_unica: Si True, todos los grupos usan una sola bobina (default: False)
            bobinas_disponibles: Lista de anchos de bobinas a considerar (default: None, usa todas las activas)
        """
        from odoo.exceptions import UserError

        # Si no se proporcionan bobinas específicas, obtener todas las activas
        if bobinas_disponibles is None:
            Bobina = self.env['megastock.bobina']
            bobinas_disponibles = Bobina.get_bobinas_activas()

        # Si no hay bobinas configuradas o seleccionadas, mostrar error
        if not bobinas_disponibles:
            raise UserError(
                "No hay bobinas disponibles para planificar. "
                "Ve a Configuración > Bobinas y configura al menos una bobina activa, "
                "o selecciona bobinas en el wizard de planificación."
            )

        # ESTRATEGIA 1: BOBINA ÚNICA - Replanificación iterativa con una sola bobina
        if bobina_unica:
            # Solo hay una bobina seleccionada
            bobina_seleccionada = bobinas_disponibles[0]
            print(f"[BOBINA ÚNICA] Usando bobina de {bobina_seleccionada}mm")

            # Separar órdenes originales (no temporales)
            ordenes_originales = ordenes.filtered(lambda o: not o.es_temporal)
            pedidos_temporales = self.env['megastock.production.order']
            ordenes_pendientes = self.env['megastock.production.order']

            max_iteraciones = 50  # Reducir para evitar cálculos innecesarios
            iteracion = 0
            grupos_finales = []

            while iteracion < max_iteraciones:
                iteracion += 1
                print(f"\n[BOBINA ÚNICA - ITERACIÓN {iteracion}] Iniciando...")

                # PASO 1: Conjunto completo a planificar (originales + temporales)
                ordenes_a_planificar = ordenes_originales | pedidos_temporales
                print(f"[BOBINA ÚNICA - ITERACIÓN {iteracion}] Órdenes a planificar: {len(ordenes_a_planificar)} ({len(ordenes_originales)} originales + {len(pedidos_temporales)} temporales)")

                # PASO 2: Ejecutar algoritmo de optimización con la bobina única
                grupos_optimizados = []
                ordenes_procesadas = set()
                grupo_counter = 1

                for orden in ordenes_a_planificar:
                    if orden.id in ordenes_procesadas:
                        continue

                    # Buscar mejor combinación usando SOLO la bobina seleccionada
                    mejor_combinacion = self._encontrar_mejor_combinacion(
                        orden, ordenes_a_planificar, ordenes_procesadas, [bobina_seleccionada], cavidad_limite
                    )

                    if mejor_combinacion:
                        grupos_optimizados.append(mejor_combinacion)

                        # Marcar órdenes como procesadas
                        for orden_comb_data in mejor_combinacion['ordenes']:
                            ordenes_procesadas.add(orden_comb_data['orden'].id)

                        grupo_counter += 1

                print(f"[BOBINA ÚNICA - ITERACIÓN {iteracion}] Grupos encontrados: {len(grupos_optimizados)}")

                # PASO 3: Aplicar grupos encontrados
                if grupos_optimizados:
                    for idx, grupo in enumerate(grupos_optimizados, start=1):
                        self._aplicar_combinacion(grupo, idx)
                    grupos_finales = grupos_optimizados
                    print(f"[BOBINA ÚNICA - ITERACIÓN {iteracion}] Grupos aplicados exitosamente")
                else:
                    print(f"[BOBINA ÚNICA - ITERACIÓN {iteracion}] ⚠️ NO se encontraron combinaciones posibles con esta bobina")

                # Forzar recálculo de campos computados
                ordenes_originales.invalidate_cache()

                # PASO 4: Clasificar faltantes de órdenes originales
                con_faltante_alto = ordenes_originales.filtered(lambda o: o.faltante >= 500)
                con_faltante_bajo = ordenes_originales.filtered(lambda o: 0 < o.faltante < 500)

                # Debug: Mostrar faltantes detectados
                if con_faltante_alto:
                    print(f"[BOBINA ÚNICA - ITERACIÓN {iteracion}] Faltantes ALTOS (>= 500): {[(o.orden_produccion, o.faltante) for o in con_faltante_alto]}")
                if con_faltante_bajo:
                    print(f"[BOBINA ÚNICA - ITERACIÓN {iteracion}] Faltantes BAJOS (< 500): {[(o.orden_produccion, o.faltante) for o in con_faltante_bajo]}")

                # PASO 5: Condición de salida - Todos cumplidos ✅
                if not con_faltante_alto and not con_faltante_bajo:
                    print(f"[BOBINA ÚNICA - ITERACIÓN {iteracion}] Todos los pedidos cumplidos. Finalizando.")
                    # Limpiar temporales
                    self._eliminar_pedidos_temporales(pedidos_temporales)
                    break

                # PASO 6: Condición de salida - Solo quedan faltantes < 500 ⚠️
                if not con_faltante_alto and con_faltante_bajo:
                    print(f"[BOBINA ÚNICA - ITERACIÓN {iteracion}] Solo quedan faltantes < 500. Reseteando {len(con_faltante_bajo)} pedidos.")
                    # Resetear órdenes con faltante bajo (quedan PENDIENTES sin grupo)
                    self._resetear_planificacion(con_faltante_bajo)
                    ordenes_pendientes = con_faltante_bajo
                    print(f"[BOBINA ÚNICA - ITERACIÓN {iteracion}] Pedidos reseteados: {[o.orden_produccion for o in con_faltante_bajo]}")
                    # Limpiar temporales
                    self._eliminar_pedidos_temporales(pedidos_temporales)
                    break

                # PASO 7: Hay faltantes >= 500, continuar iterando
                if con_faltante_alto:
                    # Verificar si podemos continuar iterando
                    if iteracion >= max_iteraciones:
                        print(f"[BOBINA ÚNICA - ITERACIÓN {iteracion}] ⚠️ LÍMITE ALCANZADO - Intentando planificación forzada individual")

                        # ESTRATEGIA FINAL: Planificar individualmente los faltantes restantes
                        for orden_faltante in con_faltante_alto:
                            # Intentar planificar el faltante como orden individual
                            mejor_comb = self._encontrar_mejor_combinacion(
                                orden_faltante, self.env['megastock.production.order'], set(), [bobina_seleccionada], 1
                            )
                            if mejor_comb:
                                # Aplicar como nuevo grupo
                                grupo_counter = len(grupos_finales) + 1
                                self._aplicar_combinacion(mejor_comb, grupo_counter)
                                grupos_finales.append(mejor_comb)
                                print(f"[BOBINA ÚNICA] Faltante planificado individualmente: {orden_faltante.orden_produccion}")
                            else:
                                # Si no cabe ni individual, resetear
                                self._resetear_planificacion(orden_faltante)
                                ordenes_pendientes |= orden_faltante
                                print(f"[BOBINA ÚNICA] ⚠️ Orden NO cabe en bobina: {orden_faltante.orden_produccion}")

                        # Limpiar temporales
                        self._eliminar_pedidos_temporales(pedidos_temporales)
                        break

                    # 7.1 GUARDAR faltantes ANTES de resetear (¡CRÍTICO!)
                    faltantes_a_replanificar = [(orden, orden.faltante) for orden in con_faltante_alto]
                    print(f"[BOBINA ÚNICA - ITERACIÓN {iteracion}] Guardando faltantes para replanificar: {[(o.orden_produccion, f) for o, f in faltantes_a_replanificar]}")

                    # 7.2 Resetear TODA la planificación (originales + temporales)
                    self._resetear_planificacion(ordenes_originales)
                    self._resetear_planificacion(pedidos_temporales)

                    # 7.3 Eliminar todos los pedidos temporales anteriores
                    self._eliminar_pedidos_temporales(pedidos_temporales)
                    pedidos_temporales = self.env['megastock.production.order']

                    # 7.4 Crear nuevos pedidos temporales con los faltantes guardados
                    for orden_original, faltante_guardado in faltantes_a_replanificar:
                        pedido_temporal = self._crear_pedido_temporal(orden_original, faltante_guardado)
                        pedidos_temporales |= pedido_temporal
                        print(f"[BOBINA ÚNICA - ITERACIÓN {iteracion}] Creado temporal: {pedido_temporal.orden_produccion} con {faltante_guardado} unidades (restante del pedido original)")

                    # Los pedidos con faltante < 500 NO se convierten en temporales
                    # Solo se desagrupan y se intentan reagrupar en la siguiente iteración

                    print(f"[BOBINA ÚNICA - ITERACIÓN {iteracion}] Continuando con {len(pedidos_temporales)} pedidos temporales...")

            # VALIDACIÓN Y CORRECCIÓN FINAL - Verificar tipos de combinación
            ordenes_con_grupo = ordenes.filtered(lambda o: o.grupo_planificacion)

            if ordenes_con_grupo:
                # Agrupar por grupo_planificacion
                grupos_dict = {}
                for orden in ordenes_con_grupo:
                    grupo = orden.grupo_planificacion
                    if grupo not in grupos_dict:
                        grupos_dict[grupo] = []
                    grupos_dict[grupo].append(orden)

                # Verificar y corregir cada grupo
                grupos_corregidos = 0
                for grupo_nombre, ordenes_grupo in grupos_dict.items():
                    num_ordenes = len(ordenes_grupo)
                    tipo_actual = ordenes_grupo[0].tipo_combinacion if ordenes_grupo else None

                    # Determinar el tipo correcto
                    if num_ordenes == 1:
                        tipo_correcto = 'individual'
                    elif num_ordenes == 2:
                        tipo_correcto = 'dupla'
                    else:
                        tipo_correcto = 'individual'  # Triplas no soportadas

                    # Si el tipo está mal, corregirlo
                    if tipo_actual != tipo_correcto:
                        print(f"[BOBINA ÚNICA - CORRECCIÓN FINAL] {grupo_nombre}: {num_ordenes} orden(es) con tipo='{tipo_actual}' → corrigiendo a '{tipo_correcto}'")

                        # Actualizar todas las órdenes del grupo
                        for orden in ordenes_grupo:
                            # Recalcular sobrante con el tipo correcto
                            MARGEN_SEGURIDAD = 30
                            espacio_por_orden = (orden.bobina_utilizada - MARGEN_SEGURIDAD) / num_ordenes
                            sobrante_correcto = round(espacio_por_orden - orden.ancho_calculado * orden.cavidad_optimizada)

                            orden.write({
                                'tipo_combinacion': tipo_correcto,
                                'sobrante': sobrante_correcto
                            })

                        grupos_corregidos += 1

                if grupos_corregidos > 0:
                    print(f"[BOBINA ÚNICA - CORRECCIÓN FINAL] ✅ {grupos_corregidos} grupo(s) corregidos")

            # Calcular estadísticas finales
            eficiencia_total = sum(grupo['eficiencia'] for grupo in grupos_finales) if grupos_finales else 0
            eficiencia_promedio = eficiencia_total / len(grupos_finales) if grupos_finales else 0
            desperdicio_total = sum(grupo['sobrante'] for grupo in grupos_finales) if grupos_finales else 0

            print(f"[BOBINA ÚNICA] Planificación completada:")
            print(f"  - Iteraciones: {iteracion}")
            print(f"  - Grupos creados: {len(grupos_finales)}")
            print(f"  - Eficiencia promedio: {eficiencia_promedio:.2f}%")
            print(f"  - Órdenes pendientes: {len(ordenes_pendientes)}")

            return {
                'grupos': len(grupos_finales),
                'eficiencia_promedio': eficiencia_promedio,
                'bobina_optima': bobina_seleccionada,
                'desperdicio_total': desperdicio_total,
                'ordenes_pendientes': len(ordenes_pendientes),
                'iteraciones': iteracion
            }

        # ESTRATEGIA 2: BOBINAS MÚLTIPLES - Replanificación iterativa con manejo de faltantes
        else:
            # Separar órdenes originales (no temporales)
            ordenes_originales = ordenes.filtered(lambda o: not o.es_temporal)
            pedidos_temporales = self.env['megastock.production.order']
            ordenes_pendientes = self.env['megastock.production.order']

            max_iteraciones = 50  # Reducir para evitar cálculos innecesarios
            iteracion = 0

            # Historial de faltantes para detectar bucles infinitos
            historial_faltantes = []
            iteraciones_sin_cambio = 0
            max_sin_cambio = 3  # Si 3 iteraciones consecutivas sin cambios, salir

            while iteracion < max_iteraciones:
                iteracion += 1

                # PASO 1: Conjunto completo a planificar (originales + temporales)
                ordenes_a_planificar = ordenes_originales | pedidos_temporales

                # PASO 2: Ejecutar algoritmo de optimización
                # ESTRATEGIA: Buscar DUPLAS primero, luego INDIVIDUALES
                grupos_optimizados = []
                ordenes_procesadas = set()
                grupo_counter = 1

                # FASE 1: Buscar todas las duplas posibles (minimiza sobrante)
                print(f"[ITERACIÓN {iteracion}] FASE 1: Buscando duplas óptimas...")
                duplas_encontradas = []

                ordenes_list = list(ordenes_a_planificar)
                print(f"[ITERACIÓN {iteracion}] Total órdenes a evaluar: {len(ordenes_list)}")

                for i, orden1 in enumerate(ordenes_list):
                    if orden1.id in ordenes_procesadas:
                        continue

                    mejor_dupla = None
                    menor_sobrante_dupla = float('inf')

                    # Probar con todas las demás órdenes para formar dupla
                    for j, orden2 in enumerate(ordenes_list):
                        if i == j or orden2.id in ordenes_procesadas:  # FIX: cambiar i >= j a i == j
                            continue

                        # Buscar mejor combinación para esta dupla potencial
                        ordenes_dupla = self.env['megastock.production.order'].browse([orden1.id, orden2.id])
                        mejor_comb = self._encontrar_mejor_combinacion(
                            orden1, ordenes_dupla, set(), bobinas_disponibles, cavidad_limite
                        )

                        # Solo considerar si es realmente una dupla (2 órdenes)
                        if mejor_comb and mejor_comb['tipo'] == 'dupla' and len(mejor_comb['ordenes']) == 2:
                            if mejor_comb['sobrante'] < menor_sobrante_dupla:
                                menor_sobrante_dupla = mejor_comb['sobrante']
                                mejor_dupla = mejor_comb
                                print(f"[ITERACIÓN {iteracion}] → Dupla candidata: {orden1.orden_produccion} + {orden2.orden_produccion} = sobrante {menor_sobrante_dupla}mm")

                    # Si encontramos una dupla válida, agregarla
                    if mejor_dupla:
                        duplas_encontradas.append({
                            'combinacion': mejor_dupla,
                            'sobrante': menor_sobrante_dupla,
                            'orden1_id': orden1.id,
                            'orden2_id': mejor_dupla['ordenes'][1]['orden'].id
                        })
                        print(f"[ITERACIÓN {iteracion}] ✓ Mejor dupla para {orden1.orden_produccion}: sobrante {menor_sobrante_dupla}mm")

                # Ordenar duplas por menor sobrante y aplicar las mejores
                duplas_encontradas.sort(key=lambda x: x['sobrante'])
                print(f"[ITERACIÓN {iteracion}] Total duplas candidatas encontradas: {len(duplas_encontradas)}")

                duplas_aplicadas = 0
                for dupla_info in duplas_encontradas:
                    # Verificar que ambas órdenes aún no estén procesadas
                    if dupla_info['orden1_id'] not in ordenes_procesadas and dupla_info['orden2_id'] not in ordenes_procesadas:
                        grupos_optimizados.append(dupla_info['combinacion'])
                        ordenes_procesadas.add(dupla_info['orden1_id'])
                        ordenes_procesadas.add(dupla_info['orden2_id'])
                        duplas_aplicadas += 1
                        print(f"[ITERACIÓN {iteracion}] ✓ Dupla #{duplas_aplicadas} agregada con sobrante {dupla_info['sobrante']}mm")

                print(f"[ITERACIÓN {iteracion}] Total duplas aplicadas: {duplas_aplicadas}")

                # FASE 2: Procesar órdenes restantes como individuales
                print(f"[ITERACIÓN {iteracion}] FASE 2: Procesando {len(ordenes_list) - len(ordenes_procesadas)} órdenes individuales...")

                for orden in ordenes_a_planificar:
                    if orden.id in ordenes_procesadas:
                        continue

                    # Buscar mejor combinación individual
                    mejor_combinacion = self._encontrar_mejor_combinacion(
                        orden, self.env['megastock.production.order'].browse([orden.id]), set(), bobinas_disponibles, cavidad_limite
                    )

                    if mejor_combinacion:
                        grupos_optimizados.append(mejor_combinacion)
                        ordenes_procesadas.add(orden.id)
                        grupo_counter += 1

                # Aplicar los grupos encontrados
                if grupos_optimizados:
                    for idx, grupo in enumerate(grupos_optimizados, start=1):
                        self._aplicar_combinacion(grupo, idx)

                # PASO 3: Refrescar y calcular faltantes (SOLO en órdenes originales)
                ordenes_originales.invalidate_cache()

                # PASO 4: Clasificar faltantes de órdenes originales
                con_faltante_alto = ordenes_originales.filtered(lambda o: o.faltante >= 500)
                con_faltante_bajo = ordenes_originales.filtered(lambda o: 0 < o.faltante < 500)

                # Debug: Mostrar faltantes detectados
                if con_faltante_alto:
                    print(f"[ITERACIÓN {iteracion}] Faltantes ALTOS (>= 500): {[(o.orden_produccion, o.faltante) for o in con_faltante_alto]}")
                if con_faltante_bajo:
                    print(f"[ITERACIÓN {iteracion}] Faltantes BAJOS (< 500): {[(o.orden_produccion, o.faltante) for o in con_faltante_bajo]}")

                # PASO 4.5: Detectar bucle infinito - Faltantes que no cambian
                faltantes_actuales = set((o.orden_produccion, o.faltante) for o in con_faltante_alto)

                if historial_faltantes and faltantes_actuales == historial_faltantes[-1]:
                    iteraciones_sin_cambio += 1
                    print(f"[ITERACIÓN {iteracion}] ⚠️ Faltantes SIN CAMBIO ({iteraciones_sin_cambio}/{max_sin_cambio})")

                    if iteraciones_sin_cambio >= max_sin_cambio:
                        print(f"[ITERACIÓN {iteracion}] 🛑 BUCLE INFINITO DETECTADO - Los faltantes no han cambiado en {max_sin_cambio} iteraciones")
                        print(f"[ITERACIÓN {iteracion}] Órdenes con faltantes persistentes: {[o.orden_produccion for o in con_faltante_alto]}")

                        # Resetear estas órdenes como no planificables (dejar pendientes)
                        self._resetear_planificacion(con_faltante_alto)
                        ordenes_pendientes |= con_faltante_alto
                        print(f"[ITERACIÓN {iteracion}] Órdenes marcadas como PENDIENTES (no planificables con bobinas disponibles)")

                        # Limpiar temporales
                        self._eliminar_pedidos_temporales(pedidos_temporales)
                        break
                else:
                    iteraciones_sin_cambio = 0

                historial_faltantes.append(faltantes_actuales)

                # PASO 5: Condición de salida - Todos cumplidos ✅
                if not con_faltante_alto and not con_faltante_bajo:
                    print(f"[ITERACIÓN {iteracion}] Todos los pedidos cumplidos. Finalizando.")
                    # Limpiar temporales
                    self._eliminar_pedidos_temporales(pedidos_temporales)
                    break

                # PASO 6: Condición de salida - Solo quedan faltantes < 500 ⚠️
                if not con_faltante_alto and con_faltante_bajo:
                    print(f"[ITERACIÓN {iteracion}] Solo quedan faltantes < 500. Reseteando {len(con_faltante_bajo)} pedidos.")
                    # Resetear órdenes con faltante bajo (quedan PENDIENTES sin grupo)
                    self._resetear_planificacion(con_faltante_bajo)
                    ordenes_pendientes = con_faltante_bajo
                    print(f"[ITERACIÓN {iteracion}] Pedidos reseteados: {[o.orden_produccion for o in con_faltante_bajo]}")
                    # Limpiar temporales
                    self._eliminar_pedidos_temporales(pedidos_temporales)
                    break

                # PASO 7: Hay faltantes >= 500, continuar iterando
                if con_faltante_alto:
                    # Verificar si podemos continuar iterando
                    if iteracion >= max_iteraciones:
                        print(f"[ITERACIÓN {iteracion}] ⚠️ LÍMITE ALCANZADO - Intentando planificación forzada individual")

                        # ESTRATEGIA FINAL: Planificar individualmente los faltantes restantes
                        grupo_counter = len(set(ordenes_originales.filtered(lambda o: o.grupo_planificacion).mapped('grupo_planificacion'))) + 1

                        for orden_faltante in con_faltante_alto:
                            # Intentar planificar el faltante como orden individual
                            mejor_comb = self._encontrar_mejor_combinacion(
                                orden_faltante, self.env['megastock.production.order'], set(), bobinas_disponibles, 1
                            )
                            if mejor_comb:
                                # Aplicar como nuevo grupo
                                self._aplicar_combinacion(mejor_comb, grupo_counter)
                                grupo_counter += 1
                                print(f"[ITERACIÓN {iteracion}] Faltante planificado individualmente: {orden_faltante.orden_produccion}")
                            else:
                                # Si no cabe ni individual, resetear
                                self._resetear_planificacion(orden_faltante)
                                ordenes_pendientes |= orden_faltante
                                print(f"[ITERACIÓN {iteracion}] ⚠️ Orden NO cabe en bobinas disponibles: {orden_faltante.orden_produccion}")

                        # Limpiar temporales
                        self._eliminar_pedidos_temporales(pedidos_temporales)
                        break

                    # 7.1 GUARDAR faltantes ANTES de resetear (¡CRÍTICO!)
                    faltantes_a_replanificar = [(orden, orden.faltante) for orden in con_faltante_alto]
                    print(f"[ITERACIÓN {iteracion}] Guardando faltantes para replanificar: {[(o.orden_produccion, f) for o, f in faltantes_a_replanificar]}")

                    # 7.2 Resetear TODA la planificación (originales + temporales)
                    self._resetear_planificacion(ordenes_originales)
                    self._resetear_planificacion(pedidos_temporales)

                    # 7.3 Eliminar temporales anteriores
                    self._eliminar_pedidos_temporales(pedidos_temporales)
                    pedidos_temporales = self.env['megastock.production.order']

                    # 7.4 Crear nuevos pedidos temporales con los faltantes guardados
                    for orden_original, faltante_guardado in faltantes_a_replanificar:
                        temp = self._crear_pedido_temporal(orden_original, faltante_guardado)
                        pedidos_temporales |= temp
                        print(f"[ITERACIÓN {iteracion}] Creado temporal: {temp.orden_produccion} con {faltante_guardado} unidades (restante del pedido original)")

                    # IMPORTANTE: Las órdenes con faltante < 500 NO generan temporal
                    # Solo quedan desagrupadas y volverán a intentar agruparse

            # PASO 8: Limpieza final - Resetear pedidos con faltante < 500 que quedaron agrupados
            ordenes_originales.invalidate_cache()
            ordenes_con_faltante_final = ordenes_originales.filtered(lambda o: 0 < o.faltante < 500)
            if ordenes_con_faltante_final:
                self._resetear_planificacion(ordenes_con_faltante_final)
                ordenes_pendientes = ordenes_con_faltante_final

            # PASO 9: VALIDACIÓN Y CORRECCIÓN FINAL - Verificar tipos de combinación
            ordenes_finales = ordenes_originales.filtered(lambda o: o.grupo_planificacion)

            if ordenes_finales:
                # Agrupar por grupo_planificacion
                grupos_dict = {}
                for orden in ordenes_finales:
                    grupo = orden.grupo_planificacion
                    if grupo not in grupos_dict:
                        grupos_dict[grupo] = []
                    grupos_dict[grupo].append(orden)

                # Verificar y corregir cada grupo
                grupos_corregidos = 0
                for grupo_nombre, ordenes_grupo in grupos_dict.items():
                    num_ordenes = len(ordenes_grupo)
                    tipo_actual = ordenes_grupo[0].tipo_combinacion if ordenes_grupo else None

                    # Determinar el tipo correcto
                    if num_ordenes == 1:
                        tipo_correcto = 'individual'
                    elif num_ordenes == 2:
                        tipo_correcto = 'dupla'
                    else:
                        tipo_correcto = 'individual'  # Triplas no soportadas

                    # Si el tipo está mal, corregirlo
                    if tipo_actual != tipo_correcto:
                        print(f"[CORRECCIÓN FINAL] {grupo_nombre}: {num_ordenes} orden(es) con tipo='{tipo_actual}' → corrigiendo a '{tipo_correcto}'")

                        # Actualizar todas las órdenes del grupo
                        for orden in ordenes_grupo:
                            # Recalcular sobrante con el tipo correcto
                            MARGEN_SEGURIDAD = 30
                            espacio_por_orden = (orden.bobina_utilizada - MARGEN_SEGURIDAD) / num_ordenes
                            sobrante_correcto = round(espacio_por_orden - orden.ancho_calculado * orden.cavidad_optimizada)

                            orden.write({
                                'tipo_combinacion': tipo_correcto,
                                'sobrante': sobrante_correcto
                            })

                        grupos_corregidos += 1

                if grupos_corregidos > 0:
                    print(f"[CORRECCIÓN FINAL] ✅ {grupos_corregidos} grupo(s) corregidos")

                # Calcular estadísticas finales
                eficiencia_total = sum(ordenes_finales.mapped('eficiencia'))
                eficiencia_promedio = eficiencia_total / len(ordenes_finales)
                desperdicio_total = sum(ordenes_finales.mapped('sobrante'))
                num_grupos = len(set(ordenes_finales.mapped('grupo_planificacion')))
            else:
                eficiencia_promedio = 0
                desperdicio_total = 0
                num_grupos = 0

            return {
                'grupos': num_grupos,
                'eficiencia_promedio': eficiencia_promedio,
                'desperdicio_total': desperdicio_total,
                'ordenes_pendientes': len(ordenes_pendientes),
                'iteraciones': iteracion
            }

    def _encontrar_mejor_combinacion_para_faltante(self, orden_con_faltante, ordenes_disponibles, bobinas, cavidad_limite=1):
        """Encuentra la mejor combinación para una orden que tiene faltante >= 500

        Args:
            orden_con_faltante: Orden que tiene faltante >= 500
            ordenes_disponibles: Órdenes sin grupo disponibles para combinar
            bobinas: Lista de anchos de bobinas disponibles
            cavidad_limite: Límite superior para multiplicar ancho_calculado

        Returns:
            dict con la mejor combinación encontrada, o None si no se encuentra
        """
        mejor_combinacion = None
        menor_sobrante = float('inf')

        MARGEN_SEGURIDAD = 30

        # IMPORTANTE: Ordenar bobinas de MENOR a MAYOR para minimizar sobrante
        bobinas_ordenadas = sorted(bobinas)

        # Crear una "orden virtual" que representa el faltante
        # Utilizamos la orden original pero ajustamos la cantidad al faltante
        faltante = orden_con_faltante.faltante

        # Probar combinaciones con el faltante como orden individual
        for multiplicador in range(1, cavidad_limite + 1):
            ancho_util = orden_con_faltante.ancho_calculado * multiplicador

            for bobina in bobinas_ordenadas:
                if ancho_util <= (bobina - MARGEN_SEGURIDAD):
                    # Calcular si el faltante cabe con este multiplicador
                    cavidad_efectiva = orden_con_faltante.cavidad * multiplicador if orden_con_faltante.cavidad else multiplicador

                    if cavidad_efectiva > 0:
                        cortes_necesarios = faltante / cavidad_efectiva

                        # Crear datos simulados para el faltante
                        orden_data = [{
                            'orden': orden_con_faltante,
                            'multiplicador': multiplicador,
                            'ancho_efectivo': ancho_util,
                            'cantidad_override': faltante  # Indicador de que usamos el faltante
                        }]

                        # Calcular eficiencia simulada
                        resultado = self._calcular_eficiencia_para_faltante(
                            orden_con_faltante, faltante, multiplicador, bobina
                        )

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

        # Probar combinaciones del faltante con otras órdenes disponibles
        for orden2 in ordenes_disponibles:
            for mult1 in range(1, cavidad_limite + 1):
                for mult2 in range(1, cavidad_limite + 1):
                    ancho1 = orden_con_faltante.ancho_calculado * mult1
                    ancho2 = orden2.ancho_calculado * mult2
                    ancho_total = ancho1 + ancho2

                    for bobina in bobinas_ordenadas:
                        if ancho_total <= (bobina - MARGEN_SEGURIDAD):
                            ordenes_data = [
                                {
                                    'orden': orden_con_faltante,
                                    'multiplicador': mult1,
                                    'ancho_efectivo': ancho1,
                                    'cantidad_override': faltante
                                },
                                {
                                    'orden': orden2,
                                    'multiplicador': mult2,
                                    'ancho_efectivo': ancho2
                                }
                            ]

                            # Calcular eficiencia para dupla con faltante
                            resultado = self._calcular_eficiencia_dupla_con_faltante(
                                orden_con_faltante, faltante, mult1,
                                orden2, mult2, bobina
                            )

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

        return mejor_combinacion

    def _calcular_eficiencia_para_faltante(self, orden, faltante, multiplicador, bobina_ancho):
        """Calcula eficiencia para una orden procesando solo su faltante"""
        ancho_efectivo = orden.ancho_calculado * multiplicador
        cavidad_efectiva = orden.cavidad * multiplicador if orden.cavidad else multiplicador

        if cavidad_efectiva == 0 or ancho_efectivo > bobina_ancho:
            return {
                'eficiencia': 0,
                'sobrante': bobina_ancho,
                'metros_lineales': 0,
                'cortes_totales': 0
            }

        MARGEN_SEGURIDAD = 30
        espacio_disponible = bobina_ancho - MARGEN_SEGURIDAD
        sobrante = espacio_disponible - ancho_efectivo

        eficiencia = round((ancho_efectivo / bobina_ancho) * 100)

        cortes_necesarios = faltante / cavidad_efectiva
        metros_lineales = (cortes_necesarios * orden.largo_calculado) / 1000 if orden.largo_calculado else 0

        return {
            'eficiencia': eficiencia,
            'sobrante': sobrante,
            'metros_lineales': metros_lineales,
            'cortes_totales': cortes_necesarios
        }

    def _calcular_eficiencia_dupla_con_faltante(self, orden1, faltante1, mult1, orden2, mult2, bobina_ancho):
        """Calcula eficiencia para dupla donde orden1 usa su faltante y orden2 usa su cantidad completa"""
        ancho1 = orden1.ancho_calculado * mult1
        ancho2 = orden2.ancho_calculado * mult2
        ancho_total = ancho1 + ancho2

        if ancho_total > bobina_ancho:
            return {
                'eficiencia': 0,
                'sobrante': bobina_ancho,
                'metros_lineales': 0,
                'cortes_totales': 0
            }

        MARGEN_SEGURIDAD = 30
        num_ordenes = 2
        espacio_por_orden = (bobina_ancho - MARGEN_SEGURIDAD) / num_ordenes

        sobrante1 = espacio_por_orden - ancho1
        sobrante2 = espacio_por_orden - ancho2
        sobrante_total = sobrante1 + sobrante2

        eficiencia = round((ancho_total / bobina_ancho) * 100)

        # Calcular metros lineales
        cavidad_efectiva1 = orden1.cavidad * mult1 if orden1.cavidad else mult1
        cavidad_efectiva2 = orden2.cavidad * mult2 if orden2.cavidad else mult2

        metros1 = 0
        cortes1 = 0
        if cavidad_efectiva1 > 0 and orden1.largo_calculado:
            cortes1 = faltante1 / cavidad_efectiva1
            metros1 = (cortes1 * orden1.largo_calculado) / 1000

        metros2 = 0
        cortes2 = 0
        if cavidad_efectiva2 > 0 and orden2.largo_calculado:
            cortes2 = orden2.cantidad / cavidad_efectiva2
            metros2 = (cortes2 * orden2.largo_calculado) / 1000

        return {
            'eficiencia': eficiencia,
            'sobrante': sobrante_total,
            'metros_lineales': max(metros1, metros2),  # En duplas se usa el mayor
            'cortes_totales': cortes1 + cortes2
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

        # IMPORTANTE: Ordenar bobinas de MENOR a MAYOR para encontrar la más pequeña que quepa
        bobinas_ordenadas = sorted(bobinas)

        # Probar combinaciones individuales con diferentes multiplicadores de cavidad
        for multiplicador in range(1, cavidad_limite + 1):
            ancho_util = orden_principal.ancho_calculado * multiplicador

            for bobina in bobinas_ordenadas:
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

                    for bobina in bobinas_ordenadas:
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
        # SIN redondeo (descomentar si NO se requiere redondeo):
        # eficiencia = (ancho_total_utilizado / bobina_ancho) * 100
        # CON redondeo (comentar si NO se requiere redondeo):
        eficiencia = round((ancho_total_utilizado / bobina_ancho) * 100)

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

        # SIN redondeo (descomentar si NO se requiere redondeo):
        # eficiencia_redondeada = eficiencia_final
        # CON redondeo (comentar si NO se requiere redondeo):
        eficiencia_redondeada = round(eficiencia_final)

        return {
            'eficiencia': eficiencia_redondeada,
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
        print(f"\n{'='*80}")
        print(f"[_APLICAR_COMBINACION] INICIO - {grupo_nombre}")
        print(f"  Tipo combinación: {combinacion.get('tipo')}")
        print(f"  Número de órdenes: {len(combinacion.get('ordenes', []))}")
        print(f"{'='*80}\n")

        # VALIDACIÓN PREVENTIVA: Filtrar órdenes que ya tienen grupo asignado
        ordenes_disponibles = []
        for orden_data in combinacion['ordenes']:
            orden = orden_data['orden']
            if not orden.grupo_planificacion:
                ordenes_disponibles.append(orden_data)
            else:
                print(f"[ADVERTENCIA] {grupo_nombre}: Orden {orden.orden_produccion} ya está en {orden.grupo_planificacion}, omitiendo")

        # Si no quedan órdenes disponibles, abortar
        if not ordenes_disponibles:
            print(f"[ERROR] {grupo_nombre}: No hay órdenes disponibles para aplicar, abortando")
            return

        # Actualizar la combinación con solo las órdenes disponibles
        combinacion['ordenes'] = ordenes_disponibles

        # Calcular sobrante individual para cada orden
        MARGEN_SEGURIDAD = 30
        num_ordenes = len(combinacion['ordenes'])

        # CORRECCIÓN DE BUG: Si solo hay 1 orden, forzar tipo 'individual'
        # Esto previene inconsistencias donde una dupla perdió una orden
        if num_ordenes == 1:
            if combinacion['tipo'] != 'individual':
                print(f"[BUG FIX] {grupo_nombre}: Corrigiendo tipo '{combinacion['tipo']}' → 'individual' (solo 1 pedido)")
            combinacion['tipo'] = 'individual'

        # VALIDACIÓN ADICIONAL: Si el tipo es 'dupla', DEBE haber exactamente 2 órdenes
        elif combinacion['tipo'] == 'dupla' and num_ordenes != 2:
            print(f"[ERROR CRÍTICO] {grupo_nombre}: Tipo 'dupla' con {num_ordenes} órdenes (debe ser exactamente 2)")
            # Forzar a individual si no son exactamente 2
            combinacion['tipo'] = 'individual'

        espacio_por_orden = (combinacion['bobina'] - MARGEN_SEGURIDAD) / num_ordenes

        # Para DUPLAS: Identificar el pedido con menor cantidad
        orden_menor = None
        orden_mayor = None
        metros_lineales_menor = 0

        if combinacion['tipo'] == 'dupla' and num_ordenes == 2:
            # Identificar cuál orden tiene menor cantidad
            orden1 = combinacion['ordenes'][0]['orden']
            orden2 = combinacion['ordenes'][1]['orden']

            if orden1.cantidad <= orden2.cantidad:
                orden_menor = orden1
                orden_mayor = orden2
            else:
                orden_menor = orden2
                orden_mayor = orden1

        # Primera pasada: Calcular orden con cantidad menor (o todas si es individual)
        for orden_data in combinacion['ordenes']:
            orden = orden_data['orden']
            multiplicador = orden_data.get('multiplicador', 1)
            ancho_efectivo = orden_data.get('ancho_efectivo', orden.ancho_calculado)

            # Calcular sobrante individual de esta orden
            # SIN redondeo (descomentar si NO se requiere redondeo):
            # sobrante_individual = espacio_por_orden - ancho_efectivo
            # CON redondeo (comentar si NO se requiere redondeo):
            sobrante_individual = round(espacio_por_orden - ancho_efectivo)

            # Si es DUPLA y esta es la orden MAYOR, saltarla por ahora
            if combinacion['tipo'] == 'dupla' and orden.id == orden_mayor.id:
                continue

            # Calcular valores de planificación según especificaciones:
            # cavidad_efectiva = cavidad * multiplicador
            cavidad_efectiva = orden.cavidad * multiplicador if orden.cavidad else multiplicador

            # 1. cortes_planificados = cantidad / cavidad_efectiva
            # Usar ceil para asegurar que se produzca al menos la cantidad solicitada
            # pero sin exceder el umbral de faltante aceptable (< 500)
            import math
            if cavidad_efectiva > 0:
                # Calcular con cantidad_override si existe (para faltantes)
                cantidad_a_usar = orden_data.get('cantidad_override', orden.cantidad)
                cortes_exactos = cantidad_a_usar / cavidad_efectiva
                cortes_planificados = int(cortes_exactos)  # Truncar, no redondear

                # Solo agregar un corte extra si el faltante resultante sería >= 500
                faltante_potencial = cantidad_a_usar - (cortes_planificados * cavidad_efectiva)
                if faltante_potencial >= 500:
                    cortes_planificados += 1
            else:
                cortes_planificados = 0

            # 2. cantidad_planificada = cortes_planificados * cavidad_efectiva
            cantidad_planificada = cortes_planificados * cavidad_efectiva

            # 3. metros_lineales_planificados = ((cantidad_planificada * largo_calculado) / cavidad_efectiva) / 1000
            metros_lineales_planificados = 0
            if cavidad_efectiva > 0 and orden.largo_calculado:
                # SIN redondeo (descomentar si NO se requiere redondeo):
                # metros_lineales_planificados = ((cantidad_planificada * orden.largo_calculado) / cavidad_efectiva) / 1000
                # CON redondeo (comentar si NO se requiere redondeo):
                metros_lineales_planificados = round(((cantidad_planificada * orden.largo_calculado) / cavidad_efectiva) / 1000)

            # Guardar metros_lineales de la orden menor para usar en el cálculo de la orden mayor
            if combinacion['tipo'] == 'dupla' and orden.id == orden_menor.id:
                metros_lineales_menor = metros_lineales_planificados

            # VALIDACIÓN FINAL: Verificar consistencia antes de escribir
            tipo_final = combinacion['tipo']
            if tipo_final == 'dupla' and len(combinacion['ordenes']) != 2:
                print(f"[ERROR CRÍTICO] Intentando escribir tipo 'dupla' con {len(combinacion['ordenes'])} órdenes. Corrigiendo a 'individual'")
                tipo_final = 'individual'
            elif tipo_final == 'individual' and len(combinacion['ordenes']) > 1:
                print(f"[ADVERTENCIA] Tipo 'individual' con {len(combinacion['ordenes'])} órdenes")

            orden.write({
                'grupo_planificacion': grupo_nombre,
                'tipo_combinacion': tipo_final,
                'ancho_utilizado': combinacion['ancho_utilizado'],
                'bobina_utilizada': combinacion['bobina'],
                'sobrante': sobrante_individual,
                'eficiencia': combinacion['eficiencia'],
                'metros_lineales_planificados': metros_lineales_planificados,
                'cortes_planificados': cortes_planificados,
                'cantidad_planificada': cantidad_planificada,
                'cavidad_optimizada': multiplicador,
            })

        # Segunda pasada: Calcular orden MAYOR en duplas con fórmula especial
        if combinacion['tipo'] == 'dupla' and orden_mayor:
            # Encontrar orden_data del pedido mayor
            orden_mayor_data = None
            for od in combinacion['ordenes']:
                if od['orden'].id == orden_mayor.id:
                    orden_mayor_data = od
                    break

            if orden_mayor_data:
                multiplicador = orden_mayor_data.get('multiplicador', 1)
                ancho_efectivo = orden_mayor_data.get('ancho_efectivo', orden_mayor.ancho_calculado)
                # SIN redondeo (descomentar si NO se requiere redondeo):
                # sobrante_individual = espacio_por_orden - ancho_efectivo
                # CON redondeo (comentar si NO se requiere redondeo):
                sobrante_individual = round(espacio_por_orden - ancho_efectivo)

                # Fórmula especial para el pedido de cantidad mayor:
                # cantidad_planificada = ((metros_lineales_menor / largo_calculado_mayor) * 1000)
                # IMPORTANTE: Limitar a la cantidad original para evitar faltantes negativos
                cantidad_planificada = 0
                if orden_mayor.largo_calculado and orden_mayor.largo_calculado > 0:
                    import math
                    cantidad_calculada = int((metros_lineales_menor / orden_mayor.largo_calculado) * 1000)
                    # NO exceder la cantidad original del pedido
                    cantidad_planificada = min(cantidad_calculada, orden_mayor.cantidad)

                # Para este pedido, cortes_planificados se calcula al revés desde cantidad_planificada
                cavidad_efectiva = orden_mayor.cavidad * multiplicador if orden_mayor.cavidad else multiplicador
                # Usar int() para evitar sobrepasarse de la cantidad planificada
                cortes_planificados = int(cantidad_planificada / cavidad_efectiva) if cavidad_efectiva > 0 else 0

                # metros_lineales_planificados usa la fórmula estándar
                metros_lineales_planificados = 0
                if cavidad_efectiva > 0 and orden_mayor.largo_calculado:
                    # SIN redondeo (descomentar si NO se requiere redondeo):
                    # metros_lineales_planificados = ((cantidad_planificada * orden_mayor.largo_calculado) / cavidad_efectiva) / 1000
                    # CON redondeo (comentar si NO se requiere redondeo):
                    metros_lineales_planificados = round(((cantidad_planificada * orden_mayor.largo_calculado) / cavidad_efectiva) / 1000)

                # VALIDACIÓN FINAL: Verificar consistencia antes de escribir
                tipo_final = combinacion['tipo']
                if tipo_final == 'dupla' and len(combinacion['ordenes']) != 2:
                    print(f"[ERROR CRÍTICO] Orden mayor: Intentando escribir tipo 'dupla' con {len(combinacion['ordenes'])} órdenes. Corrigiendo a 'individual'")
                    tipo_final = 'individual'

                orden_mayor.write({
                    'grupo_planificacion': grupo_nombre,
                    'tipo_combinacion': tipo_final,
                    'ancho_utilizado': combinacion['ancho_utilizado'],
                    'bobina_utilizada': combinacion['bobina'],
                    'sobrante': sobrante_individual,
                    'eficiencia': combinacion['eficiencia'],
                    'metros_lineales_planificados': metros_lineales_planificados,
                    'cortes_planificados': cortes_planificados,
                    'cantidad_planificada': cantidad_planificada,
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
