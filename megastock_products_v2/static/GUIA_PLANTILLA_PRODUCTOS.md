# 📋 GUÍA PLANTILLA DE PRODUCTOS MEGASTOCK

## 🎯 **Plantilla Corregida**
**Archivo:** `plantilla_productos_megastock_v2.csv`

### ✅ **Correcciones Aplicadas:**

1. **Todas las columnas tienen cabeceras** completas y descriptivas
2. **26 campos** organizados según la funcionalidad del wizard
3. **13 ejemplos** completos (2-3 por cada categoría MEGASTOCK)
4. **Datos consistentes** sin columnas vacías o mal formateadas
5. **Códigos de barras** únicos para cada ejemplo
6. **Valores apropiados** para cada tipo de producto

## 📊 **Estructura de la Plantilla**

### **Campos Obligatorios (6):**
- `Nombre del Producto` - Nombre descriptivo del producto
- `Código Interno/SKU` - Identificador único (para actualización)
- `Categoría (nombre)` - Categoría Odoo existente
- `Categoría MEGASTOCK` - Categoría específica del sistema
- `Precio de Venta` - Precio al público
- `Costo` - Costo del producto

### **Dimensiones (4):**
- `Largo (cm)` - Longitud en centímetros
- `Ancho (cm)` - Anchura en centímetros  
- `Alto (cm)` - Altura en centímetros
- `Ceja (cm)` - Ceja para cajas

### **Especificaciones Técnicas (7):**
- `Flauta (C/B/E)` - Tipo de flauta del cartón
- `Test (200/250/275/300)` - Valor de resistencia
- `KL (32/44)` - Kilolibras del material
- `Material` - Tipo de material base
- `Colores Impresión (0/1/2/3/4)` - Número de colores
- `Gramaje (90/125/150/175/200)` - Peso del papel g/m²
- `Tipo de Caja` - Estilo de caja específico

### **Campos Adicionales (6):**
- `Unidad de Medida` - UOM para ventas
- `Unidad de Compra` - UOM para compras
- `Descripción` - Descripción detallada
- `Código de Barras` - EAN/UPC del producto
- `Peso (kg)` - Peso unitario
- `Volumen (m³)` - Volumen unitario

### **Control (3):**
- `Activo` - Producto activo/inactivo
- `Se puede vender` - Habilitado para ventas
- `Se puede comprar` - Habilitado para compras

## 🏷️ **Ejemplos por Categoría**

### **CAJAS (3 ejemplos):**
1. **Americana** - Caja estándar flauta C
2. **Tapa y Fondo** - Caja con tapas separadas
3. **Jumbo** - Caja grande para volumen

### **LÁMINAS (2 ejemplos):**
1. **Impresa 2 colores** - Lámina con impresión
2. **Full Color CMYK** - Lámina 4 colores

### **PAPEL PERIÓDICO (2 ejemplos):**
1. **Standard 45g** - Papel básico para relleno
2. **Premium 60g** - Papel mejorado para impresión

### **PLANCHAS (2 ejemplos):**
1. **Kraft estándar** - Plancha para troqueles
2. **Microcanal** - Plancha fina para trabajos delicados

### **SEPARADORES (2 ejemplos):**
1. **Simple** - Separador básico pequeño
2. **Reforzado** - Separador para productos pesados

### **MATERIAS PRIMAS (2 ejemplos):**
1. **Adhesivo PVA** - Para proceso industrial
2. **Almidón modificado** - Para adhesivos eco

## 📝 **Campos por Categoría**

| Campo | CAJAS | LÁMINAS | PAPEL | PLANCHAS | SEPARADORES | MAT.PRIMAS |
|-------|-------|---------|-------|----------|-------------|------------|
| Dimensiones | ✅ Completo | ✅ L×A | ❌ N/A | ✅ L×A | ✅ L×A | ❌ N/A |
| Flauta | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ |
| Test | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| Material | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ |
| KL | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Colores | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Gramaje | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Tipo Caja | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |

## ⚠️ **Notas Importantes:**

### **Valores Permitidos:**
- **Categoría MEGASTOCK:** cajas, laminas, papel, planchas, separadores, materias_primas
- **Flauta:** c, b, e (minúsculas)
- **Test:** 200, 250, 275, 300 (como texto)
- **KL:** 32, 44 (como texto)
- **Material:** kraft, interstock, monus, westrock (minúsculas)
- **Colores:** 0, 1, 2, 3, 4 (como texto)
- **Gramaje:** 90, 125, 150, 175, 200 (como texto)
- **Tipo Caja:** tapa_fondo, jumbo, exportacion, americana
- **Booleanos:** Verdadero/Falso, True/False, Sí/No

### **Campos Vacíos:**
- Usar `0.0` para valores numéricos no aplicables
- Dejar vacío para campos de texto opcionales
- Los campos obligatorios NUNCA deben estar vacíos

### **Códigos de Barras:**
- Todos los ejemplos usan códigos EAN-13 válidos
- Formato: 7501234567XXX
- Cada producto tiene código único

## 🚀 **Uso de la Plantilla:**

1. **Descargar** `plantilla_productos_megastock_v2.csv`
2. **Abrir** con Excel o LibreOffice Calc
3. **Reemplazar** los ejemplos con tus productos reales
4. **Mantener** el formato de las cabeceras exactamente igual
5. **Guardar** como CSV UTF-8
6. **Importar** via wizard en Odoo

## 🔧 **Validación Previa:**
- Verificar que todas las filas tengan datos en campos obligatorios
- Confirmar valores de selección según tabla de valores permitidos
- Asegurar que códigos internos sean únicos
- Validar que precios sean números decimales válidos