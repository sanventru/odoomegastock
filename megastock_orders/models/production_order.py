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
    numero_troquel = fields.Char(string='Número de Troquel')
    ect_minimo = fields.Float(string='ECT Mínimo')
    ect_real = fields.Float(string='ECT Real')
    peso = fields.Float(string='Peso')
    
    # Cantidad entregada
    cantidad_entregada = fields.Integer(string='Cantidad Entregada')
    
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
    
    @api.onchange('liner_externo_ancho', 'liner_externo_gm', 'metros_lineales')
    def _onchange_liner_externo(self):
        """Actualizar cantidad liner externo cuando cambien sus parámetros"""
        if self.liner_externo_ancho and self.liner_externo_gm and self.metros_lineales:
            self.cantidad_liner_externo = (self.liner_externo_ancho * self.liner_externo_gm) * (self.metros_lineales / 1000000)
        else:
            self.cantidad_liner_externo = 0.0
    
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
