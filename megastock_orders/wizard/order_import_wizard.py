# -*- coding: utf-8 -*-

import base64
import csv
import io
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class OrderImportWizard(models.TransientModel):
    _name = 'megastock.order.import.wizard'
    _description = 'Wizard para Importar Pedidos desde CSV'

    csv_file = fields.Binary(string='Archivo CSV', required=True, help='Seleccione el archivo CSV con los pedidos')
    csv_filename = fields.Char(string='Nombre del Archivo')
    delimiter = fields.Selection([
        (';', 'Punto y coma (;)'),
        (',', 'Coma (,)'),
        ('\t', 'Tabulación'),
    ], string='Delimitador', default=';', required=True)
    
    # Opciones de importación
    skip_header = fields.Boolean(string='Omitir Encabezados', default=True, help='Omitir las primeras 2 filas (encabezados)')
    update_existing = fields.Boolean(string='Actualizar Existentes', default=True, help='Actualizar pedidos existentes si ya existen')
    
    # Estadísticas de importación
    total_rows = fields.Integer(string='Total de Filas', readonly=True)
    imported_count = fields.Integer(string='Importados', readonly=True)
    updated_count = fields.Integer(string='Actualizados', readonly=True)
    error_count = fields.Integer(string='Errores', readonly=True)
    import_log = fields.Text(string='Log de Importación', readonly=True)

    def action_import_orders(self):
        """Importar pedidos desde el archivo CSV"""
        if not self.csv_file:
            raise UserError(_('Por favor seleccione un archivo CSV.'))
        
        # Decodificar el archivo
        try:
            csv_data = base64.b64decode(self.csv_file)
            csv_content = csv_data.decode('utf-8-sig')  # utf-8-sig para manejar BOM
        except Exception as e:
            raise UserError(_('Error al leer el archivo: %s') % str(e))
        
        # Procesar CSV
        csv_reader = csv.reader(io.StringIO(csv_content), delimiter=self.delimiter)
        rows = list(csv_reader)
        
        if not rows:
            raise UserError(_('El archivo CSV está vacío.'))
        
        # Omitir encabezados si está marcado
        start_row = 2 if self.skip_header else 0
        data_rows = rows[start_row:]
        
        self.total_rows = len(data_rows)
        imported_count = 0
        updated_count = 0
        error_count = 0
        log_messages = []
        
        ProductionOrder = self.env['megastock.production.order']
        
        for row_num, row in enumerate(data_rows, start=start_row + 1):
            try:
                # Verificar que la fila tenga al menos los 14 campos requeridos
                if len(row) < 14 or not any(row[:14]):  # Si las primeras 14 columnas están vacías
                    continue
                
                # Mapear datos del CSV
                order_data = self._map_csv_row_to_order_data(row)
                
                if not order_data.get('cliente'):
                    continue  # Saltar filas sin cliente
                
                # Buscar si ya existe
                existing_order = None
                if order_data.get('orden_produccion'):
                    existing_order = ProductionOrder.search([
                        ('orden_produccion', '=', order_data['orden_produccion'])
                    ], limit=1)
                
                if existing_order and self.update_existing:
                    existing_order.write(order_data)
                    updated_count += 1
                    log_messages.append(f"Fila {row_num}: Actualizado pedido {order_data.get('orden_produccion', 'Sin número')}")
                elif not existing_order:
                    ProductionOrder.create(order_data)
                    imported_count += 1
                    log_messages.append(f"Fila {row_num}: Importado pedido {order_data.get('orden_produccion', 'Sin número')}")
                else:
                    log_messages.append(f"Fila {row_num}: Pedido {order_data.get('orden_produccion')} ya existe (no actualizado)")
                
            except Exception as e:
                error_count += 1
                log_messages.append(f"Fila {row_num}: ERROR - {str(e)}")
        
        # Actualizar estadísticas
        self.write({
            'imported_count': imported_count,
            'updated_count': updated_count,
            'error_count': error_count,
            'import_log': '\n'.join(log_messages)
        })
        
        # Mostrar resultado
        message = f"Importación completada:\n"
        message += f"- Importados: {imported_count}\n"
        message += f"- Actualizados: {updated_count}\n"
        message += f"- Errores: {error_count}"
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Importación Completada'),
                'message': message,
                'type': 'success' if error_count == 0 else 'warning',
                'sticky': True,
            }
        }

    def _map_csv_row_to_order_data(self, row):
        """Mapear una fila del CSV a datos del modelo"""
        def safe_get(index, default=''):
            return row[index].strip() if index < len(row) and row[index] else default
        
        def safe_date(date_str):
            if not date_str:
                return False
            try:
                # Intentar varios formatos de fecha
                for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y']:
                    try:
                        return datetime.strptime(date_str, fmt).date()
                    except ValueError:
                        continue
                return False
            except:
                return False
        
        def safe_float(value_str):
            if not value_str:
                return 0.0
            try:
                # Reemplazar comas por puntos para decimales
                value_str = value_str.replace(',', '.')
                return float(value_str)
            except:
                return 0.0
        
        def safe_int(value_str):
            if not value_str:
                return 0
            try:
                return int(float(value_str))
            except:
                return 0
        
        # Mapear estado
        estado_raw = safe_get(13).upper()  # ESTADO está en posición 13 (0-indexed)
        estado = 'pendiente'
        if 'ENTREGADO' in estado_raw:
            estado = 'entregado'
        elif 'PLANCHAS' in estado_raw:
            estado = 'planchas'
        elif 'PROCESO' in estado_raw:
            estado = 'proceso'
        
        # Campos requeridos según estructura real del CSV
        order_data = {
            'orden_produccion': safe_get(0),                 # ORDEN DE PRODUCCION
            'fecha_pedido_cliente': safe_date(safe_get(1)),  # FECHA PEDIDO CLIENTE
            'flauta': safe_get(2),                           # FLAUTA
            'cliente': safe_get(3),                          # CLIENTE
            'pedido': safe_get(4),                           # PEDIDO
            'codigo': safe_get(5),                           # CODIGO
            'descripcion': safe_get(6),                      # DESCRIPCIÓN
            'largo': safe_float(safe_get(7)),                # LARGO
            'ancho': safe_float(safe_get(8)),                # ANCHO
            'cantidad': safe_int(safe_get(9)),               # CANTIDAD
            'cavidad': safe_int(safe_get(10)),               # CAVIDAD
            'fecha_entrega_cliente': safe_date(safe_get(11)), # FECHA ENTREGA CLIENTE VTAS
            'fecha_produccion': safe_date(safe_get(12)),     # FECHA PRODUCCION
            'estado': estado,                                # ESTADO (posición 13)
            'cantidad_entregada': safe_int(safe_get(9)),     # Por defecto igual a cantidad
        }
        
        # Campos opcionales - solo agregar si existen en el CSV
        if len(row) > 14:
            # CUMPLIMIENTO (si existe)
            if len(row) > 14 and safe_get(14):
                order_data['cumplimiento'] = safe_get(14)
            
            # Liner Interno (si existe)
            if len(row) > 16:
                order_data['liner_interno_proveedor'] = safe_get(16)
            if len(row) > 17:
                order_data['liner_interno_ancho'] = safe_float(safe_get(17))
            if len(row) > 18:
                order_data['liner_interno_gm'] = safe_float(safe_get(18))
            if len(row) > 19:
                order_data['liner_interno_tipo'] = safe_get(19)
            
            # Medium (si existe)
            if len(row) > 20:
                order_data['medium_proveedor'] = safe_get(20)
            if len(row) > 21:
                order_data['medium_ancho'] = safe_float(safe_get(21))
            if len(row) > 22:
                order_data['medium_gm'] = safe_float(safe_get(22))
            if len(row) > 23:
                order_data['medium_tipo'] = safe_get(23)
            
            # Liner Externo (si existe)
            if len(row) > 24:
                order_data['liner_externo_proveedor'] = safe_get(24)
            if len(row) > 25:
                order_data['liner_externo_ancho'] = safe_float(safe_get(25))
            if len(row) > 26:
                order_data['liner_externo_gm'] = safe_float(safe_get(26))
            if len(row) > 27:
                order_data['liner_externo_tipo'] = safe_get(27)
            
            # Otros campos opcionales
            if len(row) > 28:
                order_data['cortes'] = safe_int(safe_get(28))
            if len(row) > 29:
                order_data['metros_lineales'] = safe_float(safe_get(29))
            if len(row) > 30:
                order_data['cantidad_liner_interno'] = safe_float(safe_get(30))
            if len(row) > 31:
                order_data['cantidad_medium'] = safe_float(safe_get(31))
            if len(row) > 32:
                order_data['cantidad_liner_externo'] = safe_float(safe_get(32))
            if len(row) > 33:
                order_data['numero_troquel'] = safe_get(33)
            if len(row) > 34:
                order_data['ect_minimo'] = safe_float(safe_get(34))
            if len(row) > 35:
                order_data['ect_real'] = safe_float(safe_get(35))
            if len(row) > 36:
                order_data['peso'] = safe_float(safe_get(36))
            if len(row) > 37 and safe_get(37):
                order_data['cantidad_entregada'] = safe_int(safe_get(37))
        
        return order_data
