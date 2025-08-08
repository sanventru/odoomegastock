# -*- coding: utf-8 -*-

from odoo import http, fields
from odoo.http import request
import json
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class ProductionDashboardController(http.Controller):
    
    @http.route('/production_planning/dashboard/data', type='json', auth='user')
    def get_dashboard_data(self, line_filter='all', **kwargs):
        """Obtener datos para el dashboard principal"""
        try:
            # Obtener KPIs recientes
            kpi_data = self._get_kpi_summary(line_filter)
            
            # Obtener estado de capacidad
            capacity_data = self._get_capacity_summary(line_filter)
            
            # Obtener alertas activas
            alerts_data = self._get_active_alerts(line_filter)
            
            # Obtener estado de colas
            queue_data = self._get_queue_status(line_filter)
            
            # Obtener estadísticas de producción
            production_stats = self._get_production_stats(line_filter)
            
            return {
                'success': True,
                'data': {
                    'kpis': kpi_data,
                    'capacity': capacity_data,
                    'alerts': alerts_data,
                    'queues': queue_data,
                    'production': production_stats,
                    'timestamp': fields.Datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            _logger.error(f"Error obteniendo datos del dashboard: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @http.route('/production_planning/dashboard/kpi_chart', type='json', auth='user')
    def get_kpi_chart_data(self, kpi_type='oee', days=7, line_filter='all', **kwargs):
        """Obtener datos para gráficos de KPIs"""
        try:
            domain = [
                ('measurement_date', '>=', (fields.Date.today() - timedelta(days=days))),
                ('kpi_category', '=', kpi_type if kpi_type != 'oee' else 'efficiency')
            ]
            
            if line_filter != 'all':
                domain.append(('production_line', '=', line_filter))
            
            kpis = request.env['megastock.production.kpi'].search(domain, order='measurement_date asc')
            
            chart_data = {
                'labels': [],
                'datasets': []
            }
            
            if kpi_type == 'oee':
                chart_data['datasets'] = [
                    {
                        'label': 'OEE %',
                        'data': [],
                        'borderColor': '#007bff',
                        'backgroundColor': 'rgba(0, 123, 255, 0.1)'
                    }
                ]
                
                for kpi in kpis:
                    chart_data['labels'].append(kpi.measurement_date.strftime('%d/%m'))
                    chart_data['datasets'][0]['data'].append(kpi.oee_percentage)
            
            elif kpi_type == 'components':
                chart_data['datasets'] = [
                    {
                        'label': 'Disponibilidad',
                        'data': [],
                        'borderColor': '#28a745',
                        'backgroundColor': 'rgba(40, 167, 69, 0.1)'
                    },
                    {
                        'label': 'Performance',
                        'data': [],
                        'borderColor': '#ffc107',
                        'backgroundColor': 'rgba(255, 193, 7, 0.1)'
                    },
                    {
                        'label': 'Calidad',
                        'data': [],
                        'borderColor': '#17a2b8',
                        'backgroundColor': 'rgba(23, 162, 184, 0.1)'
                    }
                ]
                
                for kpi in kpis:
                    chart_data['labels'].append(kpi.measurement_date.strftime('%d/%m'))
                    chart_data['datasets'][0]['data'].append(kpi.availability_percentage)
                    chart_data['datasets'][1]['data'].append(kpi.performance_percentage)
                    chart_data['datasets'][2]['data'].append(kpi.quality_percentage)
            
            return {
                'success': True,
                'data': chart_data
            }
            
        except Exception as e:
            _logger.error(f"Error obteniendo datos de gráfico KPI: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @http.route('/production_planning/dashboard/capacity_chart', type='json', auth='user')
    def get_capacity_chart_data(self, line_filter='all', **kwargs):
        """Obtener datos para gráfico de capacidad"""
        try:
            domain = [('state', '=', 'active')]
            
            if line_filter != 'all':
                domain.append(('production_line_filter', '=', line_filter))
            
            capacity_plans = request.env['megastock.capacity.planning'].search(domain)
            
            chart_data = {
                'labels': [],
                'datasets': [{
                    'label': 'Utilización %',
                    'data': [],
                    'backgroundColor': []
                }]
            }
            
            for plan in capacity_plans:
                for line in plan.capacity_line_ids:
                    chart_data['labels'].append(line.workcenter_id.name)
                    utilization = line.utilization_percentage
                    chart_data['datasets'][0]['data'].append(utilization)
                    
                    # Color según utilización
                    if utilization > 95:
                        color = '#dc3545'  # Rojo - Crítico
                    elif utilization > 85:
                        color = '#ffc107'  # Amarillo - Advertencia
                    else:
                        color = '#28a745'  # Verde - Normal
                    
                    chart_data['datasets'][0]['backgroundColor'].append(color)
            
            return {
                'success': True,
                'data': chart_data
            }
            
        except Exception as e:
            _logger.error(f"Error obteniendo datos de gráfico de capacidad: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_kpi_summary(self, line_filter):
        """Obtener resumen de KPIs"""
        domain = [
            ('measurement_date', '>=', fields.Date.today() - timedelta(days=1))
        ]
        
        if line_filter != 'all':
            domain.append(('production_line', '=', line_filter))
        
        kpis = request.env['megastock.production.kpi'].search(domain)
        
        if not kpis:
            return {
                'oee': 0,
                'availability': 0,
                'performance': 0,
                'quality': 0,
                'delivery': 0,
                'utilization': 0
            }
        
        # Calcular promedios
        total_count = len(kpis)
        
        return {
            'oee': round(sum(kpis.mapped('oee_percentage')) / total_count, 1),
            'availability': round(sum(kpis.mapped('availability_percentage')) / total_count, 1),
            'performance': round(sum(kpis.mapped('performance_percentage')) / total_count, 1),
            'quality': round(sum(kpis.mapped('quality_percentage')) / total_count, 1),
            'delivery': round(sum(kpis.mapped('on_time_delivery_rate')) / total_count, 1),
            'utilization': round(sum(kpis.mapped('utilization_rate')) / total_count, 1)
        }
    
    def _get_capacity_summary(self, line_filter):
        """Obtener resumen de capacidad"""
        domain = [('state', '=', 'active')]
        
        if line_filter != 'all':
            domain.append(('production_line_filter', '=', line_filter))
        
        capacity_plans = request.env['megastock.capacity.planning'].search(domain)
        
        total_capacity = 0
        utilized_capacity = 0
        bottlenecks = []
        
        for plan in capacity_plans:
            for line in plan.capacity_line_ids:
                total_capacity += line.available_capacity_hours
                utilized_capacity += line.utilized_capacity_hours
                
                # Identificar cuellos de botella
                if line.utilization_percentage > 90:
                    bottlenecks.append({
                        'workcenter_name': line.workcenter_id.name,
                        'utilization': line.utilization_percentage,
                        'reason': 'Alta utilización',
                        'severity': 'danger' if line.utilization_percentage > 95 else 'warning'
                    })
        
        utilization_rate = (utilized_capacity / total_capacity * 100) if total_capacity > 0 else 0
        available_capacity = total_capacity - utilized_capacity
        
        return {
            'total_capacity': round(total_capacity, 1),
            'utilized_capacity': round(utilized_capacity, 1),
            'available_capacity': round(available_capacity, 1),
            'utilization_rate': round(utilization_rate, 1),
            'bottlenecks': bottlenecks
        }
    
    def _get_active_alerts(self, line_filter):
        """Obtener alertas activas"""
        alerts = []
        
        # Alertas de KPIs críticos
        domain = [
            ('measurement_date', '>=', fields.Date.today() - timedelta(days=1)),
            ('alert_level', '=', 'red')
        ]
        
        if line_filter != 'all':
            domain.append(('production_line', '=', line_filter))
        
        critical_kpis = request.env['megastock.production.kpi'].search(domain)
        
        for kpi in critical_kpis:
            alerts.append({
                'id': f"kpi_{kpi.id}",
                'title': 'KPI Crítico',
                'message': f"{kpi.display_name} - Requiere atención inmediata",
                'level': 'danger',
                'timestamp': kpi.measurement_date.strftime('%d/%m %H:%M')
            })
        
        # Alertas de producciones retrasadas
        delayed_productions = request.env['mrp.production'].search([
            ('state', 'in', ['confirmed', 'planned', 'progress']),
            ('date_planned_finished', '<', fields.Datetime.now())
        ])
        
        for production in delayed_productions[:5]:  # Limitar a 5 más críticas
            delay_hours = (fields.Datetime.now() - production.date_planned_finished).total_seconds() / 3600
            alerts.append({
                'id': f"production_{production.id}",
                'title': 'Producción Retrasada',
                'message': f"{production.name} - {delay_hours:.1f} horas de retraso",
                'level': 'warning' if delay_hours < 24 else 'danger',
                'timestamp': production.date_planned_finished.strftime('%d/%m %H:%M')
            })
        
        # Alertas de capacidad
        capacity_plans = request.env['megastock.capacity.planning'].search([
            ('state', '=', 'active')
        ])
        
        for plan in capacity_plans:
            for line in plan.capacity_line_ids:
                if line.utilization_percentage > 95:
                    alerts.append({
                        'id': f"capacity_{line.id}",
                        'title': 'Capacidad Crítica',
                        'message': f"{line.workcenter_id.name} - {line.utilization_percentage:.1f}% utilizado",
                        'level': 'danger',
                        'timestamp': fields.Datetime.now().strftime('%d/%m %H:%M')
                    })
        
        return sorted(alerts, key=lambda x: x['level'] == 'danger', reverse=True)[:10]
    
    def _get_queue_status(self, line_filter):
        """Obtener estado de colas"""
        domain = [('state', '=', 'active')]
        
        if line_filter != 'all':
            domain.append(('production_line', '=', line_filter))
        
        queues = request.env['megastock.work.queue'].search(domain)
        
        queue_data = []
        for queue in queues:
            utilization = min(100, (queue.current_items_count / queue.max_capacity * 100)) if queue.max_capacity > 0 else 0
            
            queue_data.append({
                'id': queue.id,
                'name': queue.name,
                'items_count': queue.current_items_count,
                'max_capacity': queue.max_capacity,
                'avg_wait_time': queue.average_waiting_time,
                'utilization': round(utilization, 1),
                'status': 'active' if queue.state == 'active' else 'inactive'
            })
        
        return queue_data
    
    def _get_production_stats(self, line_filter):
        """Obtener estadísticas de producción"""
        today = fields.Date.today()
        
        # Producciones de hoy
        domain_today = [
            ('date_planned_start', '>=', today),
            ('date_planned_start', '<', today + timedelta(days=1))
        ]
        
        if line_filter != 'all':
            domain_today.append(('workorder_ids.workcenter_id.production_line_type', '=', line_filter))
        
        productions_today = request.env['mrp.production'].search(domain_today)
        
        completed_today = productions_today.filtered(lambda p: p.state == 'done')
        in_progress_today = productions_today.filtered(lambda p: p.state == 'progress')
        planned_today = productions_today.filtered(lambda p: p.state in ['confirmed', 'planned'])
        
        return {
            'total_today': len(productions_today),
            'completed_today': len(completed_today),
            'in_progress_today': len(in_progress_today),
            'planned_today': len(planned_today),
            'completion_rate': round(len(completed_today) / len(productions_today) * 100, 1) if productions_today else 0
        }