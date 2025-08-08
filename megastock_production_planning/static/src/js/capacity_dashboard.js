odoo.define('megastock_production_planning.CapacityDashboard', function (require) {
'use strict';

var AbstractAction = require('web.AbstractAction');
var core = require('web.core');
var rpc = require('web.rpc');
var session = require('web.session');
var QWeb = core.qweb;
var _t = core._t;

var CapacityDashboard = AbstractAction.extend({
    template: 'CapacityDashboardMain',
    
    events: {
        'click .refresh-capacity': '_onRefreshCapacity',
        'change .capacity-line-filter': '_onLineChange',
        'change .capacity-period-filter': '_onPeriodChange',
        'click .workcenter-detail': '_onWorkcenterDetail',
        'click .bottleneck-action': '_onBottleneckAction',
        'click .capacity-optimize': '_onOptimizeCapacity',
    },

    init: function(parent, context) {
        this._super(parent, context);
        this.capacityData = {};
        this.selectedLine = 'all';
        this.selectedPeriod = 'current';
        this.charts = {};
        this.autoRefresh = true;
        this.refreshInterval = 60000; // 1 minuto
        this.refreshTimer = null;
    },

    willStart: function() {
        var self = this;
        return this._super().then(function() {
            return self._loadCapacityData();
        });
    },

    start: function() {
        var self = this;
        return this._super().then(function() {
            self._renderCapacityDashboard();
            self._setupCapacityCharts();
            self._startAutoRefresh();
        });
    },

    destroy: function() {
        this._stopAutoRefresh();
        Object.values(this.charts).forEach(function(chart) {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
        this._super();
    },

    // === MÉTODOS DE CARGA DE DATOS ===

    _loadCapacityData: function() {
        var self = this;
        return rpc.query({
            model: 'megastock.capacity.planning',
            method: 'get_capacity_dashboard_data',
            args: [],
            kwargs: {
                line_filter: this.selectedLine,
                period: this.selectedPeriod,
                context: session.user_context,
            }
        }).then(function(data) {
            self.capacityData = data;
            return data;
        });
    },

    _loadWorkcenterDetails: function() {
        return rpc.query({
            model: 'megastock.capacity.planning',
            method: 'get_workcenter_details',
            args: [],
            kwargs: {
                line_filter: this.selectedLine,
                include_schedule: true
            }
        });
    },

    _loadCapacityTrends: function() {
        return rpc.query({
            model: 'megastock.capacity.planning',
            method: 'get_capacity_trends',
            args: [],
            kwargs: {
                line_filter: this.selectedLine,
                days: 7
            }
        });
    },

    _loadBottleneckAnalysis: function() {
        return rpc.query({
            model: 'megastock.capacity.planning',
            method: 'analyze_bottlenecks',
            args: [],
            kwargs: {
                line_filter: this.selectedLine,
                forecast_hours: 24
            }
        });
    },

    // === MÉTODOS DE RENDERIZADO ===

    _renderCapacityDashboard: function() {
        var self = this;
        
        Promise.all([
            this._loadWorkcenterDetails(),
            this._loadCapacityTrends(),
            this._loadBottleneckAnalysis()
        ]).then(function(results) {
            var workcenterData = results[0];
            var trendsData = results[1];
            var bottleneckData = results[2];
            
            self._renderCapacitySummary(self.capacityData);
            self._renderWorkcenterGrid(workcenterData);
            self._renderCapacityTrends(trendsData);
            self._renderBottleneckAnalysis(bottleneckData);
            
            // Actualizar timestamp
            self.$('.capacity-last-update').text(moment().format('DD/MM/YYYY HH:mm:ss'));
        });
    },

    _renderCapacitySummary: function(capacityData) {
        var $container = this.$('.capacity-summary-section');
        
        var summaryHtml = QWeb.render('CapacitySummarySection', {
            capacity: capacityData,
            _t: _t
        });
        
        $container.html(summaryHtml);
    },

    _renderWorkcenterGrid: function(workcenterData) {
        var $container = this.$('.workcenter-grid-section');
        
        var gridHtml = QWeb.render('WorkcenterGridSection', {
            workcenters: workcenterData,
            _t: _t
        });
        
        $container.html(gridHtml);
        
        // Agregar eventos de hover para tooltips
        this._setupWorkcenterTooltips();
    },

    _renderCapacityTrends: function(trendsData) {
        var $container = this.$('.capacity-trends-section');
        
        var trendsHtml = QWeb.render('CapacityTrendsSection', {
            trends: trendsData,
            _t: _t
        });
        
        $container.html(trendsHtml);
    },

    _renderBottleneckAnalysis: function(bottleneckData) {
        var $container = this.$('.bottleneck-analysis-section');
        
        var bottleneckHtml = QWeb.render('BottleneckAnalysisSection', {
            bottlenecks: bottleneckData,
            _t: _t
        });
        
        $container.html(bottleneckHtml);
    },

    // === MÉTODOS DE GRÁFICOS ===

    _setupCapacityCharts: function() {
        this._setupUtilizationChart();
        this._setupCapacityTrendChart();
        this._setupLoadDistributionChart();
        this._setupEfficiencyChart();
    },

    _setupUtilizationChart: function() {
        var ctx = this.$('#capacityUtilizationChart')[0];
        if (!ctx) return;

        var self = this;
        this._loadWorkcenterDetails().then(function(data) {
            if (self.charts.utilizationChart) {
                self.charts.utilizationChart.destroy();
            }

            var labels = data.map(function(wc) { return wc.name; });
            var utilization = data.map(function(wc) { return wc.utilization_percentage; });
            var colors = utilization.map(function(util) {
                if (util > 95) return '#dc3545'; // Crítico
                if (util > 85) return '#fd7e14'; // Alto
                if (util > 75) return '#ffc107'; // Medio
                return '#28a745'; // Normal
            });

            self.charts.utilizationChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Utilización %',
                        data: utilization,
                        backgroundColor: colors,
                        borderColor: colors.map(function(color) { return color + 'CC'; }),
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        },
                        title: {
                            display: true,
                            text: 'Utilización por Centro de Trabajo'
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
                    onClick: function(event, elements) {
                        if (elements.length > 0) {
                            var index = elements[0].index;
                            var workcenter = data[index];
                            self._showWorkcenterDetail(workcenter.id);
                        }
                    }
                }
            });
        });
    },

    _setupCapacityTrendChart: function() {
        var ctx = this.$('#capacityTrendChart')[0];
        if (!ctx) return;

        var self = this;
        this._loadCapacityTrends().then(function(data) {
            if (self.charts.trendChart) {
                self.charts.trendChart.destroy();
            }

            self.charts.trendChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.labels || [],
                    datasets: [
                        {
                            label: 'Capacidad Utilizada',
                            data: data.utilized_capacity || [],
                            borderColor: '#007bff',
                            backgroundColor: 'rgba(0, 123, 255, 0.1)',
                            fill: true,
                            tension: 0.4
                        },
                        {
                            label: 'Capacidad Disponible',
                            data: data.available_capacity || [],
                            borderColor: '#28a745',
                            backgroundColor: 'rgba(40, 167, 69, 0.1)',
                            fill: true,
                            tension: 0.4
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
                            text: 'Tendencia de Capacidad - Últimos 7 días'
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: function(value) {
                                    return value + 'h';
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

    _setupLoadDistributionChart: function() {
        var ctx = this.$('#loadDistributionChart')[0];
        if (!ctx) return;

        var self = this;
        this._loadCapacityData().then(function(data) {
            if (self.charts.loadChart) {
                self.charts.loadChart.destroy();
            }

            self.charts.loadChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['Utilizada', 'Disponible', 'Sobrecarga'],
                    datasets: [{
                        data: [
                            data.utilized_capacity || 0,
                            Math.max(0, (data.total_capacity || 0) - (data.utilized_capacity || 0)),
                            Math.max(0, (data.utilized_capacity || 0) - (data.total_capacity || 0))
                        ],
                        backgroundColor: ['#007bff', '#28a745', '#dc3545'],
                        borderWidth: 2,
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
                            text: 'Distribución de Carga Total'
                        }
                    }
                }
            });
        });
    },

    _setupEfficiencyChart: function() {
        var ctx = this.$('#efficiencyChart')[0];
        if (!ctx) return;

        var self = this;
        this._loadWorkcenterDetails().then(function(data) {
            if (self.charts.efficiencyChart) {
                self.charts.efficiencyChart.destroy();
            }

            var labels = data.map(function(wc) { return wc.name; });
            var planned = data.map(function(wc) { return wc.planned_efficiency || 0; });
            var actual = data.map(function(wc) { return wc.actual_efficiency || 0; });

            self.charts.efficiencyChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Eficiencia Planificada',
                            data: planned,
                            backgroundColor: 'rgba(40, 167, 69, 0.7)',
                            borderColor: '#28a745',
                            borderWidth: 1
                        },
                        {
                            label: 'Eficiencia Real',
                            data: actual,
                            backgroundColor: 'rgba(0, 123, 255, 0.7)',
                            borderColor: '#007bff',
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
                            text: 'Eficiencia Planificada vs Real'
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

    // === MÉTODOS DE UTILIDAD ===

    _setupWorkcenterTooltips: function() {
        this.$('.workcenter-card').each(function() {
            var $card = $(this);
            var workcenterData = $card.data('workcenter');
            
            $card.tooltip({
                title: function() {
                    return 'Utilización: ' + (workcenterData.utilization || 0) + '%\n' +
                           'Disponible: ' + (workcenterData.available_hours || 0) + 'h\n' +
                           'Próxima Parada: ' + (workcenterData.next_maintenance || 'N/A');
                },
                placement: 'top',
                trigger: 'hover'
            });
        });
    },

    _startAutoRefresh: function() {
        var self = this;
        if (this.autoRefresh && !this.refreshTimer) {
            this.refreshTimer = setInterval(function() {
                self._renderCapacityDashboard();
                self._setupCapacityCharts();
            }, this.refreshInterval);
        }
    },

    _stopAutoRefresh: function() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
        }
    },

    // === EVENT HANDLERS ===

    _onRefreshCapacity: function(ev) {
        ev.preventDefault();
        this._renderCapacityDashboard();
        this._setupCapacityCharts();
    },

    _onLineChange: function(ev) {
        this.selectedLine = $(ev.currentTarget).val();
        this._renderCapacityDashboard();
        this._setupCapacityCharts();
    },

    _onPeriodChange: function(ev) {
        this.selectedPeriod = $(ev.currentTarget).val();
        this._renderCapacityDashboard();
        this._setupCapacityCharts();
    },

    _onWorkcenterDetail: function(ev) {
        var workcenterData = $(ev.currentTarget).data('workcenter');
        this._showWorkcenterDetail(workcenterData.id);
    },

    _onBottleneckAction: function(ev) {
        var bottleneckId = $(ev.currentTarget).data('bottleneck-id');
        var actionType = $(ev.currentTarget).data('action-type');
        this._executeBottleneckAction(bottleneckId, actionType);
    },

    _onOptimizeCapacity: function(ev) {
        ev.preventDefault();
        this._launchCapacityOptimization();
    },

    // === MÉTODOS DE NAVEGACIÓN Y ACCIONES ===

    _showWorkcenterDetail: function(workcenterId) {
        this.do_action({
            name: _t('Detalle Centro de Trabajo'),
            type: 'ir.actions.act_window',
            res_model: 'mrp.workcenter',
            res_id: workcenterId,
            view_mode: 'form',
            target: 'new'
        });
    },

    _executeBottleneckAction: function(bottleneckId, actionType) {
        var self = this;
        
        rpc.query({
            model: 'megastock.capacity.planning',
            method: 'execute_bottleneck_action',
            args: [bottleneckId, actionType],
            kwargs: {}
        }).then(function(result) {
            if (result.success) {
                self.displayNotification({
                    type: 'success',
                    title: _t('Acción Ejecutada'),
                    message: result.message
                });
                self._renderCapacityDashboard();
            } else {
                self.displayNotification({
                    type: 'warning',
                    title: _t('Error'),
                    message: result.message
                });
            }
        });
    },

    _launchCapacityOptimization: function() {
        this.do_action({
            name: _t('Optimización de Capacidad'),
            type: 'ir.actions.act_window',
            res_model: 'megastock.capacity.optimization.wizard',
            view_mode: 'form',
            target: 'new',
            context: {
                'default_line_filter': this.selectedLine
            }
        });
    },

});

core.action_registry.add('megastock_capacity_dashboard', CapacityDashboard);

return CapacityDashboard;

});