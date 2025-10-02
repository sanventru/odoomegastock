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

    csv_file = fields.Binary(string='Archivo CSV', required=True, help='Seleccione el archivo CSV con los pedidos', attachment=False)
    csv_filename = fields.Char(string='Nombre del Archivo')
    delimiter = fields.Selection([
        (';', 'Punto y coma (;)'),
        (',', 'Coma (,)'),
        ('\t', 'Tabulación'),
    ], string='Delimitador', default=';', required=True)
    
    # Opciones de importación
    skip_header = fields.Boolean(string='Omitir Encabezados', default=True, help='Omitir la primera fila (encabezados)')
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
        start_row = 1 if self.skip_header else 0
        data_rows = rows[start_row:]
        
        self.total_rows = len(data_rows)
        imported_count = 0
        updated_count = 0
        error_count = 0
        log_messages = []
        
        ProductionOrder = self.env['megastock.production.order']
        
        for row_num, row in enumerate(data_rows, start=start_row + 1):
            try:
                # Verificar que la fila tenga al menos los campos mínimos requeridos
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

        # Si no hay errores, cerrar wizard y ir a lista de pedidos
        if error_count == 0 and (imported_count > 0 or updated_count > 0):
            # Mostrar notificación de éxito
            self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                'title': _('Importación Completada'),
                'message': message,
                'type': 'success',
                'sticky': False,
            })

            # Redirigir a lista de pedidos actualizada
            return {
                'type': 'ir.actions.act_window',
                'name': _('Lista de Pedidos'),
                'res_model': 'megastock.production.order',
                'view_mode': 'tree,form',
                'view_id': False,
                'target': 'current',
                'context': {'search_default_recent': 1}  # Mostrar pedidos recientes
            }
        else:
            # Si hay errores, mantener wizard abierto para revisar log
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Importación Completada con Errores'),
                    'message': message + '\n\nRevisa el log de importación para más detalles.',
                    'type': 'warning',
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
        
        # Mapear tipo producto
        def map_tipo_producto(tipo_csv):
            tipo_map = {
                'CAJAS': 'cajas',
                'LAMINAS': 'laminas',
                'PLANCHAS': 'planchas'
            }
            return tipo_map.get(tipo_csv.upper(), 'cajas') if tipo_csv else 'cajas'

        # Mapear sustrato
        def map_sustrato(sustrato_csv):
            sustrato_map = {
                'K/K': 'kk',
                'K/M': 'km',
                'M/K': 'mk',
                'M/M': 'mm'
            }
            return sustrato_map.get(sustrato_csv.upper(), 'kk') if sustrato_csv else 'kk'

        # Mapear troquel
        def map_troquel(troquel_csv):
            troquel_map = {
                'SI': 'si',
                'SÍ': 'si',
                'YES': 'si',
                'S': 'si',
                'NO': 'no',
                'N': 'no'
            }
            return troquel_map.get(troquel_csv.upper(), 'no') if troquel_csv else 'no'

        # Campos según estructura CSV actualizada (18 columnas)
        # 0=ORDEN, 1=PEDIDO, 2=CODIGO, 3=CLIENTE, 4=DESCRIPCIÓN, 5=FECHA_PEDIDO_CLIENTE,
        # 6=LARGO, 7=ANCHO, 8=ALTO, 9=CANTIDAD, 10=FECHA_ENTREGA_CLIENTE, 11=FECHA_PRODUCCION,
        # 12=CUMPLIMIENTO, 13=TIPO, 14=FLAUTA, 15=TEST, 16=SUSTRATO, 17=TROQUEL
        # LARGO_RAYADO = alto + 2, ALTO_RAYADO = alto + 2, ANCHO_RAYADO = ancho_calculado - (alto_rayado * 2)
        order_data = {
            'orden_produccion': safe_get(0),                 # ORDEN DE PRODUCCION
            'pedido': safe_get(1),                           # PEDIDO
            'codigo': safe_get(2),                           # CODIGO
            'cliente': safe_get(3),                          # CLIENTE
            'descripcion': safe_get(4),                      # DESCRIPCIÓN
            'fecha_pedido_cliente': safe_date(safe_get(5)),  # FECHA PEDIDO CLIENTE
            'largo': safe_float(safe_get(6)),                # LARGO
            'ancho': safe_float(safe_get(7)),                # ANCHO
            'alto': safe_float(safe_get(8)),                 # ALTO
            'cantidad': safe_int(safe_get(9)),               # CANTIDAD
            'fecha_entrega_cliente': safe_date(safe_get(10)), # FECHA ENTREGA CLIENTE VTAS
            'fecha_produccion': safe_date(safe_get(11)),     # FECHA PRODUCCION
            'cumplimiento': safe_get(12),                    # CUMPLIMIENTO
            'tipo_producto': map_tipo_producto(safe_get(13)), # TIPO
            'flauta': safe_get(14),                          # FLAUTA
            'sustrato': map_sustrato(safe_get(16)),          # SUSTRATO
            'troquel': map_troquel(safe_get(17)),            # TROQUEL
            # largo_rayado es calculado: alto + 2
            # alto_rayado es calculado: alto + 2
            # ancho_rayado es calculado: ancho_calculado - (alto_rayado * 2)
            'estado': 'pendiente',                           # Estado por defecto
            'cantidad_entregada': 0,                         # Inicialmente 0
        }
        
        return order_data
