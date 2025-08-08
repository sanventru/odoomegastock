odoo.define('megastock_production_planning.AlertDashboard', function (require) {
    'use strict';

    var core = require('web.core');
    var Widget = require('web.Widget');
    var web_client = require('web.web_client');
    var session = require('web.session');
    var rpc = require('web.rpc');
    var time = require('web.time');
    var QWeb = core.qweb;
    var _t = core._t;

    var AlertDashboard = Widget.extend({
        template: 'AlertsDashboardMain',
        events: {
            'click .alert-refresh': '_refreshDashboard',
            'click .alert-item': '_openAlert',
            'click .alert-acknowledge': '_acknowledgeAlert',
            'click .alert-resolve': '_resolveAlert',
            'click .alert-escalate': '_escalateAlert',
            'change .alert-filter-priority': '_filterByPriority',
            'change .alert-filter-type': '_filterByType',
            'change .alert-filter-line': '_filterByLine',
            'click .toggle-sound-alerts': '_toggleSoundAlerts'
        },

        init: function (parent, options) {
            this._super.apply(this, arguments);
            this.dashboard_templates = ['AlertsDashboardMain', 'AlertCard', 'AlertsList', 'AlertsStats'];
            this.alerts_data = {};
            this.charts = {};
            this.sound_enabled = true;
            this.auto_refresh_interval = null;
            this.filters = {
                priority: 'all',
                type: 'all',
                line: 'all'
            };
        },

        willStart: function () {
            var self = this;
            return this._super().then(function () {
                return self._loadQWebTemplates();
            });
        },

        start: function () {
            var self = this;
            return this._super().then(function () {
                self._setupDashboard();
                self._startAutoRefresh();
                self._setupSoundNotifications();
                return self._loadAlertsData();
            });
        },

        destroy: function () {
            if (this.auto_refresh_interval) {
                clearInterval(this.auto_refresh_interval);
            }
            this._destroyCharts();
            this._super();
        },

        _loadQWebTemplates: function () {
            return rpc.query({
                route: '/web/dataset/call_kw',
                params: {
                    model: 'ir.ui.view',
                    method: 'read_template',
                    args: ['megastock_production_planning.alert_dashboard_templates'],
                    kwargs: {}
                }
            });
        },

        _setupDashboard: function () {
            var self = this;
            
            // Configurar controles
            this.$('.alert-refresh').on('click', function() {
                self._refreshDashboard();
            });

            // Configurar filtros
            this._setupFilters();
            
            // Configurar auto-refresh
            this.$('.toggle-auto-refresh').on('click', function() {
                self._toggleAutoRefresh();
            });

            // Configurar notificaciones sonoras
            this.$('.toggle-sound-alerts').on('click', function() {
                self._toggleSoundAlerts();
            });
        },

        _setupFilters: function () {
            var self = this;
            
            // Filtro por prioridad
            this.$('.alert-filter-priority').on('change', function() {
                self.filters.priority = $(this).val();
                self._applyFilters();
            });

            // Filtro por tipo
            this.$('.alert-filter-type').on('change', function() {
                self.filters.type = $(this).val();
                self._applyFilters();
            });

            // Filtro por línea
            this.$('.alert-filter-line').on('change', function() {
                self.filters.line = $(this).val();
                self._applyFilters();
            });
        },

        _loadAlertsData: function () {
            var self = this;
            
            return rpc.query({
                model: 'megastock.production.alert',
                method: 'get_dashboard_data',
                args: [],
                kwargs: {
                    filters: this.filters
                }
            }).then(function (data) {
                self.alerts_data = data;
                self._renderDashboard();
                self._updateCharts();
                self._checkNewAlerts(data.alerts);
            }).catch(function (error) {
                console.error('Error loading alerts data:', error);
                self._showError('Error al cargar datos de alertas');
            });
        },

        _renderDashboard: function () {
            this._updateStatistics();
            this._renderAlertsList();
            this._updateLastRefresh();
        },

        _updateStatistics: function () {
            var stats = this.alerts_data.statistics || {};
            
            // Actualizar contadores principales
            this.$('#active-alerts-count').text(stats.active_count || 0);
            this.$('#escalated-alerts-count').text(stats.escalated_count || 0);
            this.$('#resolved-today-count').text(stats.resolved_today || 0);
            this.$('#avg-resolution-time').text(Math.round(stats.avg_resolution_time || 0));

            // Actualizar tarjetas por severidad
            this._updateSeverityCards(stats.by_severity || {});
            
            // Actualizar tendencias
            this._updateTrendIndicators(stats.trends || {});
        },

        _updateSeverityCards: function (severityStats) {
            var severities = ['critical', 'error', 'warning', 'info'];
            var colors = {
                'critical': 'danger',
                'error': 'warning', 
                'warning': 'info',
                'info': 'success'
            };

            severities.forEach(function (severity) {
                var count = severityStats[severity] || 0;
                var cardClass = 'alert-card-' + colors[severity];
                var $card = $('.' + cardClass);
                
                if ($card.length) {
                    $card.find('.severity-count').text(count);
                    $card.toggleClass('pulse-animation', count > 0 && severity === 'critical');
                }
            });
        },

        _updateTrendIndicators: function (trends) {
            Object.keys(trends).forEach(function (metric) {
                var trend = trends[metric];
                var $indicator = $('.trend-' + metric);
                
                if ($indicator.length) {
                    $indicator.removeClass('fa-arrow-up fa-arrow-down fa-minus');
                    
                    if (trend > 5) {
                        $indicator.addClass('fa-arrow-up text-danger');
                    } else if (trend < -5) {
                        $indicator.addClass('fa-arrow-down text-success');
                    } else {
                        $indicator.addClass('fa-minus text-muted');
                    }
                    
                    $indicator.attr('title', 'Tendencia: ' + (trend > 0 ? '+' : '') + trend + '%');
                }
            });
        },

        _renderAlertsList: function () {
            var self = this;
            var alerts = this.alerts_data.alerts || [];
            var $alertsContainer = this.$('.alerts-list-container');
            
            if (alerts.length === 0) {
                $alertsContainer.html('<div class="alert alert-success"><i class="fa fa-check-circle"></i> No hay alertas activas</div>');
                return;
            }

            var $alertsList = $('<div class="alerts-list"></div>');
            
            alerts.forEach(function (alert) {
                var $alertCard = self._createAlertCard(alert);
                $alertsList.append($alertCard);
            });
            
            $alertsContainer.html($alertsList);
        },

        _createAlertCard: function (alert) {
            var self = this;
            var severityClass = this._getSeverityClass(alert.severity);
            var priorityClass = this._getPriorityClass(alert.priority);
            var timeAgo = this._getTimeAgo(alert.detection_date);
            
            var $card = $(`
                <div class="alert-card card ${severityClass} ${priorityClass}" data-alert-id="${alert.id}">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start">
                            <div class="alert-content flex-grow-1">
                                <h6 class="alert-title">${alert.title}</h6>
                                <p class="alert-message text-muted">${alert.message}</p>
                                <div class="alert-meta">
                                    <span class="badge badge-${this._getTypeBadgeClass(alert.alert_type)}">${alert.alert_type}</span>
                                    <span class="badge badge-secondary">${alert.production_line}</span>
                                    <small class="text-muted ml-2">
                                        <i class="fa fa-clock-o"></i> ${timeAgo}
                                    </small>
                                    ${alert.escalation_count > 0 ? `<span class="badge badge-warning ml-1">Escalado ${alert.escalation_count}x</span>` : ''}
                                    ${alert.is_recurring ? '<span class="badge badge-info ml-1">Recurrente</span>' : ''}
                                </div>
                            </div>
                            <div class="alert-actions">
                                <div class="btn-group-vertical btn-group-sm">
                                    ${alert.state === 'active' ? '<button class="btn btn-outline-warning alert-acknowledge" title="Reconocer"><i class="fa fa-eye"></i></button>' : ''}
                                    ${alert.state !== 'resolved' ? '<button class="btn btn-outline-success alert-resolve" title="Resolver"><i class="fa fa-check"></i></button>' : ''}
                                    ${alert.state === 'active' || alert.state === 'acknowledged' ? '<button class="btn btn-outline-danger alert-escalate" title="Escalar"><i class="fa fa-arrow-up"></i></button>' : ''}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `);

            // Agregar eventos a los botones
            $card.find('.alert-acknowledge').on('click', function(e) {
                e.stopPropagation();
                self._acknowledgeAlert(alert.id);
            });

            $card.find('.alert-resolve').on('click', function(e) {
                e.stopPropagation();
                self._resolveAlert(alert.id);
            });

            $card.find('.alert-escalate').on('click', function(e) {
                e.stopPropagation();
                self._escalateAlert(alert.id);
            });

            // Hacer clic en la tarjeta para abrir detalles
            $card.on('click', function() {
                self._openAlert(alert.id);
            });

            return $card;
        },

        _updateCharts: function () {
            this._updateTypeChart();
            this._updateSeverityChart();
            this._updateTrendChart();
            this._updateResponseTimeChart();
        },

        _updateTypeChart: function () {
            var ctx = this.$('#alertsByTypeChart')[0];
            if (!ctx) return;

            var typeData = this.alerts_data.statistics.by_type || {};
            var labels = Object.keys(typeData);
            var data = Object.values(typeData);
            var colors = ['#007bff', '#28a745', '#ffc107', '#dc3545', '#6f42c1', '#20c997', '#fd7e14'];

            if (this.charts.typeChart) {
                this.charts.typeChart.destroy();
            }

            this.charts.typeChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        data: data,
                        backgroundColor: colors.slice(0, labels.length),
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        }
                    }
                }
            });
        },

        _updateSeverityChart: function () {
            var ctx = this.$('#alertsBySeverityChart')[0];
            if (!ctx) return;

            var severityData = this.alerts_data.statistics.by_severity || {};
            var labels = ['Crítico', 'Error', 'Advertencia', 'Info'];
            var data = [
                severityData.critical || 0,
                severityData.error || 0, 
                severityData.warning || 0,
                severityData.info || 0
            ];
            var colors = ['#dc3545', '#fd7e14', '#ffc107', '#28a745'];

            if (this.charts.severityChart) {
                this.charts.severityChart.destroy();
            }

            this.charts.severityChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Alertas',
                        data: data,
                        backgroundColor: colors,
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                stepSize: 1
                            }
                        }
                    }
                }
            });
        },

        _updateTrendChart: function () {
            var ctx = this.$('#alertsTrendChart')[0];
            if (!ctx) return;

            var trendData = this.alerts_data.trends || [];
            
            if (this.charts.trendChart) {
                this.charts.trendChart.destroy();
            }

            this.charts.trendChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: trendData.map(d => d.date),
                    datasets: [{
                        label: 'Alertas Generadas',
                        data: trendData.map(d => d.created),
                        borderColor: '#007bff',
                        backgroundColor: 'rgba(0, 123, 255, 0.1)',
                        tension: 0.4
                    }, {
                        label: 'Alertas Resueltas',
                        data: trendData.map(d => d.resolved),
                        borderColor: '#28a745',
                        backgroundColor: 'rgba(40, 167, 69, 0.1)',
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        },

        _updateResponseTimeChart: function () {
            var ctx = this.$('#responseTimeChart')[0];
            if (!ctx) return;

            var responseData = this.alerts_data.response_times || [];
            
            if (this.charts.responseChart) {
                this.charts.responseChart.destroy();
            }

            this.charts.responseChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: responseData.map(d => d.range),
                    datasets: [{
                        label: 'Número de Alertas',
                        data: responseData.map(d => d.count),
                        backgroundColor: '#17a2b8',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        },

        _checkNewAlerts: function (currentAlerts) {
            if (!this.previous_alerts) {
                this.previous_alerts = currentAlerts;
                return;
            }

            var self = this;
            var previousIds = this.previous_alerts.map(a => a.id);
            var newAlerts = currentAlerts.filter(a => !previousIds.includes(a.id));

            if (newAlerts.length > 0) {
                newAlerts.forEach(function (alert) {
                    self._notifyNewAlert(alert);
                });
            }

            this.previous_alerts = currentAlerts;
        },

        _notifyNewAlert: function (alert) {
            // Notificación sonora
            if (this.sound_enabled && (alert.severity === 'critical' || alert.severity === 'error')) {
                this._playAlertSound(alert.severity);
            }

            // Notificación del navegador
            if (Notification && Notification.permission === 'granted') {
                var notification = new Notification('Nueva Alerta MEGASTOCK', {
                    body: alert.title,
                    icon: '/megastock_production_planning/static/src/img/alert-icon.png',
                    tag: 'megastock-alert-' + alert.id
                });

                setTimeout(function() {
                    notification.close();
                }, 5000);
            }

            // Animación visual
            this._animateNewAlert();
        },

        _playAlertSound: function (severity) {
            var audio = new Audio();
            if (severity === 'critical') {
                audio.src = '/megastock_production_planning/static/src/sounds/critical-alert.mp3';
            } else {
                audio.src = '/megastock_production_planning/static/src/sounds/warning-alert.mp3';
            }
            
            audio.play().catch(function(error) {
                console.log('No se pudo reproducir sonido de alerta:', error);
            });
        },

        _animateNewAlert: function () {
            this.$('.alerts-dashboard').addClass('new-alert-flash');
            setTimeout(() => {
                this.$('.alerts-dashboard').removeClass('new-alert-flash');
            }, 1000);
        },

        _setupSoundNotifications: function () {
            // Solicitar permisos de notificación
            if (Notification && Notification.permission === 'default') {
                Notification.requestPermission();
            }
        },

        _acknowledgeAlert: function (alertId) {
            var self = this;
            
            return rpc.query({
                model: 'megastock.production.alert',
                method: 'acknowledge_alert',
                args: [alertId]
            }).then(function (result) {
                if (result) {
                    self._showSuccess('Alerta reconocida correctamente');
                    self._refreshDashboard();
                } else {
                    self._showError('No se pudo reconocer la alerta');
                }
            });
        },

        _resolveAlert: function (alertId) {
            var self = this;
            
            // Mostrar diálogo para nota de resolución
            var resolution_note = prompt('Nota de resolución (opcional):');
            
            return rpc.query({
                model: 'megastock.production.alert',
                method: 'resolve_alert',
                args: [alertId],
                kwargs: {
                    resolution_note: resolution_note
                }
            }).then(function (result) {
                if (result) {
                    self._showSuccess('Alerta resuelta correctamente');
                    self._refreshDashboard();
                } else {
                    self._showError('No se pudo resolver la alerta');
                }
            });
        },

        _escalateAlert: function (alertId) {
            var self = this;

            if (!confirm('¿Está seguro de que desea escalar esta alerta?')) {
                return;
            }
            
            return rpc.query({
                model: 'megastock.production.alert',
                method: 'escalate_alert',
                args: [alertId]
            }).then(function (result) {
                if (result) {
                    self._showSuccess('Alerta escalada correctamente');
                    self._refreshDashboard();
                } else {
                    self._showError('No se pudo escalar la alerta');
                }
            });
        },

        _openAlert: function (alertId) {
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: 'megastock.production.alert',
                res_id: alertId,
                views: [[false, 'form']],
                target: 'new'
            });
        },

        _applyFilters: function () {
            this._loadAlertsData();
        },

        _refreshDashboard: function () {
            var self = this;
            this.$('.alert-refresh i').addClass('fa-spin');
            
            return this._loadAlertsData().finally(function () {
                self.$('.alert-refresh i').removeClass('fa-spin');
            });
        },

        _startAutoRefresh: function () {
            var self = this;
            this.auto_refresh_interval = setInterval(function () {
                self._loadAlertsData();
            }, 30000); // Cada 30 segundos
        },

        _toggleAutoRefresh: function () {
            if (this.auto_refresh_interval) {
                clearInterval(this.auto_refresh_interval);
                this.auto_refresh_interval = null;
                this.$('.toggle-auto-refresh i').removeClass('fa-pause').addClass('fa-play');
                this.$('.toggle-auto-refresh').removeClass('btn-success').addClass('btn-secondary');
            } else {
                this._startAutoRefresh();
                this.$('.toggle-auto-refresh i').removeClass('fa-play').addClass('fa-pause');
                this.$('.toggle-auto-refresh').removeClass('btn-secondary').addClass('btn-success');
            }
        },

        _toggleSoundAlerts: function () {
            this.sound_enabled = !this.sound_enabled;
            
            if (this.sound_enabled) {
                this.$('.toggle-sound-alerts i').removeClass('fa-volume-off').addClass('fa-volume-up');
                this.$('.toggle-sound-alerts').removeClass('btn-secondary').addClass('btn-info');
            } else {
                this.$('.toggle-sound-alerts i').removeClass('fa-volume-up').addClass('fa-volume-off');
                this.$('.toggle-sound-alerts').removeClass('btn-info').addClass('btn-secondary');
            }
        },

        _updateLastRefresh: function () {
            var now = new Date();
            this.$('.last-refresh-time').text(now.toLocaleTimeString());
        },

        _destroyCharts: function () {
            Object.values(this.charts).forEach(function (chart) {
                if (chart && typeof chart.destroy === 'function') {
                    chart.destroy();
                }
            });
            this.charts = {};
        },

        _getSeverityClass: function (severity) {
            var classes = {
                'critical': 'border-danger',
                'error': 'border-warning',
                'warning': 'border-info',
                'info': 'border-success'
            };
            return classes[severity] || 'border-secondary';
        },

        _getPriorityClass: function (priority) {
            if (priority >= 4) return 'alert-high-priority';
            if (priority >= 3) return 'alert-medium-priority';
            return 'alert-low-priority';
        },

        _getTypeBadgeClass: function (type) {
            var classes = {
                'kpi': 'primary',
                'capacity': 'warning',
                'quality': 'danger',
                'schedule': 'info',
                'bottleneck': 'danger',
                'downtime': 'warning',
                'system': 'secondary'
            };
            return classes[type] || 'secondary';
        },

        _getTimeAgo: function (dateString) {
            var date = new Date(dateString);
            var now = new Date();
            var diff = now - date;
            var minutes = Math.floor(diff / 60000);
            
            if (minutes < 1) return 'Ahora';
            if (minutes < 60) return minutes + ' min';
            
            var hours = Math.floor(minutes / 60);
            if (hours < 24) return hours + ' h';
            
            var days = Math.floor(hours / 24);
            return days + ' d';
        },

        _showSuccess: function (message) {
            this.displayNotification({
                type: 'success',
                title: 'Éxito',
                message: message
            });
        },

        _showError: function (message) {
            this.displayNotification({
                type: 'danger',
                title: 'Error',
                message: message
            });
        }
    });

    core.action_registry.add('alert_dashboard', AlertDashboard);
    
    return AlertDashboard;
});