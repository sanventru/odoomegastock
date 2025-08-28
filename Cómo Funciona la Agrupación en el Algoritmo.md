Cómo Funciona la Agrupación en el Algoritmo de Planificación

El algoritmo de agrupación funciona en 4 fases principales:

1. Inicialización
python
BOBINAS_DISPONIBLES = [1600, 1400, 1200, 1000, 800]  # mm
grupos_optimizados = []
ordenes_procesadas = set()
grupo_counter = 1
2. Proceso Iterativo de Agrupación
El algoritmo toma cada orden pendiente y busca la mejor combinación posible:

python
for orden in ordenes:
    if orden.id in ordenes_procesadas:
        continue  # Ya fue procesada
    
    # Buscar la mejor combinación para esta orden
    mejor_combinacion = self._encontrar_mejor_combinacion(orden, ...)
3. Evaluación de Combinaciones
Para cada orden principal, el algoritmo evalúa 3 tipos de combinaciones:

A) Individual
Solo la orden actual
Busca la bobina más pequeña que la contenga
Calcula eficiencia: (ancho_orden / bobina) * 100
B) Duplas
Orden actual + otra orden pendiente
Prueba todas las combinaciones posibles
Verifica: ancho_orden1 + ancho_orden2 ≤ bobina
C) Triplas
Orden actual + otras 2 órdenes pendientes
Prueba todas las combinaciones posibles
Verifica: ancho_orden1 + ancho_orden2 + ancho_orden3 ≤ bobina
4. Selección y Asignación
El algoritmo selecciona la combinación con mayor eficiencia y:

python
# Asigna identificador único al grupo
grupo_nombre = f"GRUPO-{grupo_id:03d}"  # Ej: GRUPO-001, GRUPO-002

# Actualiza todas las órdenes del grupo
for orden in combinacion['ordenes']:
    orden.write({
        'grupo_planificacion': grupo_nombre,
        'tipo_combinacion': combinacion['tipo'],  # individual/dupla/tripla
        'bobina_utilizada': combinacion['bobina'],
        'eficiencia': combinacion['eficiencia'],
        # ... otros campos
    })
5. Control de Procesamiento
python
# Marca órdenes como procesadas para evitar duplicados
for orden_comb in mejor_combinacion['ordenes']:
    ordenes_procesadas.add(orden_comb.id)

grupo_counter += 1  # Siguiente grupo
Ejemplo Práctico
Órdenes pendientes:

Orden A: 400mm de ancho
Orden B: 350mm de ancho
Orden C: 800mm de ancho
Proceso de agrupación:

Orden A (400mm):
Individual: 400mm → Bobina 800mm → Eficiencia: 50%
Dupla A+B: 750mm → Bobina 800mm → Eficiencia: 93.75% ✅ MEJOR
Tripla A+B+C: 1550mm → Bobina 1600mm → Eficiencia: 96.87%
Resultado: Se crea GRUPO-001 con Orden A + Orden B (dupla)
Orden C (800mm) (ya no puede combinarse con A y B):
Individual: 800mm → Bobina 800mm → Eficiencia: 100% ✅
Resultado: Se crea GRUPO-002 con Orden C (individual)
Ventajas del Sistema
Optimización automática: Encuentra la mejor combinación sin intervención manual
Minimiza desperdicio: Prioriza combinaciones con mayor eficiencia
Trazabilidad: Cada grupo tiene identificador único
Flexibilidad: Maneja individuales, duplas y triplas según sea óptimo
Escalabilidad: Procesa cualquier cantidad de órdenes pendientes
El resultado final son grupos optimizados donde cada grupo representa órdenes que se procesarán juntas en la misma bobina para maximizar la eficiencia del material.