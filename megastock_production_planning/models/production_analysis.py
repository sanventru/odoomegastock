# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class ProductionAnalysis(models.Model):
    _name = 'megastock.production.analysis'
    _description = 'Análisis de Performance de Producción'
    _order = 'analysis_date desc'
    _rec_name = 'display_name'
    
    display_name = fields.Char(
        string='Nombre',
        compute='_compute_display_name',
        store=True
    )
    
    # === INFORMACIÓN BÁSICA ===
    analysis_date = fields.Date(
        string='Fecha de Análisis',
        default=fields.Date.today,
        required=True
    )
    
    analysis_period = fields.Selection([
        ('daily', 'Diario'),
        ('weekly', 'Semanal'),
        ('monthly', 'Mensual'),
        ('quarterly', 'Trimestral'),
        ('custom', 'Personalizado')
    ], string='Período de Análisis', default='daily', required=True)
    
    date_from = fields.Date(
        string='Desde',
        required=True,
        default=fields.Date.today
    )
    
    date_to = fields.Date(
        string='Hasta',
        required=True,
        default=fields.Date.today
    )
    
    # === SEGMENTACIÓN ===
    workcenter_ids = fields.Many2many(
        'mrp.workcenter',
        'analysis_workcenter_rel',
        'analysis_id',
        'workcenter_id',
        string='Centros de Trabajo',
        help='Centros de trabajo incluidos en el análisis'
    )
    
    production_line_filter = fields.Selection([
        ('all', 'Todas las Líneas'),
        ('papel_periodico', 'Papel Periódico'),
        ('cajas', 'Cajas & Planchas'),
        ('lamina_micro', 'Lámina Micro Corrugada')
    ], string='Filtro Línea', default='all')
    
    product_category_ids = fields.Many2many(
        'product.category',
        'analysis_category_rel',
        'analysis_id',
        'category_id',
        string='Categorías de Productos'
    )
    
    # === MÉTRICAS AGREGADAS ===
    total_productions = fields.Integer(
        string='Total Producciones',
        help='Número total de producciones analizadas'
    )
    
    completed_productions = fields.Integer(
        string='Producciones Completadas',
        help='Número de producciones completadas'
    )
    
    on_time_productions = fields.Integer(
        string='Producciones a Tiempo',
        help='Producciones completadas a tiempo'
    )
    
    delayed_productions = fields.Integer(
        string='Producciones Retrasadas',
        help='Producciones con retraso'
    )
    
    # === KPIs GLOBALES ===
    overall_oee = fields.Float(
        string='OEE Global (%)',
        help='OEE promedio del período'
    )
    
    overall_efficiency = fields.Float(
        string='Eficiencia Global (%)',
        help='Eficiencia promedio del período'
    )
    
    overall_quality = fields.Float(
        string='Calidad Global (%)',
        help='Calidad promedio del período'
    )
    
    on_time_delivery_rate = fields.Float(
        string='% Entregas a Tiempo',
        compute='_compute_delivery_rate',
        store=True
    )
    
    average_setup_time = fields.Float(
        string='Setup Promedio (min)',
        help='Tiempo promedio de setup'
    )
    
    # === ANÁLISIS DE CAPACIDAD ===
    planned_capacity_hours = fields.Float(
        string='Capacidad Planificada (h)',
        help='Horas de capacidad planificadas'
    )
    
    utilized_capacity_hours = fields.Float(
        string='Capacidad Utilizada (h)',
        help='Horas de capacidad realmente utilizadas'
    )
    
    capacity_utilization_rate = fields.Float(
        string='Tasa Utilización (%)',
        compute='_compute_capacity_utilization',
        store=True
    )
    
    bottleneck_hours = fields.Float(
        string='Horas Cuello Botella',
        help='Horas perdidas por cuellos de botella'
    )
    
    # === ANÁLISIS DE COSTOS ===
    total_planned_cost = fields.Float(
        string='Costo Total Planificado',
        help='Costo total planificado'
    )
    
    total_actual_cost = fields.Float(
        string='Costo Total Real',
        help='Costo total real incurrido'
    )
    
    cost_variance = fields.Float(
        string='Variación Costos',
        compute='_compute_cost_variance',
        store=True
    )
    
    cost_variance_percentage = fields.Float(
        string='Variación Costos (%)',
        compute='_compute_cost_variance',
        store=True
    )
    
    cost_per_unit_avg = fields.Float(
        string='Costo Promedio por Unidad',
        help='Costo promedio por unidad producida'
    )
    
    # === ANÁLISIS DE CALIDAD ===
    total_produced_qty = fields.Float(
        string='Cantidad Total Producida',
        help='Cantidad total producida en el período'
    )
    
    total_good_qty = fields.Float(
        string='Cantidad Buena Total',
        help='Cantidad total sin defectos'
    )
    
    total_defective_qty = fields.Float(
        string='Cantidad Defectuosa Total',
        help='Cantidad total con defectos'
    )
    
    total_scrap_qty = fields.Float(
        string='Cantidad Desechada Total',
        help='Cantidad total desechada'
    )
    
    defect_rate = fields.Float(
        string='Tasa Defectos (%)',
        compute='_compute_quality_rates',
        store=True
    )
    
    scrap_rate = fields.Float(
        string='Tasa Desecho (%)',
        compute='_compute_quality_rates',
        store=True
    )
    
    # === ANÁLISIS DE TIEMPOS ===
    average_cycle_time = fields.Float(
        string='Tiempo Ciclo Promedio (h)',
        help='Tiempo promedio de ciclo'
    )
    
    average_lead_time = fields.Float(
        string='Lead Time Promedio (días)',
        help='Lead time promedio'
    )
    
    total_downtime_hours = fields.Float(
        string='Tiempo Parada Total (h)',
        help='Tiempo total de paradas'
    )
    
    downtime_rate = fields.Float(
        string='Tasa Paradas (%)',
        compute='_compute_downtime_rate',
        store=True
    )
    
    # === TENDENCIAS Y COMPARACIONES ===
    trend_direction = fields.Selection([
        ('improving', 'Mejorando'),
        ('stable', 'Estable'),
        ('declining', 'Declinando')
    ], string='Tendencia General', compute='_compute_trend')
    
    vs_previous_period = fields.Text(
        string='vs Período Anterior',
        compute='_compute_period_comparison',
        help='Comparación con período anterior'
    )
    
    benchmark_performance = fields.Text(
        string='Performance vs Benchmark',
        compute='_compute_benchmark_comparison',
        help='Comparación con benchmarks internos'
    )
    
    # === INSIGHTS Y RECOMENDACIONES ===
    key_insights = fields.Text(
        string='Insights Clave',
        compute='_compute_key_insights',
        help='Insights principales del análisis'
    )
    
    improvement_opportunities = fields.Text(
        string='Oportunidades de Mejora',
        compute='_compute_improvement_opportunities',
        help='Oportunidades identificadas para mejora'
    )
    
    action_recommendations = fields.Text(
        string='Recomendaciones de Acción',
        compute='_compute_action_recommendations',
        help='Acciones recomendadas basadas en el análisis'
    )
    
    # === DATOS DETALLADOS ===
    analysis_data = fields.Text(
        string='Datos de Análisis',
        help='Datos detallados en formato JSON'
    )
    
    chart_data = fields.Text(
        string='Datos de Gráficos',
        help='Datos para visualizaciones en formato JSON'
    )
    
    # === CONFIGURACIÓN ===
    auto_generated = fields.Boolean(
        string='Generado Automáticamente',
        default=False,
        help='Indica si fue generado automáticamente'
    )
    
    include_forecasts = fields.Boolean(
        string='Incluir Pronósticos',
        default=False,
        help='Incluir proyecciones futuras'
    )
    
    benchmark_targets = fields.Text(
        string='Metas Benchmark',
        help='Metas y benchmarks para comparación'
    )
    
    # === MÉTODOS COMPUTADOS ===
    
    @api.depends('analysis_period', 'date_from', 'date_to', 'production_line_filter')
    def _compute_display_name(self):
        """Generar nombre descriptivo"""
        for analysis in self:
            period_name = dict(analysis._fields['analysis_period'].selection)[analysis.analysis_period]
            line_name = dict(analysis._fields['production_line_filter'].selection)[analysis.production_line_filter]
            
            analysis.display_name = f"Análisis {period_name} - {line_name} ({analysis.date_from} - {analysis.date_to})"
    
    @api.depends('on_time_productions', 'completed_productions')
    def _compute_delivery_rate(self):
        """Calcular tasa de entregas a tiempo"""
        for analysis in self:
            if analysis.completed_productions > 0:
                analysis.on_time_delivery_rate = (analysis.on_time_productions / analysis.completed_productions) * 100
            else:
                analysis.on_time_delivery_rate = 0.0
    
    @api.depends('utilized_capacity_hours', 'planned_capacity_hours')
    def _compute_capacity_utilization(self):
        """Calcular tasa de utilización de capacidad"""
        for analysis in self:
            if analysis.planned_capacity_hours > 0:
                analysis.capacity_utilization_rate = (analysis.utilized_capacity_hours / analysis.planned_capacity_hours) * 100
            else:
                analysis.capacity_utilization_rate = 0.0
    
    @api.depends('total_actual_cost', 'total_planned_cost')
    def _compute_cost_variance(self):
        """Calcular variación de costos"""
        for analysis in self:
            analysis.cost_variance = analysis.total_actual_cost - analysis.total_planned_cost
            
            if analysis.total_planned_cost > 0:
                analysis.cost_variance_percentage = (analysis.cost_variance / analysis.total_planned_cost) * 100
            else:
                analysis.cost_variance_percentage = 0.0
    
    @api.depends('total_produced_qty', 'total_defective_qty', 'total_scrap_qty')
    def _compute_quality_rates(self):
        """Calcular tasas de calidad"""
        for analysis in self:
            if analysis.total_produced_qty > 0:
                analysis.defect_rate = (analysis.total_defective_qty / analysis.total_produced_qty) * 100
                analysis.scrap_rate = (analysis.total_scrap_qty / analysis.total_produced_qty) * 100
            else:
                analysis.defect_rate = 0.0
                analysis.scrap_rate = 0.0
    
    @api.depends('total_downtime_hours', 'utilized_capacity_hours')
    def _compute_downtime_rate(self):
        """Calcular tasa de paradas"""
        for analysis in self:
            total_time = analysis.utilized_capacity_hours + analysis.total_downtime_hours
            if total_time > 0:
                analysis.downtime_rate = (analysis.total_downtime_hours / total_time) * 100
            else:
                analysis.downtime_rate = 0.0
    
    def _compute_trend(self):
        """Determinar tendencia general"""
        for analysis in self:
            # Buscar análisis del período anterior
            previous_analysis = analysis._get_previous_period_analysis()
            
            if previous_analysis:
                # Comparar KPIs principales
                current_score = (analysis.overall_oee + analysis.on_time_delivery_rate + 
                               (100 - analysis.defect_rate)) / 3
                previous_score = (previous_analysis.overall_oee + previous_analysis.on_time_delivery_rate + 
                                (100 - previous_analysis.defect_rate)) / 3
                
                if current_score > previous_score + 2:
                    analysis.trend_direction = 'improving'
                elif current_score < previous_score - 2:
                    analysis.trend_direction = 'declining'
                else:
                    analysis.trend_direction = 'stable'
            else:
                analysis.trend_direction = 'stable'
    
    def _compute_period_comparison(self):
        """Comparar con período anterior"""
        for analysis in self:
            previous_analysis = analysis._get_previous_period_analysis()
            
            if previous_analysis:
                comparisons = []
                
                # OEE
                oee_change = analysis.overall_oee - previous_analysis.overall_oee
                comparisons.append(f"OEE: {oee_change:+.1f}% ({analysis.overall_oee:.1f}% vs {previous_analysis.overall_oee:.1f}%)")
                
                # Entregas a tiempo
                delivery_change = analysis.on_time_delivery_rate - previous_analysis.on_time_delivery_rate  
                comparisons.append(f"Entregas a tiempo: {delivery_change:+.1f}% ({analysis.on_time_delivery_rate:.1f}% vs {previous_analysis.on_time_delivery_rate:.1f}%)")
                
                # Costos
                cost_change = analysis.cost_variance_percentage - previous_analysis.cost_variance_percentage
                comparisons.append(f"Variación costos: {cost_change:+.1f}% ({analysis.cost_variance_percentage:.1f}% vs {previous_analysis.cost_variance_percentage:.1f}%)")
                
                # Calidad
                defect_change = analysis.defect_rate - previous_analysis.defect_rate
                comparisons.append(f"Defectos: {defect_change:+.1f}% ({analysis.defect_rate:.1f}% vs {previous_analysis.defect_rate:.1f}%)")
                
                analysis.vs_previous_period = '\n'.join(comparisons)
            else:
                analysis.vs_previous_period = 'No hay datos del período anterior para comparar'
    
    def _compute_benchmark_comparison(self):
        """Comparar con benchmarks"""
        for analysis in self:
            # Benchmarks internos (pueden venir de configuración)
            benchmarks = {
                'oee_target': 85.0,
                'delivery_target': 95.0,
                'defect_target': 2.0,
                'utilization_target': 80.0
            }
            
            comparisons = []
            
            # OEE vs benchmark
            oee_vs_benchmark = analysis.overall_oee - benchmarks['oee_target']
            status = "✅" if oee_vs_benchmark >= 0 else "❌"
            comparisons.append(f"OEE: {analysis.overall_oee:.1f}% vs {benchmarks['oee_target']}% target {status}")
            
            # Entregas vs benchmark
            delivery_vs_benchmark = analysis.on_time_delivery_rate - benchmarks['delivery_target']
            status = "✅" if delivery_vs_benchmark >= 0 else "❌"
            comparisons.append(f"Entregas: {analysis.on_time_delivery_rate:.1f}% vs {benchmarks['delivery_target']}% target {status}")
            
            # Defectos vs benchmark
            defect_vs_benchmark = benchmarks['defect_target'] - analysis.defect_rate  # Invertido porque menos es mejor
            status = "✅" if defect_vs_benchmark >= 0 else "❌"
            comparisons.append(f"Defectos: {analysis.defect_rate:.1f}% vs {benchmarks['defect_target']}% target {status}")
            
            # Utilización vs benchmark
            util_vs_benchmark = analysis.capacity_utilization_rate - benchmarks['utilization_target']
            status = "✅" if util_vs_benchmark >= 0 else "❌"
            comparisons.append(f"Utilización: {analysis.capacity_utilization_rate:.1f}% vs {benchmarks['utilization_target']}% target {status}")
            
            analysis.benchmark_performance = '\n'.join(comparisons)
    
    def _compute_key_insights(self):
        """Generar insights clave"""
        for analysis in self:
            insights = []
            
            # Insight sobre OEE
            if analysis.overall_oee < 70:
                insights.append("🔴 OEE crítico: Requiere atención inmediata")
            elif analysis.overall_oee < 80:
                insights.append("🟡 OEE bajo: Oportunidad de mejora significativa")
            elif analysis.overall_oee > 90:
                insights.append("🟢 OEE excelente: Performance mundial")
            
            # Insight sobre entregas
            if analysis.on_time_delivery_rate < 90:
                insights.append("⏰ Problemas de puntualidad: Impacto en satisfacción cliente")
            elif analysis.on_time_delivery_rate > 98:
                insights.append("🎯 Excelente puntualidad: Ventaja competitiva")
            
            # Insight sobre costos
            if abs(analysis.cost_variance_percentage) > 10:
                insights.append("💰 Alta variación costos: Revisar control de gastos")
            elif analysis.cost_variance_percentage < -5:
                insights.append("💡 Ahorro en costos: Identificar factores de éxito")
            
            # Insight sobre calidad
            if analysis.defect_rate > 5:
                insights.append("🔧 Problemas de calidad: Revisar procesos y capacitación")
            elif analysis.defect_rate < 1:
                insights.append("⭐ Calidad excepcional: Proceso bien controlado")
            
            # Insight sobre capacidad
            if analysis.capacity_utilization_rate < 60:
                insights.append("📉 Baja utilización: Evaluar redistribución de recursos")
            elif analysis.capacity_utilization_rate > 95:
                insights.append("⚠️ Saturación capacidad: Riesgo de cuellos de botella")
            
            analysis.key_insights = '\n'.join(insights) if insights else 'Sin insights críticos identificados'
    
    def _compute_improvement_opportunities(self):
        """Identificar oportunidades de mejora"""
        for analysis in self:
            opportunities = []
            
            # Oportunidades por OEE bajo
            if analysis.overall_oee < 85:
                if analysis.capacity_utilization_rate < 85:
                    opportunities.append("• Reducir tiempos de parada no planificada")
                if analysis.average_setup_time > 45:
                    opportunities.append("• Optimizar tiempos de setup (SMED)")
                if analysis.defect_rate > 2:
                    opportunities.append("• Implementar control de calidad en tiempo real")
            
            # Oportunidades por entregas tardías
            if analysis.on_time_delivery_rate < 95:
                opportunities.append("• Mejorar planificación y programación")
                opportunities.append("• Implementar sistema de alertas tempranas")
            
            # Oportunidades por costos
            if analysis.cost_variance_percentage > 5:
                opportunities.append("• Analizar drivers de costos variables")
                opportunities.append("• Optimizar consumo de materiales")
            
            # Oportunidades por utilización
            if analysis.capacity_utilization_rate < 75:
                opportunities.append("• Balancear cargas entre líneas")
                opportunities.append("• Evaluar consolidación de operaciones")
            
            # Oportunidades por calidad
            if analysis.defect_rate > 3:
                opportunities.append("• Capacitación en procedimientos estándar")
                opportunities.append("• Mantenimiento preventivo de equipos")
            
            analysis.improvement_opportunities = '\n'.join(opportunities) if opportunities else 'Performance óptima - mantener estándares'
    
    def _compute_action_recommendations(self):
        """Generar recomendaciones de acción"""
        for analysis in self:
            recommendations = []
            
            # Acciones por prioridad crítica
            if analysis.overall_oee < 70:
                recommendations.append("🚨 INMEDIATO: Análisis de causa raíz en línea con menor OEE")
                recommendations.append("🚨 INMEDIATO: Plan de acción 30-60-90 días")
            
            if analysis.on_time_delivery_rate < 85:
                recommendations.append("🔴 URGENTE: Revisión completa del proceso de planificación")
            
            if analysis.defect_rate > 5:
                recommendations.append("🔴 URGENTE: Auditoria de calidad y capacitación operadores")
            
            # Acciones por mejora continua
            if analysis.overall_oee >= 70 and analysis.overall_oee < 85:
                recommendations.append("🟡 CORTO PLAZO: Implementar TPM (Total Productive Maintenance)")
                recommendations.append("🟡 CORTO PLAZO: Proyectos de reducción de desperdicios")
            
            if analysis.capacity_utilization_rate < 75:
                recommendations.append("🟡 MEDIANO PLAZO: Estudio de balanceado de líneas")
            
            # Acciones por excelencia
            if analysis.overall_oee > 90:
                recommendations.append("🟢 MANTENER: Documentar mejores prácticas")
                recommendations.append("🟢 COMPARTIR: Replicar éxitos en otras líneas")
            
            analysis.action_recommendations = '\n'.join(recommendations) if recommendations else 'Mantener performance actual'
    
    # === MÉTODOS DE ANÁLISIS ===
    
    def execute_analysis(self):
        """Ejecutar análisis completo"""
        self.ensure_one()
        
        # Obtener producciones del período
        productions = self._get_period_productions()
        
        if not productions:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Sin Datos',
                    'message': 'No se encontraron producciones para el período seleccionado.',
                    'type': 'warning'
                }
            }
        
        # Calcular métricas básicas
        self._calculate_basic_metrics(productions)
        
        # Calcular KPIs
        self._calculate_kpis(productions)
        
        # Calcular métricas de capacidad
        self._calculate_capacity_metrics(productions)
        
        # Calcular métricas de costos
        self._calculate_cost_metrics(productions)
        
        # Calcular métricas de calidad
        self._calculate_quality_metrics(productions)
        
        # Calcular métricas de tiempo
        self._calculate_time_metrics(productions)
        
        # Generar datos para gráficos
        self._generate_chart_data(productions)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Análisis Completado',
                'message': f'Análisis ejecutado para {len(productions)} producciones.',
                'type': 'success'
            }
        }
    
    def _get_period_productions(self):
        """Obtener producciones del período"""
        domain = [
            ('date_planned_start', '>=', self.date_from),
            ('date_planned_start', '<=', self.date_to),
            ('state', 'in', ['progress', 'done', 'cancel'])
        ]
        
        # Filtrar por centros de trabajo
        if self.workcenter_ids:
            domain.append(('workorder_ids.workcenter_id', 'in', self.workcenter_ids.ids))
        
        # Filtrar por línea de producción
        if self.production_line_filter != 'all':
            domain.append(('workorder_ids.workcenter_id.production_line_type', '=', self.production_line_filter))
        
        # Filtrar por categorías de producto
        if self.product_category_ids:
            domain.append(('product_id.categ_id', 'in', self.product_category_ids.ids))
        
        return self.env['mrp.production'].search(domain)
    
    def _calculate_basic_metrics(self, productions):
        """Calcular métricas básicas"""
        self.total_productions = len(productions)
        self.completed_productions = len(productions.filtered(lambda p: p.state == 'done'))
        
        # Calcular entregas a tiempo
        on_time_count = 0
        delayed_count = 0
        
        for production in productions.filtered(lambda p: p.state == 'done'):
            if production.date_finished and production.date_planned_finished:
                if production.date_finished <= production.date_planned_finished:
                    on_time_count += 1
                else:
                    delayed_count += 1
        
        self.on_time_productions = on_time_count
        self.delayed_productions = delayed_count
    
    def _calculate_kpis(self, productions):
        """Calcular KPIs principales"""
        completed_productions = productions.filtered(lambda p: p.state == 'done')
        
        if completed_productions:
            # OEE promedio
            oee_values = []
            efficiency_values = []
            
            for production in completed_productions:
                if hasattr(production, 'actual_oee') and production.actual_oee > 0:
                    oee_values.append(production.actual_oee)
                if hasattr(production, 'actual_efficiency') and production.actual_efficiency > 0:
                    efficiency_values.append(production.actual_efficiency)
            
            self.overall_oee = sum(oee_values) / len(oee_values) if oee_values else 0.0
            self.overall_efficiency = sum(efficiency_values) / len(efficiency_values) if efficiency_values else 0.0
            
            # Calcular calidad global
            quality_checks = self.env['quality.check'].search([
                ('production_id', 'in', completed_productions.ids)
            ])
            
            if quality_checks:
                passed_checks = quality_checks.filtered(lambda c: c.quality_state == 'pass')
                self.overall_quality = (len(passed_checks) / len(quality_checks)) * 100
            else:
                self.overall_quality = 100.0
    
    def _calculate_capacity_metrics(self, productions):
        """Calcular métricas de capacidad"""
        # Capacidad planificada (horas teóricas disponibles)
        days_in_period = (self.date_to - self.date_from).days + 1
        
        if self.workcenter_ids:
            workcenters = self.workcenter_ids
        else:
            workcenters = productions.mapped('workorder_ids.workcenter_id')
        
        # Calcular capacidad teórica
        theoretical_hours = 0.0
        for workcenter in workcenters:
            daily_capacity = 16.0  # 2 turnos de 8 horas
            theoretical_hours += daily_capacity * days_in_period
        
        self.planned_capacity_hours = theoretical_hours
        
        # Capacidad utilizada (horas realmente trabajadas)
        total_workorder_hours = sum(
            wo.duration / 60.0 for wo in productions.mapped('workorder_ids') 
            if wo.duration > 0
        )
        
        self.utilized_capacity_hours = total_workorder_hours
    
    def _calculate_cost_metrics(self, productions):
        """Calcular métricas de costos"""
        completed_productions = productions.filtered(lambda p: p.state == 'done')
        
        self.total_planned_cost = sum(completed_productions.mapped('total_planned_cost'))
        self.total_actual_cost = sum(completed_productions.mapped('total_actual_cost'))
        
        # Costo promedio por unidad
        total_qty = sum(completed_productions.mapped('qty_produced'))
        if total_qty > 0:
            self.cost_per_unit_avg = self.total_actual_cost / total_qty
    
    def _calculate_quality_metrics(self, productions):
        """Calcular métricas de calidad"""
        completed_productions = productions.filtered(lambda p: p.state == 'done')
        
        self.total_produced_qty = sum(completed_productions.mapped('qty_produced'))
        
        # Buscar datos de calidad (simplificado)
        quality_checks = self.env['quality.check'].search([
            ('production_id', 'in', completed_productions.ids)
        ])
        
        if quality_checks:
            failed_checks = quality_checks.filtered(lambda c: c.quality_state == 'fail')
            
            # Estimación de cantidades defectuosas basada en controles fallidos
            if failed_checks:
                self.total_defective_qty = len(failed_checks) * 10  # Simplificado
                self.total_scrap_qty = len(failed_checks) * 2  # Simplificado
            
        self.total_good_qty = self.total_produced_qty - self.total_defective_qty - self.total_scrap_qty
    
    def _calculate_time_metrics(self, productions):
        """Calcular métricas de tiempo"""
        completed_productions = productions.filtered(lambda p: p.state == 'done')
        
        if completed_productions:
            # Tiempo de ciclo promedio
            cycle_times = []
            lead_times = []
            
            for production in completed_productions:
                if production.date_start and production.date_finished:
                    cycle_time = (production.date_finished - production.date_start).total_seconds() / 3600.0
                    cycle_times.append(cycle_time)
                
                if production.create_date and production.date_finished:
                    lead_time = (production.date_finished - production.create_date).days
                    lead_times.append(lead_time)
            
            self.average_cycle_time = sum(cycle_times) / len(cycle_times) if cycle_times else 0.0
            self.average_lead_time = sum(lead_times) / len(lead_times) if lead_times else 0.0
            
            # Tiempo de setup promedio
            setup_times = []
            for production in completed_productions:
                if hasattr(production, 'setup_time_estimated'):
                    setup_times.append(production.setup_time_estimated)
            
            self.average_setup_time = sum(setup_times) / len(setup_times) if setup_times else 0.0
            
            # Tiempo de parada (simplificado)
            total_workorder_time = sum(
                wo.duration / 60.0 for wo in completed_productions.mapped('workorder_ids')
                if wo.duration > 0
            )
            
            total_stoppage_time = sum(
                wo.total_stoppage_time / 60.0 for wo in completed_productions.mapped('workorder_ids')
                if hasattr(wo, 'total_stoppage_time') and wo.total_stoppage_time > 0
            )
            
            self.total_downtime_hours = total_stoppage_time
    
    def _generate_chart_data(self, productions):
        """Generar datos para gráficos"""
        import json
        
        # Datos para gráfico de tendencia OEE
        oee_trend = []
        for production in productions.filtered('actual_oee'):
            oee_trend.append({
                'date': production.date_finished.strftime('%Y-%m-%d') if production.date_finished else '',
                'oee': production.actual_oee,
                'production_name': production.name
            })
        
        # Datos para gráfico de distribución por línea
        line_distribution = {}
        for production in productions:
            line_type = getattr(production, 'corrugated_line_type', 'unknown')
            if line_type not in line_distribution:
                line_distribution[line_type] = 0
            line_distribution[line_type] += 1
        
        # Datos para gráfico de pareto de problemas
        problem_categories = {
            'setup_delays': 0,
            'material_shortage': 0,
            'quality_issues': 0,
            'equipment_failure': 0,
            'other': 0
        }
        
        # Simplificado - en implementación real vendría de datos detallados
        for production in productions:
            if production.state == 'cancel':
                problem_categories['other'] += 1
            elif hasattr(production, 'delay_hours') and production.delay_hours > 0:
                problem_categories['setup_delays'] += 1
        
        chart_data = {
            'oee_trend': oee_trend,
            'line_distribution': line_distribution,
            'problem_pareto': problem_categories
        }
        
        self.chart_data = json.dumps(chart_data)
    
    def _get_previous_period_analysis(self):
        """Obtener análisis del período anterior"""
        if self.analysis_period == 'daily':
            prev_date = self.date_from - timedelta(days=1)
        elif self.analysis_period == 'weekly':
            prev_date = self.date_from - timedelta(days=7)
        elif self.analysis_period == 'monthly':
            prev_date = self.date_from - timedelta(days=30)
        else:
            prev_date = self.date_from - timedelta(days=30)
        
        return self.search([
            ('analysis_period', '=', self.analysis_period),
            ('production_line_filter', '=', self.production_line_filter),
            ('date_from', '=', prev_date),
        ], limit=1)
    
    # === MÉTODOS DE EXPORTACIÓN ===
    
    def action_export_analysis(self):
        """Exportar análisis a Excel"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Exportar Análisis',
            'res_model': 'megastock.analysis.export.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_analysis_id': self.id}
        }
    
    def action_generate_report(self):
        """Generar reporte ejecutivo"""
        return {
            'type': 'ir.actions.report',
            'report_name': 'megastock_production_planning.production_analysis_report',
            'report_type': 'qweb-pdf',
            'data': {'analysis_id': self.id},
            'context': self.env.context
        }
    
    @api.model
    def auto_generate_daily_analysis(self):
        """Generar análisis diario automáticamente"""
        yesterday = fields.Date.today() - timedelta(days=1)
        
        # Verificar si ya existe análisis para ayer
        existing = self.search([
            ('analysis_date', '=', yesterday),
            ('analysis_period', '=', 'daily'),
            ('auto_generated', '=', True)
        ])
        
        if existing:
            return existing
        
        # Crear análisis para cada línea de producción
        production_lines = ['papel_periodico', 'cajas', 'lamina_micro']
        analyses_created = []
        
        for line in production_lines:
            analysis = self.create({
                'analysis_date': yesterday,
                'analysis_period': 'daily',
                'date_from': yesterday,
                'date_to': yesterday,
                'production_line_filter': line,
                'auto_generated': True
            })
            
            # Ejecutar análisis
            analysis.execute_analysis()
            analyses_created.append(analysis)
        
        _logger.info(f"Generados {len(analyses_created)} análisis diarios automáticos")
        
        return analyses_created