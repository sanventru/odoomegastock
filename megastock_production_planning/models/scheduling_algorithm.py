# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class SchedulingAlgorithm(models.Model):
    _name = 'megastock.scheduling.algorithm'
    _description = 'Algoritmos de Programación de Producción'
    _order = 'priority desc, name'
    
    name = fields.Char(
        string='Nombre del Algoritmo',
        required=True,
        help='Nombre descriptivo del algoritmo'
    )
    
    code = fields.Char(
        string='Código',
        required=True,
        help='Código único del algoritmo'
    )
    
    algorithm_type = fields.Selection([
        ('fifo', 'FIFO - First In, First Out'),
        ('lifo', 'LIFO - Last In, First Out'),
        ('spt', 'SPT - Shortest Processing Time'),  
        ('lpt', 'LPT - Longest Processing Time'),
        ('edd', 'EDD - Earliest Due Date'),
        ('cr', 'CR - Critical Ratio'),
        ('slack', 'Slack Time'),
        ('genetic', 'Algoritmo Genético'),
        ('simulated_annealing', 'Simulated Annealing'),
        ('tabu_search', 'Búsqueda Tabú'),
        ('johnson', 'Regla de Johnson'),
        ('custom', 'Personalizado')
    ], string='Tipo de Algoritmo', required=True)
    
    priority = fields.Integer(
        string='Prioridad',
        default=5,
        help='Prioridad del algoritmo (1-10)'
    )
    
    active = fields.Boolean(
        string='Activo',
        default=True
    )
    
    # === CONFIGURACIÓN DEL ALGORITMO ===
    optimization_objective = fields.Selection([
        ('minimize_makespan', 'Minimizar Makespan'),
        ('minimize_total_completion', 'Minimizar Tiempo Total'),
        ('minimize_lateness', 'Minimizar Tardanza'),
        ('minimize_setup_time', 'Minimizar Tiempo Setup'),
        ('maximize_utilization', 'Maximizar Utilización'),
        ('minimize_cost', 'Minimizar Costos'),
        ('balance_workload', 'Balancear Carga')
    ], string='Objetivo de Optimización', default='minimize_makespan')
    
    # === PARÁMETROS ESPECÍFICOS ===
    # Para algoritmos genéticos
    population_size = fields.Integer(
        string='Tamaño Población',
        default=50,
        help='Tamaño de población para algoritmo genético'
    )
    
    generations = fields.Integer(
        string='Generaciones',
        default=100,
        help='Número de generaciones para algoritmo genético'
    )
    
    mutation_rate = fields.Float(
        string='Tasa Mutación',
        default=0.1,
        help='Tasa de mutación (0.0-1.0)'
    )
    
    crossover_rate = fields.Float(
        string='Tasa Cruce',
        default=0.8,
        help='Tasa de cruce (0.0-1.0)'
    )
    
    # Para simulated annealing
    initial_temperature = fields.Float(
        string='Temperatura Inicial',
        default=1000.0,
        help='Temperatura inicial para simulated annealing'
    )
    
    cooling_rate = fields.Float(
        string='Tasa Enfriamiento',
        default=0.95,
        help='Tasa de enfriamiento (0.0-1.0)'
    )
    
    min_temperature = fields.Float(
        string='Temperatura Mínima',
        default=1.0,
        help='Temperatura mínima para parar'
    )
    
    # Para búsqueda tabú
    tabu_list_size = fields.Integer(
        string='Tamaño Lista Tabú',
        default=20,
        help='Tamaño de la lista tabú'
    )
    
    max_iterations = fields.Integer(
        string='Máximo Iteraciones',
        default=1000,
        help='Máximo número de iteraciones'
    )
    
    # === RESTRICCIONES ===
    consider_setup_times = fields.Boolean(
        string='Considerar Tiempos Setup',
        default=True,
        help='Incluir tiempos de setup en programación'
    )
    
    consider_capacity_constraints = fields.Boolean(
        string='Considerar Restricciones Capacidad',
        default=True,
        help='Respetar límites de capacidad'
    )
    
    consider_material_availability = fields.Boolean(
        string='Considerar Disponibilidad Material',
        default=True,
        help='Verificar disponibilidad de materiales'
    )
    
    allow_preemption = fields.Boolean(
        string='Permitir Interrupción',
        default=False,
        help='Permitir interrumpir trabajos en proceso'
    )
    
    # === CONFIGURACIÓN ESPECÍFICA POR LÍNEA ===
    applicable_lines = fields.Selection([
        ('all', 'Todas las Líneas'),
        ('papel_periodico', 'Papel Periódico'),
        ('cajas', 'Cajas & Planchas'),
        ('lamina_micro', 'Lámina Micro Corrugada')
    ], string='Líneas Aplicables', default='all')
    
    # === ESTADÍSTICAS DE USO ===
    usage_count = fields.Integer(
        string='Veces Utilizado',
        default=0,
        readonly=True
    )
    
    average_performance = fields.Float(
        string='Performance Promedio',
        default=0.0,
        readonly=True,
        help='Performance promedio del algoritmo'
    )
    
    last_execution_time = fields.Float(
        string='Último Tiempo Ejecución (s)',
        readonly=True,
        help='Tiempo de ejecución de la última corrida'
    )
    
    success_rate = fields.Float(
        string='Tasa de Éxito (%)',
        default=0.0,
        readonly=True
    )
    
    description = fields.Text(
        string='Descripción',
        help='Descripción detallada del algoritmo'
    )
    
    # === MÉTODOS DE PROGRAMACIÓN ===
    
    def execute_algorithm(self, production_orders, workcenters=None, context=None):
        """Ejecutar algoritmo de programación"""
        self.ensure_one()
        
        start_time = datetime.now()
        
        try:
            if self.algorithm_type == 'fifo':
                result = self._execute_fifo(production_orders)
            elif self.algorithm_type == 'lifo':
                result = self._execute_lifo(production_orders)
            elif self.algorithm_type == 'spt':
                result = self._execute_spt(production_orders)
            elif self.algorithm_type == 'lpt':
                result = self._execute_lpt(production_orders)
            elif self.algorithm_type == 'edd':
                result = self._execute_edd(production_orders)
            elif self.algorithm_type == 'cr':
                result = self._execute_critical_ratio(production_orders)
            elif self.algorithm_type == 'slack':
                result = self._execute_slack_time(production_orders)
            elif self.algorithm_type == 'genetic':
                result = self._execute_genetic_algorithm(production_orders, workcenters)
            elif self.algorithm_type == 'simulated_annealing':
                result = self._execute_simulated_annealing(production_orders, workcenters)
            elif self.algorithm_type == 'tabu_search':
                result = self._execute_tabu_search(production_orders, workcenters)
            elif self.algorithm_type == 'johnson':
                result = self._execute_johnson_rule(production_orders, workcenters)
            else:
                result = self._execute_custom_algorithm(production_orders, workcenters, context)
            
            # Registrar estadísticas
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            self.usage_count += 1
            self.last_execution_time = execution_time
            
            if result.get('success', True):
                # Actualizar tasa de éxito
                success_count = (self.success_rate * (self.usage_count - 1) / 100.0) + 1
                self.success_rate = (success_count / self.usage_count) * 100
            
            _logger.info(f"Algoritmo {self.name} ejecutado en {execution_time:.2f}s")
            
            return result
            
        except Exception as e:
            _logger.error(f"Error ejecutando algoritmo {self.name}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'schedule': []
            }
    
    def _execute_fifo(self, production_orders):
        """Ejecutar algoritmo FIFO"""
        # Ordenar por fecha de creación
        sorted_orders = production_orders.sorted('create_date')
        
        schedule = []
        current_time = datetime.now()
        
        for order in sorted_orders:
            duration = self._estimate_production_duration(order)
            
            schedule.append({
                'production_id': order.id,
                'start_time': current_time,
                'end_time': current_time + timedelta(hours=duration),
                'duration': duration,
                'sequence': len(schedule) + 1
            })
            
            current_time += timedelta(hours=duration)
        
        return {
            'success': True,
            'algorithm': 'FIFO',
            'schedule': schedule,
            'makespan': (current_time - datetime.now()).total_seconds() / 3600.0
        }
    
    def _execute_lifo(self, production_orders):
        """Ejecutar algoritmo LIFO"""
        # Ordenar por fecha de creación (inverso)
        sorted_orders = production_orders.sorted('create_date', reverse=True)
        
        schedule = []
        current_time = datetime.now()
        
        for order in sorted_orders:
            duration = self._estimate_production_duration(order)
            
            schedule.append({
                'production_id': order.id,
                'start_time': current_time,
                'end_time': current_time + timedelta(hours=duration),
                'duration': duration,
                'sequence': len(schedule) + 1
            })
            
            current_time += timedelta(hours=duration)
        
        return {
            'success': True,
            'algorithm': 'LIFO',
            'schedule': schedule,
            'makespan': (current_time - datetime.now()).total_seconds() / 3600.0
        }
    
    def _execute_spt(self, production_orders):
        """Ejecutar algoritmo SPT (Shortest Processing Time)"""
        # Calcular duraciones y ordenar
        order_durations = []
        for order in production_orders:
            duration = self._estimate_production_duration(order)
            order_durations.append((order, duration))
        
        # Ordenar por duración ascendente
        order_durations.sort(key=lambda x: x[1])
        
        schedule = []
        current_time = datetime.now()
        
        for order, duration in order_durations:
            schedule.append({
                'production_id': order.id,
                'start_time': current_time,
                'end_time': current_time + timedelta(hours=duration),
                'duration': duration,
                'sequence': len(schedule) + 1
            })
            
            current_time += timedelta(hours=duration)
        
        return {
            'success': True,
            'algorithm': 'SPT',
            'schedule': schedule,
            'makespan': (current_time - datetime.now()).total_seconds() / 3600.0
        }
    
    def _execute_lpt(self, production_orders):
        """Ejecutar algoritmo LPT (Longest Processing Time)"""
        # Calcular duraciones y ordenar
        order_durations = []
        for order in production_orders:
            duration = self._estimate_production_duration(order)
            order_durations.append((order, duration))
        
        # Ordenar por duración descendente
        order_durations.sort(key=lambda x: x[1], reverse=True)
        
        schedule = []
        current_time = datetime.now()
        
        for order, duration in order_durations:
            schedule.append({
                'production_id': order.id,
                'start_time': current_time,
                'end_time': current_time + timedelta(hours=duration),
                'duration': duration,
                'sequence': len(schedule) + 1
            })
            
            current_time += timedelta(hours=duration)
        
        return {
            'success': True,
            'algorithm': 'LPT',
            'schedule': schedule,
            'makespan': (current_time - datetime.now()).total_seconds() / 3600.0
        }
    
    def _execute_edd(self, production_orders):
        """Ejecutar algoritmo EDD (Earliest Due Date)"""
        # Ordenar por fecha de entrega
        sorted_orders = production_orders.sorted('date_planned_finished')
        
        schedule = []
        current_time = datetime.now()
        
        for order in sorted_orders:
            duration = self._estimate_production_duration(order)
            
            schedule.append({
                'production_id': order.id,
                'start_time': current_time,
                'end_time': current_time + timedelta(hours=duration),
                'duration': duration,
                'sequence': len(schedule) + 1,
                'due_date': order.date_planned_finished
            })
            
            current_time += timedelta(hours=duration)
        
        return {
            'success': True,
            'algorithm': 'EDD',
            'schedule': schedule,
            'makespan': (current_time - datetime.now()).total_seconds() / 3600.0
        }
    
    def _execute_critical_ratio(self, production_orders):
        """Ejecutar algoritmo Critical Ratio"""
        current_time = datetime.now()
        
        # Calcular ratio crítico para cada orden
        order_ratios = []
        for order in production_orders:
            duration = self._estimate_production_duration(order)
            
            if order.date_planned_finished:
                time_remaining = (order.date_planned_finished - current_time).total_seconds() / 3600.0
                critical_ratio = time_remaining / duration if duration > 0 else float('inf')
            else:
                critical_ratio = float('inf')
            
            order_ratios.append((order, duration, critical_ratio))
        
        # Ordenar por ratio crítico ascendente (más crítico primero)
        order_ratios.sort(key=lambda x: x[2])
        
        schedule = []
        
        for order, duration, ratio in order_ratios:
            schedule.append({
                'production_id': order.id,
                'start_time': current_time,
                'end_time': current_time + timedelta(hours=duration),
                'duration': duration,
                'sequence': len(schedule) + 1,
                'critical_ratio': ratio
            })
            
            current_time += timedelta(hours=duration)
        
        return {
            'success': True,
            'algorithm': 'Critical Ratio',
            'schedule': schedule,
            'makespan': (current_time - datetime.now()).total_seconds() / 3600.0
        }
    
    def _execute_slack_time(self, production_orders):
        """Ejecutar algoritmo Slack Time"""
        current_time = datetime.now()
        
        # Calcular slack time para cada orden
        order_slacks = []
        for order in production_orders:
            duration = self._estimate_production_duration(order)
            
            if order.date_planned_finished:
                time_available = (order.date_planned_finished - current_time).total_seconds() / 3600.0
                slack_time = time_available - duration
            else:
                slack_time = float('inf')
            
            order_slacks.append((order, duration, slack_time))
        
        # Ordenar por slack time ascendente (menos holgura primero)
        order_slacks.sort(key=lambda x: x[2])
        
        schedule = []
        
        for order, duration, slack in order_slacks:
            schedule.append({
                'production_id': order.id,
                'start_time': current_time,
                'end_time': current_time + timedelta(hours=duration),
                'duration': duration,
                'sequence': len(schedule) + 1,
                'slack_time': slack
            })
            
            current_time += timedelta(hours=duration)
        
        return {
            'success': True,
            'algorithm': 'Slack Time',
            'schedule': schedule,
            'makespan': (current_time - datetime.now()).total_seconds() / 3600.0
        }
    
    def _execute_genetic_algorithm(self, production_orders, workcenters):
        """Ejecutar algoritmo genético (simplificado)"""
        import random
        
        # Implementación simplificada de algoritmo genético
        orders_list = list(production_orders)
        n_orders = len(orders_list)
        
        if n_orders <= 1:
            return self._execute_fifo(production_orders)
        
        # Generar población inicial
        population = []
        for _ in range(self.population_size):
            individual = orders_list.copy()
            random.shuffle(individual)
            population.append(individual)
        
        # Evolución
        for generation in range(self.generations):
            # Evaluar fitness de cada individuo
            fitness_scores = []
            for individual in population:
                fitness = self._calculate_fitness(individual)
                fitness_scores.append((individual, fitness))
            
            # Seleccionar mejores individuos
            fitness_scores.sort(key=lambda x: x[1])
            survivors = [ind for ind, _ in fitness_scores[:self.population_size // 2]]
            
            # Generar nueva población
            new_population = survivors.copy()
            
            while len(new_population) < self.population_size:
                # Seleccionar padres
                parent1 = random.choice(survivors)
                parent2 = random.choice(survivors)
                
                # Cruzamiento
                if random.random() < self.crossover_rate:
                    child = self._crossover(parent1, parent2)
                else:
                    child = parent1.copy()
                
                # Mutación
                if random.random() < self.mutation_rate:
                    child = self._mutate(child)
                
                new_population.append(child)
            
            population = new_population
        
        # Obtener mejor solución
        best_individual = min(population, key=self._calculate_fitness)
        
        # Generar programa
        schedule = self._generate_schedule_from_sequence(best_individual)
        
        return {
            'success': True,
            'algorithm': 'Genetic Algorithm',
            'schedule': schedule,
            'generations': self.generations,
            'population_size': self.population_size
        }
    
    def _calculate_fitness(self, individual):
        """Calcular fitness de un individuo (secuencia de órdenes)"""
        # Fitness basado en makespan (menor es mejor)
        current_time = datetime.now()
        total_time = 0
        
        for order in individual:
            duration = self._estimate_production_duration(order)
            total_time += duration
        
        return total_time
    
    def _crossover(self, parent1, parent2):
        """Operador de cruzamiento (Order Crossover - OX)"""
        n = len(parent1)
        
        # Seleccionar puntos de cruce
        start = random.randint(0, n - 1)
        end = random.randint(start + 1, n)
        
        # Crear hijo con segmento del padre1
        child = [None] * n
        for i in range(start, end):
            child[i] = parent1[i]
        
        # Completar con elementos del padre2 en orden
        pointer = 0
        for i in range(n):
            if child[i] is None:
                while parent2[pointer] in child:
                    pointer += 1
                child[i] = parent2[pointer]
                pointer += 1
        
        return child
    
    def _mutate(self, individual):
        """Operador de mutación (intercambio)"""
        child = individual.copy()
        
        # Intercambiar dos elementos aleatorios
        i, j = random.sample(range(len(child)), 2)
        child[i], child[j] = child[j], child[i]
        
        return child
    
    def _generate_schedule_from_sequence(self, sequence):
        """Generar programa desde secuencia de órdenes"""
        schedule = []
        current_time = datetime.now()
        
        for idx, order in enumerate(sequence):
            duration = self._estimate_production_duration(order)
            
            schedule.append({
                'production_id': order.id,
                'start_time': current_time,
                'end_time': current_time + timedelta(hours=duration),
                'duration': duration,
                'sequence': idx + 1
            })
            
            current_time += timedelta(hours=duration)
        
        return schedule
    
    def _execute_simulated_annealing(self, production_orders, workcenters):
        """Ejecutar algoritmo Simulated Annealing (simplificado)"""
        import random
        import math
        
        orders_list = list(production_orders)
        
        if len(orders_list) <= 1:
            return self._execute_fifo(production_orders)
        
        # Solución inicial (aleatoria)
        current_solution = orders_list.copy()
        random.shuffle(current_solution)
        current_cost = self._calculate_fitness(current_solution)
        
        best_solution = current_solution.copy()
        best_cost = current_cost
        
        temperature = self.initial_temperature
        
        while temperature > self.min_temperature:
            # Generar vecino (intercambiar dos elementos)
            neighbor = current_solution.copy()
            i, j = random.sample(range(len(neighbor)), 2)
            neighbor[i], neighbor[j] = neighbor[j], neighbor[i]
            
            neighbor_cost = self._calculate_fitness(neighbor)
            
            # Decidir si aceptar la nueva solución
            if neighbor_cost < current_cost:
                # Mejor solución - siempre aceptar
                current_solution = neighbor
                current_cost = neighbor_cost
                
                if neighbor_cost < best_cost:
                    best_solution = neighbor.copy()
                    best_cost = neighbor_cost
            else:
                # Peor solución - aceptar con probabilidad
                delta = neighbor_cost - current_cost
                probability = math.exp(-delta / temperature)
                
                if random.random() < probability:
                    current_solution = neighbor
                    current_cost = neighbor_cost
            
            # Enfriar
            temperature *= self.cooling_rate
        
        # Generar programa final
        schedule = self._generate_schedule_from_sequence(best_solution)
        
        return {
            'success': True,
            'algorithm': 'Simulated Annealing',
            'schedule': schedule,
            'best_cost': best_cost,
            'initial_temperature': self.initial_temperature
        }
    
    def _execute_tabu_search(self, production_orders, workcenters):
        """Ejecutar búsqueda tabú (simplificado)"""
        import random
        
        orders_list = list(production_orders)
        
        if len(orders_list) <= 1:
            return self._execute_fifo(production_orders)
        
        # Solución inicial
        current_solution = orders_list.copy()
        random.shuffle(current_solution)
        
        best_solution = current_solution.copy()
        best_cost = self._calculate_fitness(best_solution)
        
        tabu_list = []
        
        for iteration in range(self.max_iterations):
            # Generar vecindario (todas las permutaciones de 2 elementos)
            neighbors = []
            for i in range(len(current_solution)):
                for j in range(i + 1, len(current_solution)):
                    neighbor = current_solution.copy()
                    neighbor[i], neighbor[j] = neighbor[j], neighbor[i]
                    
                    # Verificar si no está en lista tabú
                    move = (i, j)
                    if move not in tabu_list:
                        neighbors.append((neighbor, move))
            
            if not neighbors:
                break
            
            # Encontrar mejor vecino
            best_neighbor, best_move = min(neighbors, 
                                         key=lambda x: self._calculate_fitness(x[0]))
            
            current_solution = best_neighbor
            current_cost = self._calculate_fitness(current_solution)
            
            # Actualizar mejor solución global
            if current_cost < best_cost:
                best_solution = current_solution.copy()
                best_cost = current_cost
            
            # Actualizar lista tabú
            tabu_list.append(best_move)
            if len(tabu_list) > self.tabu_list_size:
                tabu_list.pop(0)
        
        # Generar programa final
        schedule = self._generate_schedule_from_sequence(best_solution)
        
        return {
            'success': True,
            'algorithm': 'Tabu Search',
            'schedule': schedule,
            'best_cost': best_cost,
            'iterations': iteration + 1
        }
    
    def _execute_johnson_rule(self, production_orders, workcenters):
        """Ejecutar regla de Johnson para 2 máquinas"""
        # Implementación simplificada para 2 estaciones
        if not workcenters or len(workcenters) != 2:
            return self._execute_spt(production_orders)
        
        # Agrupar órdenes por tiempos en cada máquina
        orders_with_times = []
        
        for order in production_orders:
            time_1 = self._get_operation_time(order, workcenters[0])
            time_2 = self._get_operation_time(order, workcenters[1])
            orders_with_times.append((order, time_1, time_2))
        
        # Aplicar regla de Johnson
        set_1 = []  # min(time_1, time_2) = time_1
        set_2 = []  # min(time_1, time_2) = time_2
        
        for order, time_1, time_2 in orders_with_times:
            if time_1 <= time_2:
                set_1.append((order, time_1, time_2))
            else:
                set_2.append((order, time_1, time_2))
        
        # Ordenar set_1 por tiempo en máquina 1
        set_1.sort(key=lambda x: x[1])
        
        # Ordenar set_2 por tiempo en máquina 2 (descendente)
        set_2.sort(key=lambda x: x[2], reverse=True)
        
        # Combinar secuencias
        final_sequence = [item[0] for item in set_1] + [item[0] for item in set_2]
        
        # Generar programa
        schedule = self._generate_schedule_from_sequence(final_sequence)
        
        return {
            'success': True,
            'algorithm': 'Johnson Rule',
            'schedule': schedule,
            'workcenters': len(workcenters)
        }
    
    def _execute_custom_algorithm(self, production_orders, workcenters, context):
        """Ejecutar algoritmo personalizado"""
        # Implementar lógica específica de MEGASTOCK
        # Por ejemplo: minimizar setup times por tipo de producto
        
        # Agrupar por categoría de producto
        grouped_orders = {}
        for order in production_orders:
            category = order.product_id.categ_id.name
            if category not in grouped_orders:
                grouped_orders[category] = []
            grouped_orders[category].append(order)
        
        # Ordenar cada grupo por prioridad
        final_sequence = []
        for category, orders in grouped_orders.items():
            sorted_orders = sorted(orders, key=lambda o: getattr(o, 'priority', 5), reverse=True)
            final_sequence.extend(sorted_orders)
        
        # Generar programa
        schedule = self._generate_schedule_from_sequence(final_sequence)
        
        return {
            'success': True,
            'algorithm': 'Custom MEGASTOCK',
            'schedule': schedule,
            'categories_grouped': len(grouped_orders)
        }
    
    def _estimate_production_duration(self, production_order):
        """Estimar duración de una orden de producción"""
        if production_order.routing_id:
            total_minutes = 0.0
            for operation in production_order.routing_id.operation_ids:
                op_minutes = (operation.time_cycle * production_order.product_qty) + \
                           (operation.time_mode_batch or 0)
                total_minutes += op_minutes
            return total_minutes / 60.0  # Convertir a horas
        else:
            # Estimación por defecto
            return production_order.product_qty * 0.1  # 0.1 horas por unidad
    
    def _get_operation_time(self, production_order, workcenter):
        """Obtener tiempo de operación en un centro específico"""
        if production_order.routing_id:
            operation = production_order.routing_id.operation_ids.filtered(
                lambda op: op.workcenter_id == workcenter
            )
            if operation:
                return (operation[0].time_cycle * production_order.product_qty) / 60.0
        
        return 1.0  # Tiempo por defecto
    
    # === MÉTODOS DE UTILIDAD ===
    
    def test_algorithm(self, sample_size=10):
        """Probar algoritmo con datos de muestra"""
        # Crear órdenes de producción de muestra
        sample_orders = self.env['mrp.production'].search([
            ('state', 'in', ['confirmed', 'planned'])
        ], limit=sample_size)
        
        if not sample_orders:
            return {
                'success': False,
                'message': 'No hay órdenes de producción disponibles para prueba'
            }
        
        # Ejecutar algoritmo
        result = self.execute_algorithm(sample_orders)
        
        return {
            'success': True,
            'test_result': result,
            'sample_size': len(sample_orders),
            'algorithm': self.name
        }
    
    def compare_with_other_algorithms(self, production_orders):
        """Comparar este algoritmo con otros disponibles"""
        other_algorithms = self.search([
            ('id', '!=', self.id),
            ('active', '=', True)
        ])
        
        comparison_results = []
        
        # Ejecutar este algoritmo
        my_result = self.execute_algorithm(production_orders)
        comparison_results.append({
            'algorithm': self.name,
            'makespan': my_result.get('makespan', 0),
            'execution_time': self.last_execution_time
        })
        
        # Ejecutar otros algoritmos
        for algo in other_algorithms[:3]:  # Limitar a 3 para evitar demora
            try:
                result = algo.execute_algorithm(production_orders)
                comparison_results.append({
                    'algorithm': algo.name,
                    'makespan': result.get('makespan', 0),
                    'execution_time': algo.last_execution_time
                })
            except Exception as e:
                _logger.warning(f"Error ejecutando algoritmo {algo.name}: {str(e)}")
        
        # Ordenar por makespan
        comparison_results.sort(key=lambda x: x['makespan'])
        
        return comparison_results