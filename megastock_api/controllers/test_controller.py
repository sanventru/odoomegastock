from odoo import http
import logging

_logger = logging.getLogger(__name__)

class TestController(http.Controller):
    
    @http.route('/test_route', type='http', auth='none', website=True)
    def test_route(self, **kw):
        _logger.info("¡Se ha llamado al endpoint de prueba!")
        return "¡El endpoint de prueba está funcionando!"
    
    @http.route(['/update_consumo/<string:nombre>/<float:valor>',
                '/update_consumo/<string:nombre>/<int:valor>'],
               type='http', auth='none', methods=['GET'], csrf=False)
    def update_consumo(self, nombre, valor, **kw):
        try:
            _logger.info(f"Actualizando consumo para {nombre} a {valor} kW")
            
            # Buscar el centro de trabajo
            workcenter = http.request.env['mrp.workcenter'].sudo().search([
                ('name', '=', nombre.upper())
            ], limit=1)
            
            if not workcenter:
                return http.request.make_json_response({
                    'status': 'error',
                    'message': f'No se encontró el centro de trabajo: {nombre}'
                }, status=404)
            
            # Actualizar el valor
            workcenter.write({
                'power_consumption_kw': float(valor)
            })
            
            return http.request.make_json_response({
                'status': 'success',
                'message': f'Consumo actualizado correctamente a {valor} kW',
                'centro': nombre,
                'nuevo_valor': valor
            })
            
        except Exception as e:
            _logger.error(f"Error: {str(e)}", exc_info=True)
            return http.request.make_json_response({
                'status': 'error',
                'message': str(e)
            }, status=500)
            
    @http.route(['/get_parametro/<string:nombre>/<string:parametro>'],
               type='http', auth='none', methods=['GET'], csrf=False)
    def get_parametro(self, nombre, parametro, **kw):
        try:
            _logger.info(f"Obteniendo parámetro {parametro} para {nombre}")
            
            # Mapeo de nombres de parámetros a campos de la base de datos
            parametros_disponibles = {
                'Consumo Energético (kW)': 'power_consumption_kw',
                'Consumo Aire Comprimido (m³/h)': 'compressed_air_consumption',
                'Consumo Aceite Hidráulico (L/mes)': 'hydraulic_oil_consumption',
                'Consumo Lubricantes (kg/mes)': 'lubricant_consumption',
                'Ancho Máximo (mm)': 'max_width_mm',
                'Longitud Máxima (mm)': 'max_length_mm',
                'Espesor Máximo (mm)': 'max_thickness_mm',
                'Capacidad Teórica/Hora': 'theoretical_capacity',
                'Capacidad Real/Hora': 'real_capacity'
            }
            
            # Buscar el campo correspondiente al parámetro
            campo = parametros_disponibles.get(parametro)
            if not campo:
                return http.request.make_json_response({
                    'status': 'error',
                    'message': f'Parámetro no válido: {parametro}'
                }, status=400)
            
            # Buscar el centro de trabajo
            workcenter = http.request.env['mrp.workcenter'].sudo().search([
                ('name', '=', nombre.upper())
            ], limit=1)
            
            if not workcenter:
                return http.request.make_json_response({
                    'status': 'error',
                    'message': f'No se encontró el centro de trabajo: {nombre}'
                }, status=404)
            
            # Obtener el valor del campo
            valor = workcenter[campo]
            
            return http.request.make_json_response({
                'maquina': workcenter.name,
                'parametro': parametro,
                'valor': valor
            })
            
        except Exception as e:
            _logger.error(f"Error: {str(e)}", exc_info=True)
            return http.request.make_json_response({
                'status': 'error',
                'message': str(e)
            }, status=500)
