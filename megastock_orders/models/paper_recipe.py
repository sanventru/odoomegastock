# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError

class PaperRecipe(models.Model):
    _name = 'megastock.paper.recipe'
    _description = 'Receta de Papel y Test de Resistencia MEGASTOCK'
    _order = 'test_name, ect_value'
    _rec_name = 'test_name'

    # ========== CAMPOS PRINCIPALES ==========

    test_name = fields.Char(
        string='Nombre del Test',
        required=True,
        help='Nombre del test (ej: Test 150, Test 200, etc.)'
    )

    ect_value = fields.Float(
        string='Valor ECT',
        required=True,
        help='Valor de resistencia ECT del test'
    )

    # Gramajes por capa de papel (g/m²)
    liner_interno_gm = fields.Float(
        string='Liner Interno (g/m²)',
        required=True,
        help='Gramaje del liner interno en gramos por metro cuadrado'
    )

    corrugado_medio_gm = fields.Float(
        string='Corrugado Medio (g/m²)',
        required=True,
        help='Gramaje del corrugado medio en gramos por metro cuadrado'
    )

    liner_externo_gm = fields.Float(
        string='Liner Externo (g/m²)',
        required=True,
        help='Gramaje del liner externo en gramos por metro cuadrado'
    )

    # ========== CAMPOS CALCULADOS ==========

    gramaje_combinado = fields.Float(
        string='Gramaje Combinado (g/m²)',
        compute='_compute_gramaje_combinado',
        store=True,
        help='Gramaje total: LI + (CM * 1.45) + LE'
    )

    gramaje_tolerancia_min = fields.Float(
        string='Tolerancia Mínima (-3%)',
        compute='_compute_tolerancias',
        store=True,
        help='Gramaje mínimo permitido (gramaje_combinado - 3%)'
    )

    gramaje_tolerancia_max = fields.Float(
        string='Tolerancia Máxima (+3%)',
        compute='_compute_tolerancias',
        store=True,
        help='Gramaje máximo permitido (gramaje_combinado + 3%)'
    )

    # ========== CAMPOS ADICIONALES ==========

    factor_corrugador = fields.Float(
        string='Factor Corrugador',
        default=1.45,
        help='Factor de conversión para corrugado medio (default: 1.45)'
    )

    active = fields.Boolean(
        string='Activo',
        default=True,
        help='Test activo y disponible para uso'
    )

    descripcion = fields.Text(
        string='Descripción',
        help='Descripción adicional del test y sus características'
    )

    # ========== MÉTODOS COMPUTED ==========

    @api.depends('liner_interno_gm', 'corrugado_medio_gm', 'liner_externo_gm', 'factor_corrugador')
    def _compute_gramaje_combinado(self):
        """Calcular gramaje combinado: LI + (CM * factor) + LE"""
        for record in self:
            if record.liner_interno_gm and record.corrugado_medio_gm and record.liner_externo_gm:
                record.gramaje_combinado = (
                    record.liner_interno_gm +
                    (record.corrugado_medio_gm * record.factor_corrugador) +
                    record.liner_externo_gm
                )
            else:
                record.gramaje_combinado = 0.0

    @api.depends('gramaje_combinado')
    def _compute_tolerancias(self):
        """Calcular tolerancias ±3% del gramaje combinado"""
        for record in self:
            if record.gramaje_combinado:
                tolerancia = record.gramaje_combinado * 0.03  # 3%
                record.gramaje_tolerancia_min = record.gramaje_combinado - tolerancia
                record.gramaje_tolerancia_max = record.gramaje_combinado + tolerancia
            else:
                record.gramaje_tolerancia_min = 0.0
                record.gramaje_tolerancia_max = 0.0

    # ========== CONSTRAINTS Y VALIDACIONES ==========

    @api.constrains('ect_value')
    def _check_ect_value(self):
        """Validar que ECT sea positivo"""
        for record in self:
            if record.ect_value <= 0:
                raise ValidationError('El valor ECT debe ser mayor a 0')

    @api.constrains('liner_interno_gm', 'corrugado_medio_gm', 'liner_externo_gm')
    def _check_gramajes(self):
        """Validar que todos los gramajes sean positivos"""
        for record in self:
            if record.liner_interno_gm <= 0:
                raise ValidationError('El gramaje del Liner Interno debe ser mayor a 0')
            if record.corrugado_medio_gm <= 0:
                raise ValidationError('El gramaje del Corrugado Medio debe ser mayor a 0')
            if record.liner_externo_gm <= 0:
                raise ValidationError('El gramaje del Liner Externo debe ser mayor a 0')

    @api.constrains('test_name')
    def _check_test_name_unique(self):
        """Validar que el nombre del test sea único"""
        for record in self:
            if record.test_name:
                existing = self.search([
                    ('test_name', '=', record.test_name),
                    ('id', '!=', record.id)
                ])
                if existing:
                    raise ValidationError(f'Ya existe un test con el nombre "{record.test_name}"')

    # ========== MÉTODOS DE NEGOCIO ==========

    def name_get(self):
        """Mostrar nombre personalizado en relaciones"""
        result = []
        for record in self:
            name = f"{record.test_name} (ECT: {record.ect_value}) - {record.gramaje_combinado:.1f} g/m²"
            result.append((record.id, name))
        return result

    def get_paper_consumption_ratios(self):
        """Obtener ratios de consumo por tipo de papel"""
        self.ensure_one()
        if not self.gramaje_combinado:
            return {'li': 0, 'cm': 0, 'le': 0}

        total = self.gramaje_combinado
        return {
            'li': self.liner_interno_gm / total,
            'cm': (self.corrugado_medio_gm * self.factor_corrugador) / total,
            'le': self.liner_externo_gm / total
        }

    def validate_gramaje_tolerance(self, gramaje_test):
        """Validar si un gramaje está dentro de la tolerancia ±3%"""
        self.ensure_one()
        return self.gramaje_tolerancia_min <= gramaje_test <= self.gramaje_tolerancia_max

    @api.model
    def get_available_tests(self):
        """Obtener tests disponibles para selección"""
        return self.search([('active', '=', True)]).read(['id', 'test_name', 'ect_value', 'gramaje_combinado'])

    # ========== MÉTODOS DE CREACIÓN MASIVA ==========

    @api.model
    def create_standard_tests(self):
        """Crear tests estándar basados en recetas.csv"""
        standard_tests = [
            {
                'test_name': 'Test 150',
                'ect_value': 26,
                'liner_interno_gm': 150,
                'corrugado_medio_gm': 160,
                'liner_externo_gm': 150,
                'descripcion': 'Test estándar 150 - Uso general'
            },
            {
                'test_name': 'Test 175',
                'ect_value': 29,
                'liner_interno_gm': 175,
                'corrugado_medio_gm': 160,
                'liner_externo_gm': 175,
                'descripcion': 'Test estándar 175 - Resistencia media'
            },
            {
                'test_name': 'Test 200',
                'ect_value': 32,
                'liner_interno_gm': 200,
                'corrugado_medio_gm': 180,
                'liner_externo_gm': 200,
                'descripcion': 'Test estándar 200 - Alta resistencia'
            },
            {
                'test_name': 'Test 250',
                'ect_value': 40,
                'liner_interno_gm': 225,
                'corrugado_medio_gm': 180,
                'liner_externo_gm': 225,
                'descripcion': 'Test estándar 250 - Muy alta resistencia'
            },
            {
                'test_name': 'Test 275',
                'ect_value': 44,
                'liner_interno_gm': 250,
                'corrugado_medio_gm': 160,
                'liner_externo_gm': 250,
                'descripcion': 'Test estándar 275 - Máxima resistencia'
            }
        ]

        created_tests = []
        for test_data in standard_tests:
            # Verificar si ya existe
            existing = self.search([('test_name', '=', test_data['test_name'])])
            if not existing:
                created_test = self.create(test_data)
                created_tests.append(created_test)

        return created_tests