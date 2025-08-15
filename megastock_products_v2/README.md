# MEGASTOCK Products v2 - Wizard de Importación

## Descripción
Módulo para la gestión completa de productos MEGASTOCK con funcionalidad de importación masiva desde archivos Excel.

## Características Principales

### 1. Campos Personalizados por Categoría
El módulo maneja 6 categorías principales de productos:

#### CAJAS
- **Dimensiones**: Largo, Ancho, Alto, Ceja (en cm)
- **Especificaciones**: Flauta (C/B/E), Test (200-300), Material, Tipo de caja
- **Extras**: Colores de impresión

#### LÁMINAS  
- **Dimensiones**: Largo, Ancho (en cm)
- **Especificaciones**: Flauta, Test, Material
- **Extras**: Colores de impresión

#### PAPEL PERIÓDICO
- **Especificaciones**: Gramaje (g/m²)
- **Extras**: Colores de impresión

#### PLANCHAS
- **Dimensiones**: Largo, Ancho (en cm)
- **Especificaciones**: Flauta, Test, Material

#### SEPARADORES
- **Dimensiones**: Largo, Ancho (en cm)
- **Especificaciones**: Flauta, Material

#### MATERIAS PRIMAS
- **Especificaciones**: Material, KL (Kilolibras)

### 2. Wizard de Importación Excel

#### Acceso
- **Ubicación**: Ventas → Configuración → Productos → Importar desde Excel
- **Menú**: Sales → Configuration → Products → Import from Excel

#### Funcionalidades
1. **Descarga de Plantilla**: Genera automáticamente un archivo Excel con todos los campos necesarios
2. **Importación Flexible**: Permite crear nuevos productos, actualizar existentes, o ambos
3. **Validación de Datos**: Valida formatos y valores antes de importar
4. **Reporte Detallado**: Muestra resultados del proceso con detalles de éxitos y errores

#### Uso del Wizard

##### Paso 1: Descargar Plantilla
1. Ir a Ventas → Configuración → Productos → Importar desde Excel
2. Hacer clic en "Descargar Plantilla"
3. Se descarga un archivo Excel con:
   - Hoja "Productos": Campos de importación con comentarios explicativos
   - Hoja "Ejemplos": Datos de ejemplo para cada categoría
   - Hoja "Validaciones": Lista de valores permitidos por campo

##### Paso 2: Completar Datos
Complete el archivo Excel con los datos de productos:

**Campos Obligatorios:**
- Nombre del Producto
- Categoría MEGASTOCK (cajas, laminas, papel, planchas, separadores, materias_primas)

**Campos Recomendados:**
- Código Interno/SKU (para identificar productos existentes)
- Precios (Venta y Costo)
- Categoría (nombre de categoría existente en Odoo)

**Campos Específicos por Categoría:**
Ver sección anterior de categorías

##### Paso 3: Configurar Importación
1. **Archivo Excel**: Seleccionar el archivo completado
2. **Modo de Importación**:
   - **Solo Crear**: Solo crea productos nuevos
   - **Solo Actualizar**: Solo actualiza productos existentes 
   - **Crear o Actualizar**: Ambas opciones (recomendado)
3. **Opciones**:
   - **Actualizar Existentes**: Actualiza productos con mismo código interno
   - **Validar Datos**: Valida formatos antes de importar

##### Paso 4: Importar
1. Hacer clic en "Importar Productos"
2. El sistema procesará el archivo y mostrará:
   - Resumen: Total de productos creados, actualizados y errores
   - Detalle: Resultado fila por fila

## Campos del Producto

### Campos Básicos
- `name`: Nombre del producto
- `default_code`: Código interno/SKU
- `categ_id`: Categoría del producto
- `megastock_category`: Categoría MEGASTOCK
- `list_price`: Precio de venta
- `standard_price`: Costo estándar

### Dimensiones
- `largo_cm`: Largo en centímetros (Decimal 8,2)
- `ancho_cm`: Ancho en centímetros (Decimal 8,2)
- `alto_cm`: Alto en centímetros (Decimal 8,2)
- `ceja_cm`: Ceja en centímetros (Decimal 8,2)

### Especificaciones Técnicas
- `flauta`: Tipo de flauta (c, b, e)
- `test_value`: Valor de test (200, 250, 275, 300)
- `kl_value`: Kilolibras (32, 44)
- `material_type`: Tipo de material (kraft, interstock, monus, westrock)

### Impresión y Acabados
- `colors_printing`: Colores de impresión (0-4)
- `gramaje`: Gramaje en g/m² (90, 125, 150, 175, 200)
- `tipo_caja`: Tipo de caja (tapa_fondo, jumbo, exportacion, americana)

### Campos Calculados
- `technical_description`: Descripción técnica generada automáticamente

## Validaciones y Formatos

### Valores de Selección
- **Flauta**: c, b, e (minúsculas)
- **Test**: "200", "250", "275", "300" (como texto)
- **KL**: "32", "44" (como texto)  
- **Material**: kraft, interstock, monus, westrock (minúsculas)
- **Colores**: "0", "1", "2", "3", "4" (como texto)
- **Gramaje**: "90", "125", "150", "175", "200" (como texto)
- **Tipo Caja**: tapa_fondo, jumbo, exportacion, americana (minúsculas con guión bajo)
- **Categoría MEGASTOCK**: cajas, laminas, papel, planchas, separadores, materias_primas

### Valores Booleanos
Acepte cualquiera de estos formatos:
- **Verdadero**: "Verdadero", "True", "Sí", "Si", "1", "Yes"
- **Falso**: "Falso", "False", "No", "0"

### Valores Numéricos
- Decimales con punto como separador
- Se permite texto vacío para valores opcionales

## Archivos de Ejemplo

### Plantilla CSV
Se incluye el archivo `static/plantilla_productos_megastock.csv` con ejemplos de cada categoría:

1. **Caja Corrugada**: Ejemplo completo con dimensiones y especificaciones
2. **Lámina Corrugada**: Con colores de impresión
3. **Papel Periódico**: Con gramaje
4. **Plancha Corrugada**: Material kraft con test
5. **Separador**: Dimensiones básicas
6. **Materia Prima**: Adhesivo industrial

## Instalación

1. Copiar el módulo en la carpeta `addons`
2. Actualizar lista de aplicaciones
3. Instalar "MEGASTOCK Products v2"
4. El wizard estará disponible en el menú de productos

## Dependencias

- `base`: Módulo base de Odoo
- `product`: Gestión de productos
- `stock`: Gestión de inventario  
- `mrp`: Fabricación
- `megastock_base`: Módulo base de MEGASTOCK

## Librerías Python Requeridas

- `xlrd`: Para leer archivos .xls
- `openpyxl`: Para leer archivos .xlsx
- `xlsxwriter`: Para generar plantillas Excel

## Notas Técnicas

### Procesamiento de Excel
- Soporta archivos .xlsx (openpyxl) y .xls (xlrd)
- Lee la primera hoja del archivo
- Los encabezados deben estar en la fila 1
- Los datos empiezan desde la fila 2

### Identificación de Productos Existentes
- Usa el campo `default_code` (Código Interno) para identificar productos existentes
- Si no encuentra el código, crea un nuevo producto
- Si encuentra el código, actualiza el producto existente (según configuración)

### Manejo de Errores
- Registra errores por fila en el log del sistema
- Muestra resumen detallado al usuario
- No detiene el proceso por errores individuales

### Descripción Técnica Automática
- Se genera automáticamente basada en los campos completados
- Se actualiza cuando cambian los campos relacionados
- Es un campo calculado y almacenado