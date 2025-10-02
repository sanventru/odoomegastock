# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
import math

class MegastockWeightCalculator(models.TransientModel):
    _name = 'megastock.weight.calculator'
    _description = 'Motor de Cálculo de Pesos y Consumos MEGASTOCK'

    # Campos de ejemplo para testing
    test_largo = fields.Float(string='Largo Test (mm)')
    test_ancho = fields.Float(string='Ancho Test (mm)')
    test_gramaje = fields.Float(string='Gramaje Test (g/m²)', default=200.0)
    resultado_peso = fields.Float(string='Peso Calculado (g)', readonly=True)

    def calculate_sheet_weight_basic(self):
        """
        Método de prueba para calcular peso de lámina
        PASO 1: Cálculo con gramaje personalizable
        """
        # Validación de campos requeridos
        if not self.test_largo or not self.test_ancho:
            raise UserError("Por favor ingresa valores de Largo y Ancho antes de calcular")

        if self.test_largo <= 0 or self.test_ancho <= 0:
            raise UserError("Largo y ancho deben ser mayores a cero")

        # Usar gramaje del campo o valor por defecto
        gramaje = self.test_gramaje if self.test_gramaje > 0 else 200.0

        # Área en m²
        area_m2 = (self.test_largo * self.test_ancho) / 1000000

        # Peso en gramos
        peso_gramos = area_m2 * gramaje

        # Actualizar campo resultado
        self.resultado_peso = peso_gramos

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Cálculo Completado',
                'message': f'Peso calculado: {peso_gramos:.2f}g\nÁrea: {area_m2:.4f}m²\nGramaje: {gramaje}g/m²',
                'type': 'success',
                'sticky': True,
            }
        }

    def calculate_sheet_weight(self, largo_mm, ancho_mm, gramaje_gm2=200.0):
        """
        Calcula peso de una lámina según dimensiones y gramaje
        Retorna peso en gramos - VERSION SIMPLIFICADA
        """
        if not largo_mm or not ancho_mm or gramaje_gm2 <= 0:
            return 0.0

        # Área en m²
        area_m2 = (largo_mm * ancho_mm) / 1000000

        # Peso = área * gramaje
        peso_gramos = area_m2 * gramaje_gm2

        return peso_gramos

    def get_calculation_info(self):
        """
        Método para mostrar información del calculador
        """
        return {
            'name': 'MEGASTOCK Weight Calculator',
            'version': '1.0',
            'status': 'Fase 3 - Paso 1 Completado'
        }