odoo.define('megastock_production_planning.ProductionDashboard', function (require) {
'use strict';

var AbstractAction = require('web.AbstractAction');
var core = require('web.core');
var rpc = require('web.rpc');
var session = require('web.session');
var QWeb = core.qweb;
var _t = core._t;

var ProductionDashboard = AbstractAction.extend({
    template: 'ProductionDashboardMain',
    
    events: {
        'click .refresh-dashboard': '_onRefreshDashboard',
        'click .toggle-auto-refresh': '_onToggleAutoRefresh',
        'change .line-filter': '_onLineFilterChange',
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
        this._super();
    },

    // === MÉTODOS DE CARGA DE DATOS ===

    _loadDashboardData: function() {
        var self = this;
        return rpc.query({
            model: 'megastock.production.plan',
            method: 'get_dashboard_data',
            args: [],
            kwargs: {
                line_filter: this.selectedLine,
                context: session.user_context,
            }
        }).then(function(data) {
            self.dashboardData = data;
            return data;
        });
    },

    _loadKpiData: function() {
        return rpc.query({
            model: 'megastock.production.kpi',
            method: 'search_read',
            args: [[
                ['measurement_date', '>=', moment().subtract(7, 'days').format('YYYY-MM-DD')],
                ['production_line', this.selectedLine === 'all' ? 'in' : '=', 
                 this.selectedLine === 'all' ? ['papel_periodico', 'cajas', 'lamina_micro'] : this.selectedLine]
            ]],
            kwargs: {
                fields: ['display_name', 'oee_percentage', 'availability_percentage', 
                        'performance_percentage', 'quality_percentage', 'on_time_delivery_rate',
                        'utilization_rate', 'alert_level', 'measurement_date', 'production_line'],
                order: 'measurement_date desc',
                limit: 50
            }
        });
    },

    _loadCapacityData: function() {
        return rpc.query({
            model: 'megastock.capacity.planning',
            method: 'get_capacity_dashboard_data',
            args: [],
            kwargs: {
                line_filter: this.selectedLine
            }
        });
    },

    _loadAlerts: function() {
        return rpc.query({
            model: 'megastock.production.plan',
            method: 'get_active_alerts',
            args: [],
            kwargs: {
                line_filter: this.selectedLine
            }
        });
    },

    _loadWorkQueueData: function() {
        return rpc.query({
            model: 'megastock.work.queue',
            method: 'get_queue_status_data',
            args: [],
            kwargs: {
                line_filter: this.selectedLine
            }
        });
    },

    // === MÉTODOS DE RENDERIZADO ===

    _renderDashboard: function() {
        var self = this;
        
        // Cargar todos los datos necesarios
        Promise.all([
            this._loadKpiData(),
            this._loadCapacityData(),
            this._loadAlerts(),
            this._loadWorkQueueData()
        ]).then(function(results) {
            var kpiData = results[0];
            var capacityData = results[1];
            var alertsData = results[2];
            var queueData = results[3];
            
            // Renderizar secciones
            self._renderKpiCards(kpiData);
            self._renderCapacitySection(capacityData);
            self._renderAlertsSection(alertsData);
            self._renderQueueSection(queueData);
            
            // Actualizar timestamp
            self.$('.last-update-time').text(moment().format('DD/MM/YYYY HH:mm:ss'));
        });
    },

    _renderKpiCards: function(kpiData) {
        var self = this;
        var $kpiContainer = this.$('.kpi-cards-container');
        
        if (!kpiData || kpiData.length === 0) {
            $kpiContainer.html('<div class="alert alert-info">No hay datos de KPIs disponibles</div>');
            return;
        }

        // Calcular KPIs agregados
        var aggregatedKpis = this._aggregateKpiData(kpiData);
        
        // Renderizar cards
        var kpiCardsHtml = QWeb.render('KpiCards', {
            kpis: aggregatedKpis,
            moment: moment
        });
        
        $kpiContainer.html(kpiCardsHtml);
    },

    _renderCapacitySection: function(capacityData) {
        var $capacityContainer = this.$('.capacity-section');
        
        if (!capacityData) {
            $capacityContainer.html('<div class="alert alert-warning">Datos de capacidad no disponibles</div>');
            return;
        }

        var capacityHtml = QWeb.render('CapacitySection', {
            capacity: capacityData,
            _t: _t
        });
        
        $capacityContainer.html(capacityHtml);
    },

    _renderAlertsSection: function(alertsData) {
        var $alertsContainer = this.$('.alerts-section');
        
        var alertsHtml = QWeb.render('AlertsSection', {
            alerts: alertsData || [],
            _t: _t
        });
        
        $alertsContainer.html(alertsHtml);
    },

    _renderQueueSection: function(queueData) {
        var $queueContainer = this.$('.queue-section');
        
        var queueHtml = QWeb.render('QueueSection', {
            queues: queueData || [],
            _t: _t
        });
        
        $queueContainer.html(queueHtml);
    },

    // === MÉTODOS DE GRÁFICOS ===

    _setupCharts: function() {
        this._setupOeeChart();
        this._setupCapacityChart();
        this._setupTrendChart();
    },

    _setupOeeChart: function() {
        var self = this;
        var ctx = this.$('#oeeChart')[0];
        if (!ctx) return;

        this._loadKpiData().then(function(kpiData) {
            var chartData = self._prepareOeeChartData(kpiData);
            
            new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['Disponibilidad', 'Performance', 'Calidad'],
                    datasets: [{
                        data: [
                            chartData.availability,
                            chartData.performance,
                            chartData.quality
                        ],
                        backgroundColor: ['#28a745', '#ffc107', '#17a2b8'],
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    legend: {
                        position: 'bottom'
                    },
                    title: {
                        display: true,
                        text: 'Componentes OEE'
                    }
                }
            });
        });
    },

    _setupCapacityChart: function() {
        var self = this;
        var ctx = this.$('#capacityChart')[0];
        if (!ctx) return;

        this._loadCapacityData().then(function(capacityData) {
            if (!capacityData || !capacityData.workcenters) return;

            var labels = capacityData.workcenters.map(function(wc) { return wc.name; });
            var utilization = capacityData.workcenters.map(function(wc) { return wc.utilization_percentage; });
            
            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Utilización %',
                        data: utilization,
                        backgroundColor: utilization.map(function(val) {
                            return val > 90 ? '#dc3545' : val > 75 ? '#ffc107' : '#28a745';
                        })
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100
                        }
                    }
                }
            });
        });
    },

    _setupTrendChart: function() {
        var self = this;
        var ctx = this.$('#trendChart')[0];
        if (!ctx) return;

        this._loadKpiData().then(function(kpiData) {
            var chartData = self._prepareTrendChartData(kpiData);
            
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: chartData.labels,
                    datasets: [
                        {
                            label: 'OEE %',
                            data: chartData.oee,
                            borderColor: '#007bff',
                            backgroundColor: 'rgba(0, 123, 255, 0.1)',
                            fill: false
                        },
                        {
                            label: 'Entregas a Tiempo %',
                            data: chartData.delivery,
                            borderColor: '#28a745',
                            backgroundColor: 'rgba(40, 167, 69, 0.1)',
                            fill: false
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100
                        }
                    }
                }
            });
        });
    },

    // === MÉTODOS DE UTILIDAD ===

    _aggregateKpiData: function(kpiData) {
        if (!kpiData || kpiData.length === 0) return {};

        var totalOee = 0, totalAvailability = 0, totalPerformance = 0, 
            totalQuality = 0, totalDelivery = 0, totalUtilization = 0;
        var count = kpiData.length;

        kpiData.forEach(function(kpi) {
            totalOee += kpi.oee_percentage || 0;
            totalAvailability += kpi.availability_percentage || 0;
            totalPerformance += kpi.performance_percentage || 0;
            totalQuality += kpi.quality_percentage || 0;
            totalDelivery += kpi.on_time_delivery_rate || 0;
            totalUtilization += kpi.utilization_rate || 0;
        });

        return {
            oee: (totalOee / count).toFixed(1),
            availability: (totalAvailability / count).toFixed(1),
            performance: (totalPerformance / count).toFixed(1),
            quality: (totalQuality / count).toFixed(1),
            delivery: (totalDelivery / count).toFixed(1),
            utilization: (totalUtilization / count).toFixed(1)
        };
    },

    _prepareOeeChartData: function(kpiData) {
        var aggregated = this._aggregateKpiData(kpiData);
        return {
            availability: parseFloat(aggregated.availability) || 0,
            performance: parseFloat(aggregated.performance) || 0,
            quality: parseFloat(aggregated.quality) || 0
        };
    },

    _prepareTrendChartData: function(kpiData) {
        if (!kpiData || kpiData.length === 0) return { labels: [], oee: [], delivery: [] };

        // Agrupar por fecha
        var groupedData = {};
        kpiData.forEach(function(kpi) {
            var date = kpi.measurement_date;
            if (!groupedData[date]) {
                groupedData[date] = { oee: [], delivery: [] };
            }
            groupedData[date].oee.push(kpi.oee_percentage || 0);
            groupedData[date].delivery.push(kpi.on_time_delivery_rate || 0);
        });

        var labels = Object.keys(groupedData).sort();
        var oeeData = labels.map(function(date) {
            var values = groupedData[date].oee;
            return values.reduce((a, b) => a + b, 0) / values.length;
        });
        var deliveryData = labels.map(function(date) {
            var values = groupedData[date].delivery;
            return values.reduce((a, b) => a + b, 0) / values.length;
        });

        return {
            labels: labels.map(function(date) { return moment(date).format('DD/MM'); }),
            oee: oeeData,
            delivery: deliveryData
        };
    },

    // === AUTO REFRESH ===

    _startAutoRefresh: function() {
        var self = this;
        if (this.autoRefresh && !this.refreshTimer) {
            this.refreshTimer = setInterval(function() {
                self._renderDashboard();
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
        this._renderDashboard();
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
        this.selectedLine = $(ev.currentTarget).val();
        this._renderDashboard();
    },

    _onKpiCardClick: function(ev) {
        var kpiType = $(ev.currentTarget).data('kpi-type');
        this.do_action({
            name: _t('Detalle KPI'),
            type: 'ir.actions.act_window',
            res_model: 'megastock.production.kpi',
            view_mode: 'tree,form',
            domain: [['kpi_category', '=', kpiType]],
            target: 'new'
        });
    },

    _onAlertClick: function(ev) {
        var alertId = $(ev.currentTarget).data('alert-id');
        // Implementar navegación a detalle de alerta
        console.log('Alert clicked:', alertId);
    },

});

core.action_registry.add('megastock_production_dashboard', ProductionDashboard);

return ProductionDashboard;

});