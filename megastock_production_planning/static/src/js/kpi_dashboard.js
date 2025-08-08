odoo.define('megastock_production_planning.KpiDashboard', function (require) {
'use strict';

var AbstractAction = require('web.AbstractAction');
var core = require('web.core');
var rpc = require('web.rpc');
var session = require('web.session');
var QWeb = core.qweb;
var _t = core._t;

var KpiDashboard = AbstractAction.extend({
    template: 'KpiDashboardMain',
    
    events: {
        'click .refresh-kpis': '_onRefreshKpis',
        'change .kpi-period-filter': '_onPeriodChange',
        'change .kpi-line-filter': '_onLineChange',
        'click .kpi-drill-down': '_onKpiDrillDown',
        'click .export-kpis': '_onExportKpis',
    },

    init: function(parent, context) {
        this._super(parent, context);
        this.kpiData = {};
        this.selectedPeriod = 'daily';
        this.selectedLine = 'all';
        this.charts = {};
    },

    willStart: function() {
        var self = this;
        return this._super().then(function() {
            return self._loadKpiData();
        });
    },

    start: function() {
        var self = this;
        return this._super().then(function() {
            self._renderKpiDashboard();
            self._setupKpiCharts();
        });
    },

    destroy: function() {
        // Destruir gráficos para evitar memory leaks
        Object.values(this.charts).forEach(function(chart) {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
        this._super();
    },

    // === MÉTODOS DE CARGA DE DATOS ===

    _loadKpiData: function() {
        var self = this;
        return rpc.query({
            model: 'megastock.production.kpi',
            method: 'get_kpi_dashboard_data',
            args: [],
            kwargs: {
                period: this.selectedPeriod,
                line_filter: this.selectedLine,
                context: session.user_context,
            }
        }).then(function(data) {
            self.kpiData = data;
            return data;
        });
    },

    _loadKpiTrends: function() {
        return rpc.query({
            model: 'megastock.production.kpi',
            method: 'get_kpi_trends',
            args: [],
            kwargs: {
                period: this.selectedPeriod,
                line_filter: this.selectedLine,
                days: this.selectedPeriod === 'hourly' ? 1 : 
                      this.selectedPeriod === 'daily' ? 7 : 
                      this.selectedPeriod === 'weekly' ? 4 : 12
            }
        });
    },

    _loadKpiComparisons: function() {
        return rpc.query({
            model: 'megastock.production.kpi',
            method: 'get_kpi_comparisons',
            args: [],
            kwargs: {
                period: this.selectedPeriod,
                line_filter: this.selectedLine
            }
        });
    },

    // === MÉTODOS DE RENDERIZADO ===

    _renderKpiDashboard: function() {
        var self = this;
        
        Promise.all([
            this._loadKpiTrends(),
            this._loadKpiComparisons()
        ]).then(function(results) {
            var trendsData = results[0];
            var comparisonsData = results[1];
            
            self._renderKpiSummaryCards(self.kpiData);
            self._renderKpiTrends(trendsData);
            self._renderKpiComparisons(comparisonsData);
            self._renderKpiAlerts();
            
            // Actualizar timestamp
            self.$('.kpi-last-update').text(moment().format('DD/MM/YYYY HH:mm:ss'));
        });
    },

    _renderKpiSummaryCards: function(kpiData) {
        var $container = this.$('.kpi-summary-cards');
        
        var summaryHtml = QWeb.render('KpiSummaryCards', {
            kpis: kpiData,
            _t: _t
        });
        
        $container.html(summaryHtml);
    },

    _renderKpiTrends: function(trendsData) {
        var $container = this.$('.kpi-trends-section');
        
        var trendsHtml = QWeb.render('KpiTrendsSection', {
            trends: trendsData,
            period: this.selectedPeriod,
            _t: _t
        });
        
        $container.html(trendsHtml);
    },

    _renderKpiComparisons: function(comparisonsData) {
        var $container = this.$('.kpi-comparisons-section');
        
        var comparisonsHtml = QWeb.render('KpiComparisonsSection', {
            comparisons: comparisonsData,
            _t: _t
        });
        
        $container.html(comparisonsHtml);
    },

    _renderKpiAlerts: function() {
        var self = this;
        
        rpc.query({
            model: 'megastock.production.kpi',
            method: 'get_kpi_alerts',
            args: [],
            kwargs: {
                severity: ['critical', 'warning'],
                line_filter: this.selectedLine
            }
        }).then(function(alerts) {
            var alertsHtml = QWeb.render('KpiAlertsSection', {
                alerts: alerts,
                _t: _t
            });
            
            self.$('.kpi-alerts-section').html(alertsHtml);
        });
    },

    // === MÉTODOS DE GRÁFICOS ===

    _setupKpiCharts: function() {
        this._setupOeeChart();
        this._setupTrendChart();
        this._setupRadarChart();
        this._setupBenchmarkChart();
    },

    _setupOeeChart: function() {
        var ctx = this.$('#oeeComponentsChart')[0];
        if (!ctx) return;

        var self = this;
        this._loadKpiData().then(function(data) {
            if (self.charts.oeeChart) {
                self.charts.oeeChart.destroy();
            }

            self.charts.oeeChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['Disponibilidad', 'Performance', 'Calidad'],
                    datasets: [{
                        data: [
                            data.availability_avg || 0,
                            data.performance_avg || 0,
                            data.quality_avg || 0
                        ],
                        backgroundColor: ['#28a745', '#ffc107', '#17a2b8'],
                        borderWidth: 3,
                        borderColor: '#fff'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        },
                        title: {
                            display: true,
                            text: 'Componentes OEE - ' + (data.oee_avg || 0).toFixed(1) + '%'
                        }
                    },
                    onClick: function(event, elements) {
                        if (elements.length > 0) {
                            var index = elements[0].index;
                            var component = ['availability', 'performance', 'quality'][index];
                            self._drillDownOeeComponent(component);
                        }
                    }
                }
            });
        });
    },

    _setupTrendChart: function() {
        var ctx = this.$('#kpiTrendChart')[0];
        if (!ctx) return;

        var self = this;
        this._loadKpiTrends().then(function(data) {
            if (self.charts.trendChart) {
                self.charts.trendChart.destroy();
            }

            self.charts.trendChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.labels || [],
                    datasets: [
                        {
                            label: 'OEE %',
                            data: data.oee_trend || [],
                            borderColor: '#007bff',
                            backgroundColor: 'rgba(0, 123, 255, 0.1)',
                            fill: false,
                            tension: 0.1
                        },
                        {
                            label: 'Entregas a Tiempo %',
                            data: data.delivery_trend || [],
                            borderColor: '#28a745',
                            backgroundColor: 'rgba(40, 167, 69, 0.1)',
                            fill: false,
                            tension: 0.1
                        },
                        {
                            label: 'Calidad %',
                            data: data.quality_trend || [],
                            borderColor: '#17a2b8',
                            backgroundColor: 'rgba(23, 162, 184, 0.1)',
                            fill: false,
                            tension: 0.1
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'top'
                        },
                        title: {
                            display: true,
                            text: 'Tendencias KPI - Últimos ' + (data.labels ? data.labels.length : 0) + ' períodos'
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            ticks: {
                                callback: function(value) {
                                    return value + '%';
                                }
                            }
                        }
                    },
                    interaction: {
                        intersect: false,
                        mode: 'index'
                    }
                }
            });
        });
    },

    _setupRadarChart: function() {
        var ctx = this.$('#kpiRadarChart')[0];
        if (!ctx) return;

        var self = this;
        this._loadKpiData().then(function(data) {
            if (self.charts.radarChart) {
                self.charts.radarChart.destroy();
            }

            self.charts.radarChart = new Chart(ctx, {
                type: 'radar',
                data: {
                    labels: ['OEE', 'Eficiencia', 'Calidad', 'Entregas', 'Utilización', 'Costos'],
                    datasets: [{
                        label: 'Actual',
                        data: [
                            data.oee_avg || 0,
                            data.efficiency_avg || 0,
                            data.quality_avg || 0,
                            data.delivery_avg || 0,
                            data.utilization_avg || 0,
                            Math.max(0, 100 - Math.abs(data.cost_variance_avg || 0)) // Invertir para que mejor = más alto
                        ],
                        borderColor: '#007bff',
                        backgroundColor: 'rgba(0, 123, 255, 0.2)',
                        borderWidth: 2
                    }, {
                        label: 'Target',
                        data: [85, 90, 98, 95, 80, 95], // Targets objetivo
                        borderColor: '#28a745',
                        backgroundColor: 'rgba(40, 167, 69, 0.1)',
                        borderWidth: 2,
                        borderDash: [5, 5]
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'top'
                        },
                        title: {
                            display: true,
                            text: 'Performance Global vs Targets'
                        }
                    },
                    scales: {
                        r: {
                            beginAtZero: true,
                            max: 100,
                            ticks: {
                                stepSize: 20
                            }
                        }
                    }
                }
            });
        });
    },

    _setupBenchmarkChart: function() {
        var ctx = this.$('#kpiBenchmarkChart')[0];
        if (!ctx) return;

        var self = this;
        this._loadKpiComparisons().then(function(data) {
            if (self.charts.benchmarkChart) {
                self.charts.benchmarkChart.destroy();
            }

            self.charts.benchmarkChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.lines || [],
                    datasets: [
                        {
                            label: 'OEE %',
                            data: data.oee_by_line || [],
                            backgroundColor: '#007bff',
                            borderColor: '#0056b3',
                            borderWidth: 1
                        },
                        {
                            label: 'Eficiencia %',
                            data: data.efficiency_by_line || [],
                            backgroundColor: '#28a745',
                            borderColor: '#1e7e34',
                            borderWidth: 1
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'top'
                        },
                        title: {
                            display: true,
                            text: 'Comparativo por Líneas de Producción'
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            ticks: {
                                callback: function(value) {
                                    return value + '%';
                                }
                            }
                        }
                    }
                }
            });
        });
    },

    // === EVENT HANDLERS ===

    _onRefreshKpis: function(ev) {
        ev.preventDefault();
        this._renderKpiDashboard();
        this._setupKpiCharts();
    },

    _onPeriodChange: function(ev) {
        this.selectedPeriod = $(ev.currentTarget).val();
        this._renderKpiDashboard();
        this._setupKpiCharts();
    },

    _onLineChange: function(ev) {
        this.selectedLine = $(ev.currentTarget).val();
        this._renderKpiDashboard();
        this._setupKpiCharts();
    },

    _onKpiDrillDown: function(ev) {
        var kpiType = $(ev.currentTarget).data('kpi-type');
        this._drillDownKpi(kpiType);
    },

    _onExportKpis: function(ev) {
        ev.preventDefault();
        this._exportKpiData();
    },

    // === MÉTODOS DE NAVEGACIÓN ===

    _drillDownKpi: function(kpiType) {
        this.do_action({
            name: _t('Detalle KPI - ') + kpiType,
            type: 'ir.actions.act_window',
            res_model: 'megastock.production.kpi',
            view_mode: 'tree,graph,pivot,form',
            domain: [['kpi_category', '=', kpiType]],
            context: {
                'group_by': ['measurement_date:day', 'production_line'],
                'search_default_this_month': 1
            },
            target: 'current'
        });
    },

    _drillDownOeeComponent: function(component) {
        var field_map = {
            'availability': 'availability_percentage',
            'performance': 'performance_percentage', 
            'quality': 'quality_percentage'
        };
        
        this.do_action({
            name: _t('Análisis ') + component.toUpperCase(),
            type: 'ir.actions.act_window',
            res_model: 'megastock.production.kpi',
            view_mode: 'graph,tree,form',
            domain: [['kpi_category', '=', 'efficiency']],
            context: {
                'group_by': ['measurement_date:day'],
                'measures': [field_map[component]],
                'search_default_this_week': 1
            },
            target: 'new'
        });
    },

    _exportKpiData: function() {
        var self = this;
        
        rpc.query({
            model: 'megastock.production.kpi',
            method: 'export_kpi_excel',
            args: [],
            kwargs: {
                period: this.selectedPeriod,
                line_filter: this.selectedLine
            }
        }).then(function(result) {
            if (result.url) {
                window.open(result.url, '_blank');
            } else {
                self.displayNotification({
                    type: 'warning',
                    title: _t('Exportación'),
                    message: _t('No se pudo generar el archivo de exportación')
                });
            }
        });
    },

});

core.action_registry.add('megastock_kpi_dashboard', KpiDashboard);

return KpiDashboard;

});