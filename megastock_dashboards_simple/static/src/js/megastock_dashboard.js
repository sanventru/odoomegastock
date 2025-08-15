odoo.define('megastock_dashboards_simple.MegastockDashboard', function (require) {
'use strict';

var AbstractAction = require('web.AbstractAction');
var core = require('web.core');
var rpc = require('web.rpc');
var session = require('web.session');
var QWeb = core.qweb;
var _t = core._t;

var MegastockDashboard = AbstractAction.extend({
    template: 'MegastockDashboardMain',
    
    events: {
        'click .refresh-dashboard': '_onRefreshDashboard',
        'click .toggle-auto-refresh': '_onToggleAutoRefresh',
        'change .line-filter-select': '_onLineFilterChange',
        'click .kpi-card': '_onKpiCardClick',
        'click .alert-item': '_onAlertClick',
    },

    init: function(parent, context) {
        this._super(parent, context);
        this.dashboardData = {};
        this.autoRefresh = true;
        this.refreshInterval = 30000; // 30 segundos
        this.refreshTimer = null;
        this.selectedLine = 'all';
        this.charts = {};
    },

    willStart: function() {
        var self = this;
        return this._super().then(function() {
            return self._loadDashboardData();
        });
    },

    start: function() {
        var self = this;
        return this._super().then(function() {
            self._renderDashboard();
            self._startAutoRefresh();
            self._setupCharts();
        });
    },

    destroy: function() {
        this._stopAutoRefresh();
        this._destroyCharts();
        this._super();
    },

    // === MÉTODOS DE CARGA DE DATOS ===

    _loadDashboardData: function() {
        var self = this;
        return rpc.query({
            model: 'megastock.production.kpi',
            method: 'get_dashboard_data',
            args: [this.selectedLine],
            context: session.user_context,
        }).then(function(data) {
            self.dashboardData = data;
            return data;
        }).catch(function(error) {
            console.error('Error loading dashboard data:', error);
            self.dashboardData = {
                summary: {oee: 0, availability: 0, performance: 0, quality: 0, delivery: 0, utilization: 0},
                alerts: [],
                trend_data: [],
                workcenters: []
            };
        });
    },

    _createSampleData: function() {
        var self = this;
        return rpc.query({
            route: '/megastock/dashboard/create_sample',
            params: {}
        }).then(function(result) {
            if (result.success) {
                self._loadDashboardData().then(function() {
                    self._renderDashboard();
                });
            }
        });
    },

    // === MÉTODOS DE RENDERIZADO ===

    _renderDashboard: function() {
        var self = this;
        this._renderKpiCards();
        this._renderAlerts();
        this._updateCharts();
        this.$('.last-update-time').text(moment().format('DD/MM/YYYY HH:mm:ss'));
    },

    _renderKpiCards: function() {
        var self = this;
        var $kpiContainer = this.$('.kpi-cards-container');
        
        if (!this.dashboardData || !this.dashboardData.summary) {
            $kpiContainer.html('<div class="alert alert-info">No hay datos disponibles. <button class="btn btn-primary" onclick="window.createSampleData()">Crear datos de ejemplo</button></div>');
            window.createSampleData = function() {
                self._createSampleData();
            };
            return;
        }

        var summary = this.dashboardData.summary;
        var kpis = [
            {
                type: 'oee',
                title: 'OEE General',
                value: summary.oee.toFixed(1) + '%',
                level: summary.oee >= 80 ? 'green' : summary.oee >= 70 ? 'yellow' : 'red'
            },
            {
                type: 'availability',
                title: 'Disponibilidad',
                value: summary.availability.toFixed(1) + '%',
                level: summary.availability >= 90 ? 'green' : summary.availability >= 80 ? 'yellow' : 'red'
            },
            {
                type: 'performance',
                title: 'Performance',
                value: summary.performance.toFixed(1) + '%',
                level: summary.performance >= 85 ? 'green' : summary.performance >= 75 ? 'yellow' : 'red'
            },
            {
                type: 'quality',
                title: 'Calidad',
                value: summary.quality.toFixed(1) + '%',
                level: summary.quality >= 95 ? 'green' : summary.quality >= 90 ? 'yellow' : 'red'
            },
            {
                type: 'delivery',
                title: 'Entregas a Tiempo',
                value: summary.delivery.toFixed(1) + '%',
                level: summary.delivery >= 95 ? 'green' : summary.delivery >= 85 ? 'yellow' : 'red'
            },
            {
                type: 'utilization',
                title: 'Utilización',
                value: summary.utilization.toFixed(1) + '%',
                level: summary.utilization >= 85 ? 'green' : summary.utilization >= 75 ? 'yellow' : 'red'
            }
        ];
        
        var kpiCardsHtml = QWeb.render('KpiCards', {
            kpis: kpis
        });
        
        $kpiContainer.html(kpiCardsHtml);
    },

    _renderAlerts: function() {
        var $alertsContainer = this.$('.alerts-container');
        
        var alertsHtml = QWeb.render('AlertsSection', {
            alerts: this.dashboardData.alerts || []
        });
        
        $alertsContainer.html(alertsHtml);
    },

    // === MÉTODOS DE GRÁFICOS ===

    _setupCharts: function() {
        this._setupOeeChart();
        this._setupCapacityChart();
        this._setupTrendChart();
    },

    _updateCharts: function() {
        this._setupOeeChart();
        this._setupCapacityChart();
        this._setupTrendChart();
    },

    _destroyCharts: function() {
        Object.values(this.charts).forEach(function(chart) {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
        this.charts = {};
    },

    _setupOeeChart: function() {
        var ctx = this.$('#oeeChart')[0];
        if (!ctx || !this.dashboardData.summary) return;

        if (this.charts.oee) {
            this.charts.oee.destroy();
        }

        var summary = this.dashboardData.summary;
        
        this.charts.oee = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Disponibilidad', 'Performance', 'Calidad'],
                datasets: [{
                    data: [
                        summary.availability || 0,
                        summary.performance || 0,
                        summary.quality || 0
                    ],
                    backgroundColor: ['#28a745', '#ffc107', '#17a2b8'],
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
                        display: false
                    }
                }
            }
        });
    },

    _setupCapacityChart: function() {
        var ctx = this.$('#capacityChart')[0];
        if (!ctx || !this.dashboardData.workcenters) return;

        if (this.charts.capacity) {
            this.charts.capacity.destroy();
        }

        var workcenters = this.dashboardData.workcenters;
        var labels = workcenters.map(function(wc) { return wc.name; });
        var utilization = workcenters.map(function(wc) { return wc.utilization_percentage; });
        
        this.charts.capacity = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Utilización %',
                    data: utilization,
                    backgroundColor: utilization.map(function(val) {
                        return val > 90 ? '#dc3545' : val > 75 ? '#ffc107' : '#28a745';
                    }),
                    borderColor: utilization.map(function(val) {
                        return val > 90 ? '#c82333' : val > 75 ? '#e0a800' : '#1e7e34';
                    }),
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
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
    },

    _setupTrendChart: function() {
        var ctx = this.$('#trendChart')[0];
        if (!ctx || !this.dashboardData.trend_data) return;

        if (this.charts.trend) {
            this.charts.trend.destroy();
        }

        var trendData = this.dashboardData.trend_data;
        var labels = trendData.map(function(d) { return d.date; });
        var oeeData = trendData.map(function(d) { return d.oee; });
        var deliveryData = trendData.map(function(d) { return d.delivery; });
        
        this.charts.trend = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'OEE %',
                        data: oeeData,
                        borderColor: '#007bff',
                        backgroundColor: 'rgba(0, 123, 255, 0.1)',
                        fill: false,
                        tension: 0.1
                    },
                    {
                        label: 'Entregas a Tiempo %',
                        data: deliveryData,
                        borderColor: '#28a745',
                        backgroundColor: 'rgba(40, 167, 69, 0.1)',
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
    },

    // === AUTO REFRESH ===

    _startAutoRefresh: function() {
        var self = this;
        if (this.autoRefresh && !this.refreshTimer) {
            this.refreshTimer = setInterval(function() {
                self._loadDashboardData().then(function() {
                    self._renderDashboard();
                });
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

    _onRefreshDashboard: function(ev) {
        ev.preventDefault();
        var self = this;
        this._loadDashboardData().then(function() {
            self._renderDashboard();
        });
    },

    _onToggleAutoRefresh: function(ev) {
        this.autoRefresh = !this.autoRefresh;
        var $button = $(ev.currentTarget);
        
        if (this.autoRefresh) {
            $button.removeClass('btn-outline-success').addClass('btn-success')
                   .find('i').removeClass('fa-play').addClass('fa-pause');
            this._startAutoRefresh();
        } else {
            $button.removeClass('btn-success').addClass('btn-outline-success')
                   .find('i').removeClass('fa-pause').addClass('fa-play');
            this._stopAutoRefresh();
        }
    },

    _onLineFilterChange: function(ev) {
        var self = this;
        this.selectedLine = $(ev.currentTarget).val();
        this._loadDashboardData().then(function() {
            self._renderDashboard();
        });
    },

    _onKpiCardClick: function(ev) {
        var kpiType = $(ev.currentTarget).data('kpi-type');
        this.do_action({
            name: _t('Detalle KPI'),
            type: 'ir.actions.act_window',
            res_model: 'megastock.production.kpi',
            view_mode: 'tree,form',
            domain: [],
            target: 'new'
        });
    },

    _onAlertClick: function(ev) {
        var alertId = $(ev.currentTarget).data('alert-id');
        console.log('Alert clicked:', alertId);
    },

});

core.action_registry.add('megastock_production_dashboard', MegastockDashboard);

return MegastockDashboard;

});