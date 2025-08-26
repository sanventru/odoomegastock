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
                # Verificar que la fila tenga datos suficientes
                if len(row) < 10 or not any(row[:10]):  # Si las primeras 10 columnas están vacías
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
        estado_raw = safe_get(13).upper()
        estado = 'pendiente'
        if 'ENTREGADO' in estado_raw:
            estado = 'entregado'
        elif 'PLANCHAS' in estado_raw:
            estado = 'planchas'
        elif 'PROCESO' in estado_raw:
            estado = 'proceso'
        
        return {
            'orden_produccion': safe_get(0),
            'fecha_pedido_cliente': safe_date(safe_get(1)),
            'flauta': safe_get(2),
            'cliente': safe_get(3),
            'pedido': safe_get(4),
            'codigo': safe_get(5),
            'descripcion': safe_get(6),
            'largo': safe_float(safe_get(7)),
            'ancho': safe_float(safe_get(8)),
            'cantidad': safe_int(safe_get(9)),
            'cavidad': safe_int(safe_get(10)),
            'fecha_entrega_cliente': safe_date(safe_get(11)),
            'fecha_produccion': safe_date(safe_get(12)),
            'estado': estado,
            'cumplimiento': safe_get(14),
            
            # Liner Interno (columnas 16-19)
            'liner_interno_proveedor': safe_get(16),
            'liner_interno_ancho': safe_float(safe_get(17)),
            'liner_interno_gm': safe_float(safe_get(18)),
            'liner_interno_tipo': safe_get(19),
            
            # Medium (columnas 20-23)
            'medium_proveedor': safe_get(20),
            'medium_ancho': safe_float(safe_get(21)),
            'medium_gm': safe_float(safe_get(22)),
            'medium_tipo': safe_get(23),
            
            # Liner Externo (columnas 24-27)
            'liner_externo_proveedor': safe_get(24),
            'liner_externo_ancho': safe_float(safe_get(25)),
            'liner_externo_gm': safe_float(safe_get(26)),
            'liner_externo_tipo': safe_get(27),
            
            # Otros campos
            'cortes': safe_int(safe_get(28)),
            'metros_lineales': safe_float(safe_get(29)),
            'cantidad_liner_interno': safe_float(safe_get(30)),
            'cantidad_medium': safe_float(safe_get(31)),
            'cantidad_liner_externo': safe_float(safe_get(32)),
            'numero_troquel': safe_get(33),
            'ect_minimo': safe_float(safe_get(34)),
            'ect_real': safe_float(safe_get(35)),
            'peso': safe_float(safe_get(36)),
            'cantidad_entregada': safe_int(safe_get(37)) if safe_get(37) else safe_int(safe_get(9)),  # Si no hay cantidad entregada, usar cantidad
        }
