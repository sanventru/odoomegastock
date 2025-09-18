# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime

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
    cantidad = fields.Integer(string='Cantidad')
    cavidad = fields.Integer(string='Cavidad')
    
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
    ancho_utilizado = fields.Float(string='Ancho Utilizado (mm)', help='Ancho total utilizado en la bobina')
    bobina_utilizada = fields.Float(string='Bobina Utilizada (mm)', help='Ancho de bobina utilizada')
    sobrante = fields.Float(string='Sobrante (mm)', help='Material sobrante después del corte')
    eficiencia = fields.Float(string='Eficiencia (%)', help='Porcentaje de eficiencia del material calculado con algoritmo avanzado')
    metros_lineales_planificados = fields.Float(string='Metros Lineales Planificados', help='Metros lineales calculados para la planificación')
    cortes_planificados = fields.Integer(string='Cortes Planificados', help='Total de cortes calculados en la planificación')
    
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

    def _optimizar_ordenes(self, ordenes):
        """Algoritmo de optimización basado en el archivo Excel de trimado"""
        # Obtener anchos de bobina disponibles desde la configuración
        Bobina = self.env['megastock.bobina']
        bobinas_disponibles = Bobina.get_bobinas_activas()

        # Si no hay bobinas configuradas, usar valores por defecto
        if not bobinas_disponibles:
            Bobina.create_default_bobinas()
            bobinas_disponibles = Bobina.get_bobinas_activas()
        
        # Agrupar órdenes por características similares
        grupos_optimizados = []
        ordenes_procesadas = set()
        grupo_counter = 1
        
        for orden in ordenes:
            if orden.id in ordenes_procesadas:
                continue
                
            # Buscar combinaciones óptimas
            mejor_combinacion = self._encontrar_mejor_combinacion(orden, ordenes, ordenes_procesadas, bobinas_disponibles)
            
            if mejor_combinacion:
                # Aplicar la combinación encontrada
                self._aplicar_combinacion(mejor_combinacion, grupo_counter)
                grupos_optimizados.append(mejor_combinacion)
                
                # Marcar órdenes como procesadas
                for orden_comb in mejor_combinacion['ordenes']:
                    ordenes_procesadas.add(orden_comb.id)
                
                grupo_counter += 1
        
        # Calcular estadísticas
        eficiencia_total = sum(grupo['eficiencia'] for grupo in grupos_optimizados)
        eficiencia_promedio = eficiencia_total / len(grupos_optimizados) if grupos_optimizados else 0
        
        return {
            'grupos': len(grupos_optimizados),
            'eficiencia_promedio': eficiencia_promedio
        }

    def _encontrar_mejor_combinacion(self, orden_principal, todas_ordenes, procesadas, bobinas):
        """Encuentra la mejor combinación para una orden principal"""
        mejor_combinacion = None
        mejor_eficiencia = 0
        
        # Probar combinación individual
        for bobina in bobinas:
            if orden_principal.ancho <= (bobina - 30):
                resultado = self._calcular_eficiencia_real([orden_principal], bobina)
                
                if resultado['eficiencia'] > mejor_eficiencia:
                    mejor_eficiencia = resultado['eficiencia']
                    mejor_combinacion = {
                        'ordenes': [orden_principal],
                        'tipo': 'individual',
                        'bobina': bobina,
                        'ancho_utilizado': orden_principal.ancho,
                        'sobrante': resultado['sobrante'],
                        'eficiencia': resultado['eficiencia'],
                        'metros_lineales': resultado['metros_lineales'],
                        'cortes_totales': resultado['cortes_totales']
                    }
        
        # Probar duplas
        for orden2 in todas_ordenes:
            if orden2.id == orden_principal.id or orden2.id in procesadas:
                continue
                
            ordenes_dupla = [orden_principal, orden2]
            ancho_total = sum(orden.ancho for orden in ordenes_dupla)
            
            for bobina in bobinas:
                if ancho_total <= bobina:
                    resultado = self._calcular_eficiencia_real(ordenes_dupla, bobina)
                    
                    if resultado['eficiencia'] > mejor_eficiencia:
                        mejor_eficiencia = resultado['eficiencia']
                        mejor_combinacion = {
                            'ordenes': ordenes_dupla,
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

    def _calcular_eficiencia_real(self, ordenes, bobina_ancho):
        """Calcula la eficiencia real basada en el algoritmo del Excel de trimado"""
        # Calcular totales de las órdenes
        ancho_total_utilizado = sum(orden.ancho for orden in ordenes)
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
        
        # Calcular metros lineales necesarios
        # Basado en la fórmula del Excel: cantidad / cavidad * largo (convertido a metros)
        metros_lineales = 0
        for orden in ordenes:
            if orden.cavidad and orden.cavidad > 0:
                cortes_necesarios = orden.cantidad / orden.cavidad
                metros_por_orden = (cortes_necesarios * orden.largo) / 1000  # mm a metros
                metros_lineales += metros_por_orden
        
        # Calcular eficiencia base (aprovechamiento de la bobina)
        eficiencia_base = (ancho_total_utilizado / bobina_ancho) * 100
        
        # Aplicar ajustes aditivos (no multiplicativos)
        eficiencia_final = eficiencia_base
        
        # Factor 1: Bonus por combinaciones (aditivo, no multiplicativo)
        if len(ordenes) == 2:  # Dupla
            eficiencia_final += 5  # +5% bonus
        # Las triplas no son posibles debido a limitaciones de máquinas corrugadoras
        
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
        """Aplica la combinación encontrada a las órdenes"""
        grupo_nombre = f"GRUPO-{grupo_id:03d}"
        
        for orden in combinacion['ordenes']:
            orden.write({
                'grupo_planificacion': grupo_nombre,
                'tipo_combinacion': combinacion['tipo'],
                'ancho_utilizado': combinacion['ancho_utilizado'],
                'bobina_utilizada': combinacion['bobina'],
                'sobrante': combinacion['sobrante'],
                'eficiencia': combinacion['eficiencia'],
                'metros_lineales_planificados': combinacion.get('metros_lineales', 0),
                'cortes_planificados': combinacion.get('cortes_totales', 0),
            })

    def action_generar_ordenes_trabajo(self):
        """Acción para generar órdenes de trabajo desde grupos planificados"""
        # Buscar todas las órdenes que tienen grupo de planificación pero no tienen orden de trabajo
        ordenes_planificadas = self.search([
            ('grupo_planificacion', '!=', False),
            ('work_order_id', '=', False)
        ])
        
        if not ordenes_planificadas:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Sin órdenes planificadas',
                    'message': 'No hay órdenes planificadas sin orden de trabajo para procesar.',
                    'type': 'warning',
                }
            }
        
        # Agrupar por grupo_planificacion
        grupos = {}
        for orden in ordenes_planificadas:
            grupo = orden.grupo_planificacion
            if grupo not in grupos:
                grupos[grupo] = []
            grupos[grupo].append(orden)
        
        # Crear órdenes de trabajo para cada grupo
        ordenes_trabajo_creadas = []
        WorkOrder = self.env['megastock.work.order']
        
        for grupo_nombre, ordenes_grupo in grupos.items():
            # Calcular datos del grupo
            primer_orden = ordenes_grupo[0]
            metros_lineales_totales = sum(orden.metros_lineales_planificados for orden in ordenes_grupo)
            cortes_totales = sum(orden.cortes_planificados for orden in ordenes_grupo)
            
            # Crear la orden de trabajo
            work_order = WorkOrder.create({
                'grupo_planificacion': grupo_nombre,
                'tipo_combinacion': primer_orden.tipo_combinacion,
                'bobina_utilizada': primer_orden.bobina_utilizada,
                'ancho_utilizado': primer_orden.ancho_utilizado,
                'sobrante': primer_orden.sobrante,
                'eficiencia': primer_orden.eficiencia,
                'metros_lineales_totales': metros_lineales_totales,
                'cortes_totales': cortes_totales,
                'fecha_programada': primer_orden.fecha_produccion,
                'observaciones': f'Generada automáticamente desde {len(ordenes_grupo)} órdenes de producción del grupo {grupo_nombre}',
            })
            
            # Asignar la orden de trabajo a todas las órdenes del grupo y cambiar estado
            for orden in ordenes_grupo:
                orden.write({
                    'work_order_id': work_order.id,
                    'estado': 'ot'
                })
            
            ordenes_trabajo_creadas.append(work_order)
        
        # Mostrar resultado
        mensaje = f'Se han creado {len(ordenes_trabajo_creadas)} órdenes de trabajo desde {len(grupos)} grupos planificados.'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Órdenes de trabajo generadas',
                'message': mensaje,
                'type': 'success',
            }
        }
