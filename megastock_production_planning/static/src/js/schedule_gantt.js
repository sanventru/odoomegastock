odoo.define('megastock_production_planning.ScheduleGantt', function (require) {
'use strict';

var AbstractAction = require('web.AbstractAction');
var core = require('web.core');
var rpc = require('web.rpc');
var session = require('web.session');
var QWeb = core.qweb;
var _t = core._t;

var ScheduleGantt = AbstractAction.extend({
    template: 'ScheduleGanttMain',
    
    events: {
        'click .refresh-gantt': '_onRefreshGantt',
        'change .gantt-date-filter': '_onDateFilterChange',
        'change .gantt-line-filter': '_onLineFilterChange',
        'click .schedule-item': '_onScheduleItemClick',
        'click .add-schedule': '_onAddSchedule',
        'click .optimize-schedule': '_onOptimizeSchedule',
        'change .gantt-view-mode': '_onViewModeChange',
    },

    init: function(parent, context) {
        this._super(parent, context);
        this.ganttData = {};
        this.selectedDateFrom = moment().format('YYYY-MM-DD');
        this.selectedDateTo = moment().add(7, 'days').format('YYYY-MM-DD');
        this.selectedLine = 'all';
        this.viewMode = 'week'; // week, month, day
        this.ganttContainer = null;
        this.draggedItem = null;
    },

    willStart: function() {
        var self = this;
        return this._super().then(function() {
            return self._loadGanttData();
        });
    },

    start: function() {
        var self = this;
        return this._super().then(function() {
            self._renderGanttChart();
            self._setupGanttInteractions();
        });
    },

    destroy: function() {
        if (this.ganttContainer) {
            this.ganttContainer.remove();
        }
        this._super();
    },

    // === MÉTODOS DE CARGA DE DATOS ===

    _loadGanttData: function() {
        var self = this;
        return rpc.query({
            model: 'megastock.production.schedule',
            method: 'get_gantt_data',
            args: [this.selectedDateFrom, this.selectedDateTo],
            kwargs: {
                line_filter: this.selectedLine,
                context: session.user_context,
            }
        }).then(function(data) {
            self.ganttData = data;
            return data;
        });
    },

    _loadWorkcenters: function() {
        var domain = [];
        if (this.selectedLine !== 'all') {
            domain.push(['production_line_type', '=', this.selectedLine]);
        }

        return rpc.query({
            model: 'mrp.workcenter',
            method: 'search_read',
            args: [domain],
            kwargs: {
                fields: ['name', 'production_line_type', 'capacity_hours', 'time_efficiency'],
                order: 'name'
            }
        });
    },

    _loadScheduleConflicts: function() {
        return rpc.query({
            model: 'megastock.production.schedule',
            method: 'detect_schedule_conflicts',
            args: [this.selectedDateFrom, this.selectedDateTo],
            kwargs: {
                line_filter: this.selectedLine
            }
        });
    },

    // === MÉTODOS DE RENDERIZADO ===

    _renderGanttChart: function() {
        var self = this;
        
        Promise.all([
            this._loadWorkcenters(),
            this._loadScheduleConflicts()
        ]).then(function(results) {
            var workcenters = results[0];
            var conflicts = results[1];
            
            self._createGanttContainer();
            self._renderGanttHeader(workcenters);
            self._renderGanttRows(workcenters);
            self._renderScheduleItems();
            self._highlightConflicts(conflicts);
            
            // Actualizar timestamp
            self.$('.gantt-last-update').text(moment().format('DD/MM/YYYY HH:mm:ss'));
        });
    },

    _createGanttContainer: function() {
        var self = this;
        var $ganttArea = this.$('.gantt-chart-area');
        
        // Limpiar contenedor anterior
        $ganttArea.empty();
        
        // Crear estructura del Gantt
        var ganttHtml = QWeb.render('GanttChartStructure', {
            dateFrom: this.selectedDateFrom,
            dateTo: this.selectedDateTo,
            viewMode: this.viewMode,
            _t: _t
        });
        
        $ganttArea.html(ganttHtml);
        this.ganttContainer = $ganttArea.find('.gantt-container');
    },

    _renderGanttHeader: function(workcenters) {
        var $header = this.ganttContainer.find('.gantt-header');
        var timeScale = this._generateTimeScale();
        
        var headerHtml = QWeb.render('GanttHeader', {
            timeScale: timeScale,
            viewMode: this.viewMode
        });
        
        $header.html(headerHtml);
    },

    _renderGanttRows: function(workcenters) {
        var self = this;
        var $rows = this.ganttContainer.find('.gantt-rows');
        
        var rowsHtml = '';
        workcenters.forEach(function(workcenter, index) {
            rowsHtml += QWeb.render('GanttRow', {
                workcenter: workcenter,
                index: index,
                timeScale: self._generateTimeScale()
            });
        });
        
        $rows.html(rowsHtml);
    },

    _renderScheduleItems: function() {
        var self = this;
        
        this.ganttData.forEach(function(schedule) {
            self._renderScheduleItem(schedule);
        });
    },

    _renderScheduleItem: function(schedule) {
        var $row = this.ganttContainer.find('[data-workcenter-id="' + schedule.workcenter_id + '"]');
        if (!$row.length) return;
        
        var startTime = moment(schedule.start);
        var endTime = moment(schedule.end);
        var duration = endTime.diff(startTime, 'hours', true);
        
        // Calcular posición y ancho
        var position = this._calculateItemPosition(startTime);
        var width = this._calculateItemWidth(duration);
        
        var itemHtml = QWeb.render('GanttScheduleItem', {
            schedule: schedule,
            position: position,
            width: width,
            duration: duration
        });
        
        var $item = $(itemHtml);
        $item.data('schedule-data', schedule);
        
        $row.find('.gantt-row-content').append($item);
        
        // Hacer draggable
        this._makeItemDraggable($item);
    },

    _highlightConflicts: function(conflicts) {
        var self = this;
        
        conflicts.forEach(function(conflict) {
            var $items = self.ganttContainer.find('[data-schedule-id="' + conflict.schedule_id + '"]');
            $items.addClass('schedule-conflict');
            $items.attr('title', 'Conflicto: ' + conflict.reason);
        });
    },

    // === MÉTODOS DE INTERACCIÓN ===

    _setupGanttInteractions: function() {
        this._setupDragAndDrop();
        this._setupZoom();
        this._setupTooltips();
        this._setupContextMenu();
    },

    _setupDragAndDrop: function() {
        var self = this;
        
        // Configurar drop zones
        this.ganttContainer.find('.gantt-row-content').droppable({
            accept: '.schedule-item',
            tolerance: 'pointer',
            drop: function(event, ui) {
                var $dropRow = $(this);
                var workcenterId = $dropRow.closest('.gantt-row').data('workcenter-id');
                var scheduleData = ui.draggable.data('schedule-data');
                
                self._handleScheduleDrop(scheduleData, workcenterId, event.pageX);
            }
        });
    },

    _makeItemDraggable: function($item) {
        var self = this;
        
        $item.draggable({
            containment: this.ganttContainer,
            helper: 'clone',
            opacity: 0.7,
            cursor: 'move',
            start: function(event, ui) {
                self.draggedItem = $item.data('schedule-data');
                $item.addClass('dragging');
            },
            stop: function(event, ui) {
                $item.removeClass('dragging');
                self.draggedItem = null;
            }
        });
    },

    _setupZoom: function() {
        var self = this;
        
        this.$('.gantt-zoom-controls').on('click', '.zoom-btn', function(e) {
            var zoomType = $(this).data('zoom');
            self._handleZoom(zoomType);
        });
    },

    _setupTooltips: function() {
        this.ganttContainer.find('.schedule-item').each(function() {
            var $item = $(this);
            var scheduleData = $item.data('schedule-data');
            
            $item.tooltip({
                title: self._generateTooltipContent(scheduleData),
                html: true,
                placement: 'top',
                trigger: 'hover'
            });
        });
    },

    _setupContextMenu: function() {
        var self = this;
        
        this.ganttContainer.on('contextmenu', '.schedule-item', function(e) {
            e.preventDefault();
            var scheduleData = $(this).data('schedule-data');
            self._showContextMenu(e.pageX, e.pageY, scheduleData);
        });
    },

    // === MÉTODOS DE CÁLCULO ===

    _generateTimeScale: function() {
        var timeScale = [];
        var current = moment(this.selectedDateFrom);
        var end = moment(this.selectedDateTo);
        
        while (current.isSameOrBefore(end)) {
            timeScale.push({
                date: current.format('YYYY-MM-DD'),
                label: current.format('DD/MM'),
                dayName: current.format('ddd'),
                isWeekend: current.day() === 0 || current.day() === 6
            });
            current.add(1, 'day');
        }
        
        return timeScale;
    },

    _calculateItemPosition: function(startTime) {
        var chartStart = moment(this.selectedDateFrom);
        var hoursFromStart = startTime.diff(chartStart, 'hours', true);
        var pixelsPerHour = this._getPixelsPerHour();
        
        return hoursFromStart * pixelsPerHour;
    },

    _calculateItemWidth: function(durationHours) {
        var pixelsPerHour = this._getPixelsPerHour();
        return Math.max(20, durationHours * pixelsPerHour); // Mínimo 20px
    },

    _getPixelsPerHour: function() {
        var containerWidth = this.ganttContainer.find('.gantt-header').width();
        var totalHours = moment(this.selectedDateTo).diff(moment(this.selectedDateFrom), 'hours');
        return containerWidth / totalHours;
    },

    _generateTooltipContent: function(scheduleData) {
        return `
            <strong>${scheduleData.production_name}</strong><br/>
            <strong>Producto:</strong> ${scheduleData.product_name}<br/>
            <strong>Cantidad:</strong> ${scheduleData.quantity}<br/>
            <strong>Inicio:</strong> ${moment(scheduleData.start).format('DD/MM HH:mm')}<br/>
            <strong>Fin:</strong> ${moment(scheduleData.end).format('DD/MM HH:mm')}<br/>
            <strong>Duración:</strong> ${scheduleData.duration.toFixed(1)}h<br/>
            <strong>Estado:</strong> ${scheduleData.state}<br/>
            <strong>Operadores:</strong> ${scheduleData.operators.join(', ') || 'N/A'}
        `;
    },

    // === EVENT HANDLERS ===

    _onRefreshGantt: function(ev) {
        ev.preventDefault();
        this._loadGanttData().then(() => {
            this._renderGanttChart();
        });
    },

    _onDateFilterChange: function(ev) {
        var filterType = $(ev.currentTarget).data('filter-type');
        var value = $(ev.currentTarget).val();
        
        if (filterType === 'from') {
            this.selectedDateFrom = value;
        } else {
            this.selectedDateTo = value;
        }
        
        this._loadGanttData().then(() => {
            this._renderGanttChart();
        });
    },

    _onLineFilterChange: function(ev) {
        this.selectedLine = $(ev.currentTarget).val();
        this._loadGanttData().then(() => {
            this._renderGanttChart();
        });
    },

    _onScheduleItemClick: function(ev) {
        var scheduleData = $(ev.currentTarget).data('schedule-data');
        this._showScheduleDetail(scheduleData);
    },

    _onAddSchedule: function(ev) {
        ev.preventDefault();
        this._launchScheduleWizard();
    },

    _onOptimizeSchedule: function(ev) {
        ev.preventDefault();
        this._launchOptimizationWizard();
    },

    _onViewModeChange: function(ev) {
        this.viewMode = $(ev.currentTarget).val();
        this._renderGanttChart();
    },

    // === MÉTODOS DE ACCIÓN ===

    _handleScheduleDrop: function(scheduleData, newWorkcenterId, dropX) {
        var self = this;
        
        // Calcular nueva fecha basada en posición X
        var newStartTime = this._calculateTimeFromPosition(dropX);
        
        rpc.query({
            model: 'megastock.production.schedule',
            method: 'reschedule_item',
            args: [scheduleData.id],
            kwargs: {
                new_workcenter_id: newWorkcenterId,
                new_start_time: newStartTime.format('YYYY-MM-DD HH:mm:ss')
            }
        }).then(function(result) {
            if (result.success) {
                self.displayNotification({
                    type: 'success',
                    title: _t('Reprogramado'),
                    message: result.message
                });
                self._renderGanttChart();
            } else {
                self.displayNotification({
                    type: 'warning',
                    title: _t('Error'),
                    message: result.message
                });
            }
        });
    },

    _handleZoom: function(zoomType) {
        var newDateRange;
        
        switch(zoomType) {
            case 'day':
                newDateRange = {
                    from: moment().format('YYYY-MM-DD'),
                    to: moment().add(1, 'day').format('YYYY-MM-DD')
                };
                break;
            case 'week':
                newDateRange = {
                    from: moment().startOf('week').format('YYYY-MM-DD'),
                    to: moment().endOf('week').format('YYYY-MM-DD')
                };
                break;
            case 'month':
                newDateRange = {
                    from: moment().startOf('month').format('YYYY-MM-DD'),
                    to: moment().endOf('month').format('YYYY-MM-DD')
                };
                break;
        }
        
        if (newDateRange) {
            this.selectedDateFrom = newDateRange.from;
            this.selectedDateTo = newDateRange.to;
            this.viewMode = zoomType;
            
            // Actualizar controles
            this.$('.gantt-date-from').val(this.selectedDateFrom);
            this.$('.gantt-date-to').val(this.selectedDateTo);
            this.$('.gantt-view-mode').val(this.viewMode);
            
            this._loadGanttData().then(() => {
                this._renderGanttChart();
            });
        }
    },

    _calculateTimeFromPosition: function(positionX) {
        var chartStart = moment(this.selectedDateFrom);
        var pixelsPerHour = this._getPixelsPerHour();
        var hoursFromStart = positionX / pixelsPerHour;
        
        return chartStart.add(hoursFromStart, 'hours');
    },

    _showContextMenu: function(x, y, scheduleData) {
        var self = this;
        var contextMenuHtml = QWeb.render('GanttContextMenu', {
            schedule: scheduleData,
            _t: _t
        });
        
        var $menu = $(contextMenuHtml);
        $menu.css({
            position: 'absolute',
            left: x,
            top: y,
            zIndex: 1000
        });
        
        $('body').append($menu);
        
        // Eventos del menú
        $menu.on('click', '.context-menu-item', function(e) {
            var action = $(this).data('action');
            self._executeContextAction(action, scheduleData);
            $menu.remove();
        });
        
        // Cerrar al hacer click fuera
        $(document).one('click', function() {
            $menu.remove();
        });
    },

    _executeContextAction: function(action, scheduleData) {
        switch(action) {
            case 'view':
                this._showScheduleDetail(scheduleData);
                break;
            case 'edit':
                this._editSchedule(scheduleData);
                break;
            case 'reschedule':
                this._rescheduleSchedule(scheduleData);
                break;
            case 'cancel':
                this._cancelSchedule(scheduleData);
                break;
        }
    },

    _showScheduleDetail: function(scheduleData) {
        this.do_action({
            name: _t('Detalle Programación'),
            type: 'ir.actions.act_window',
            res_model: 'megastock.production.schedule',
            res_id: scheduleData.id,
            view_mode: 'form',
            target: 'new'
        });
    },

    _editSchedule: function(scheduleData) {
        this.do_action({
            name: _t('Editar Programación'),
            type: 'ir.actions.act_window',
            res_model: 'megastock.production.schedule',
            res_id: scheduleData.id,
            view_mode: 'form',
            target: 'current'
        });
    },

    _rescheduleSchedule: function(scheduleData) {
        this.do_action({
            name: _t('Reprogramar'),
            type: 'ir.actions.act_window',
            res_model: 'megastock.reschedule.wizard',
            view_mode: 'form',
            target: 'new',
            context: {
                'default_schedule_id': scheduleData.id
            }
        });
    },

    _cancelSchedule: function(scheduleData) {
        var self = this;
        
        rpc.query({
            model: 'megastock.production.schedule',
            method: 'action_cancel',
            args: [scheduleData.id]
        }).then(function(result) {
            self.displayNotification({
                type: 'success',
                title: _t('Cancelado'),
                message: _t('Programación cancelada')
            });
            self._renderGanttChart();
        });
    },

    _launchScheduleWizard: function() {
        this.do_action({
            name: _t('Nueva Programación'),
            type: 'ir.actions.act_window',
            res_model: 'megastock.schedule.wizard',
            view_mode: 'form',
            target: 'new',
            context: {
                'default_date_from': this.selectedDateFrom,
                'default_date_to': this.selectedDateTo,
                'default_line_filter': this.selectedLine
            }
        });
    },

    _launchOptimizationWizard: function() {
        this.do_action({
            name: _t('Optimizar Cronograma'),
            type: 'ir.actions.act_window',
            res_model: 'megastock.schedule.optimization.wizard',
            view_mode: 'form',
            target: 'new',
            context: {
                'default_date_from': this.selectedDateFrom,
                'default_date_to': this.selectedDateTo,
                'default_line_filter': this.selectedLine
            }
        });
    },

});

core.action_registry.add('megastock_schedule_gantt', ScheduleGantt);

return ScheduleGantt;

});