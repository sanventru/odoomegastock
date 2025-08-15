# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, timedelta
import json

class ProductionKpi(models.Model):
    _name = 'megastock.production.kpi'
    _description = 'KPI de Producción MEGASTOCK'
    _order = 'measurement_date desc'

    name = fields.Char(string='Nombre KPI', required=True)
    measurement_date = fields.Date(string='Fecha Medición', required=True, default=fields.Date.today)
    production_line = fields.Selection([
        ('cajas', 'Línea CAJAS'),
        ('laminas', 'Línea LÁMINAS'),
        ('papel', 'Línea PAPEL PERIÓDICO'),
        ('all', 'Todas las Líneas')
    ], string='Línea de Producción', default='all')
    
    # KPIs básicos
    oee_percentage = fields.Float(string='OEE %', digits=(5, 2))
    availability_percentage = fields.Float(string='Disponibilidad %', digits=(5, 2))
    performance_percentage = fields.Float(string='Performance %', digits=(5, 2))
    quality_percentage = fields.Float(string='Calidad %', digits=(5, 2))
    on_time_delivery_rate = fields.Float(string='Entregas a Tiempo %', digits=(5, 2))
    utilization_rate = fields.Float(string='Tasa Utilización %', digits=(5, 2))
    
    # Estados y alertas
    alert_level = fields.Selection([
        ('green', 'Verde - Normal'),
        ('yellow', 'Amarillo - Atención'),
        ('red', 'Rojo - Crítico')
    ], string='Nivel de Alerta', default='green')
    
    notes = fields.Text(string='Observaciones')

    @api.model
    def get_dashboard_data(self, line_filter='all'):
        """Obtener datos para el dashboard"""
        domain = [('measurement_date', '>=', fields.Date.today() - timedelta(days=7))]
        if line_filter and line_filter != 'all':
            domain.append(('production_line', '=', line_filter))
        
        kpis = self.search(domain, limit=50)
        
        # Calcular promedios
        total_records = len(kpis)
        if total_records == 0:
            return {
                'summary': {
                    'oee': 0, 'availability': 0, 'performance': 0,
                    'quality': 0, 'delivery': 0, 'utilization': 0
                },
                'alerts': [],
                'trend_data': [],
                'workcenters': []
            }
        
        summary = {
            'oee': sum(k.oee_percentage for k in kpis) / total_records,
            'availability': sum(k.availability_percentage for k in kpis) / total_records,
            'performance': sum(k.performance_percentage for k in kpis) / total_records,
            'quality': sum(k.quality_percentage for k in kpis) / total_records,
            'delivery': sum(k.on_time_delivery_rate for k in kpis) / total_records,
            'utilization': sum(k.utilization_rate for k in kpis) / total_records,
        }
        
        # Alertas activas
        alerts = kpis.filtered(lambda k: k.alert_level in ['yellow', 'red'])
        
        # Datos de tendencia
        trend_data = []
        for kpi in kpis[:10]:  # Últimos 10 registros
            trend_data.append({
                'date': kpi.measurement_date.strftime('%d/%m'),
                'oee': kpi.oee_percentage,
                'delivery': kpi.on_time_delivery_rate
            })
        
        # Centros de trabajo (simulados basados en megastock_base)
        workcenters = [
            {'name': 'CORRUGADORA', 'utilization_percentage': 85.5},
            {'name': 'TROQUELADORA', 'utilization_percentage': 72.3},
            {'name': 'GUILLOTINA', 'utilization_percentage': 68.7},
            {'name': 'EMPAQUE', 'utilization_percentage': 91.2},
        ]
        
        return {
            'summary': summary,
            'alerts': [{
                'id': a.id,
                'name': a.name,
                'level': a.alert_level,
                'line': a.production_line,
                'date': a.measurement_date.strftime('%d/%m/%Y')
            } for a in alerts],
            'trend_data': trend_data,
            'workcenters': workcenters
        }

    @api.model
    def create_sample_data(self):
        """Crear datos de ejemplo para pruebas"""
        sample_kpis = [
            {
                'name': 'KPI Diario Línea CAJAS',
                'production_line': 'cajas',
                'measurement_date': fields.Date.today(),
                'oee_percentage': 82.5,
                'availability_percentage': 91.0,
                'performance_percentage': 85.2,
                'quality_percentage': 96.8,
                'on_time_delivery_rate': 88.5,
                'utilization_rate': 85.0,
                'alert_level': 'green'
            },
            {
                'name': 'KPI Diario Línea LÁMINAS',
                'production_line': 'laminas',
                'measurement_date': fields.Date.today() - timedelta(days=1),
                'oee_percentage': 75.8,
                'availability_percentage': 88.5,
                'performance_percentage': 78.9,
                'quality_percentage': 94.2,
                'on_time_delivery_rate': 92.1,
                'utilization_rate': 79.5,
                'alert_level': 'yellow'
            },
            {
                'name': 'KPI Diario PAPEL PERIÓDICO',
                'production_line': 'papel',
                'measurement_date': fields.Date.today() - timedelta(days=2),
                'oee_percentage': 68.2,
                'availability_percentage': 82.1,
                'performance_percentage': 71.5,
                'quality_percentage': 89.8,
                'on_time_delivery_rate': 85.3,
                'utilization_rate': 72.8,
                'alert_level': 'red',
                'notes': 'Parada no programada por mantenimiento correctivo'
            }
        ]
        
        for data in sample_kpis:
            if not self.search([('name', '=', data['name']), ('measurement_date', '=', data['measurement_date'])]):
                self.create(data)
        
        return True