# -*- coding: utf-8 -*-

from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    # Campo de código MEGASTOCK
    megastock_code = fields.Char(string='Código MEGASTOCK', help='Código interno del producto MEGASTOCK')
    
    # Campos básicos MEGASTOCK sin funcionalidades complejas
    megastock_category = fields.Selection([
        ('cajas', 'CAJAS'),
        ('laminas', 'LÁMINAS'),
        ('papel', 'PAPEL PERIÓDICO'),
        ('planchas', 'PLANCHAS'),
        ('separadores', 'SEPARADORES'),
        ('materias_primas', 'MATERIAS PRIMAS'),
    ], string='Categoría MEGASTOCK')
    
    # Dimensiones
    largo_cm = fields.Float(string='Largo (cm)')
    ancho_cm = fields.Float(string='Ancho (cm)')
    alto_cm = fields.Float(string='Alto (cm)')
    ceja_cm = fields.Float(string='Ceja (cm)', help='Medida de la ceja del producto')
    
    # Especificaciones generales
    flauta = fields.Selection([
        ('c', 'C'),
        ('b', 'B'), 
        ('e', 'E'),
    ], string='Flauta')
    
    material_type = fields.Selection([
        ('kraft', 'KRAFT'),
        ('interstock', 'INTERSTOCK'),
        ('monus', 'MONUS'),
        ('westrock', 'WESTROCK'),
    ], string='Material')
    
    # Campos técnicos específicos
    test_value = fields.Float(string='Test Value (lbs)', help='Resistencia al aplastamiento en libras')
    test_value_lbs = fields.Float(string='Test Value (lbs)', help='Resistencia al aplastamiento en libras')
    kl_value = fields.Float(string='KL Value', help='Resistencia al punzonado')
    gramaje = fields.Float(string='Gramaje (g/m²)', help='Peso del papel por metro cuadrado')
    
    # Colores de impresión como selección
    colors_printing = fields.Selection([
        ('sin_impresion', 'Sin Impresión'),
        ('negro', '1 Color - Negro'),
        ('negro_azul', '2 Colores - Negro + Azul'),
        ('negro_rojo', '2 Colores - Negro + Rojo'),
        ('cmyk_3', '3 Colores - CMY'),
        ('cmyk_full', '4 Colores - CMYK Full'),
        ('cmyk_plus1', '5 Colores - CMYK + 1 Pantone'),
        ('cmyk_plus2', '6 Colores - CMYK + 2 Pantone'),
        ('pantone_especial', 'Pantone Especial'),
        ('multicolor', 'Multicolor (7+ colores)'),
    ], string='Colores de Impresión', help='Configuración de tintas para impresión')
    
    colores_impresion = fields.Selection([
        ('sin_impresion', 'Sin Impresión'),
        ('negro', '1 Color - Negro'),
        ('negro_azul', '2 Colores - Negro + Azul'),
        ('negro_rojo', '2 Colores - Negro + Rojo'),
        ('cmyk_3', '3 Colores - CMY'),
        ('cmyk_full', '4 Colores - CMYK Full'),
        ('cmyk_plus1', '5 Colores - CMYK + 1 Pantone'),
        ('cmyk_plus2', '6 Colores - CMYK + 2 Pantone'),
        ('pantone_especial', 'Pantone Especial'),
        ('multicolor', 'Multicolor (7+ colores)'),
    ], string='Colores de Impresión', help='Configuración de tintas para impresión')
    
    # Campos específicos para CAJAS
    tipo_caja = fields.Selection([
        ('tapa_fondo', 'Tapa y Fondo'),
        ('jumbo', 'Jumbo'),
        ('exportacion', 'Exportación'),
        ('americana', 'Americana'),
    ], string='Tipo de Caja')
    
    capacidad_kg = fields.Float(string='Capacidad (kg)', help='Peso máximo que puede soportar')
    resistencia_edge = fields.Float(string='Resistencia Edge (kgf/cm)', help='Resistencia al aplastamiento')
    tipo_troquelado = fields.Selection([
        ('0200', 'Caja Regular 0200'),
        ('0201', 'Caja Regular 0201'),
        ('0202', 'Caja Regular 0202'),
        ('especial', 'Troquelado Especial'),
    ], string='Tipo de Troquelado')
    
    # Campos específicos para LÁMINAS
    calibre_lamina = fields.Float(string='Calibre', help='Grosor de la lámina')
    acabado_superficie = fields.Selection([
        ('lisa', 'Lisa'),
        ('texturizada', 'Texturizada'),
        ('brillante', 'Brillante'),
        ('mate', 'Mate'),
    ], string='Acabado de Superficie')
    
    # Campos específicos para PAPEL PERIÓDICO
    gramaje = fields.Float(string='Gramaje (g/m²)', help='Peso del papel por metro cuadrado')
    blancura = fields.Float(string='Blancura (%)', help='Porcentaje de blancura del papel')
    
    # Campos específicos para PLANCHAS
    espesor_plancha = fields.Float(string='Espesor (mm)', help='Grosor de la plancha')
    densidad = fields.Float(string='Densidad (kg/m³)', help='Densidad del material')
    
    # Campos específicos para SEPARADORES
    perforacion = fields.Boolean(string='Perforación', help='Tiene perforación para fácil separación')
    adhesivo = fields.Selection([
        ('ninguno', 'Sin Adhesivo'),
        ('removible', 'Adhesivo Removible'),
        ('permanente', 'Adhesivo Permanente'),
    ], string='Tipo de Adhesivo')
    
    # Campos específicos para MATERIAS PRIMAS
    origen_material = fields.Selection([
        ('nacional', 'Nacional'),
        ('importado', 'Importado'),
        ('reciclado', 'Reciclado'),
    ], string='Origen del Material')
    pureza = fields.Float(string='Pureza (%)', help='Porcentaje de pureza del material')