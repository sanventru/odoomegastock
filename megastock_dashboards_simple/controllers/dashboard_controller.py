# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json

class MegastockDashboardController(http.Controller):

    @http.route('/megastock/dashboard/data', type='json', auth='user')
    def get_dashboard_data(self, line_filter='all', **kwargs):
        """API endpoint para obtener datos del dashboard"""
        try:
            ProductionKpi = request.env['megastock.production.kpi']
            data = ProductionKpi.get_dashboard_data(line_filter)
            return {
                'success': True,
                'data': data
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/megastock/dashboard/create_sample', type='json', auth='user')
    def create_sample_data(self, **kwargs):
        """Crear datos de ejemplo para el dashboard"""
        try:
            ProductionKpi = request.env['megastock.production.kpi']
            ProductionKpi.create_sample_data()
            return {
                'success': True,
                'message': 'Datos de ejemplo creados correctamente'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }