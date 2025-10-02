from odoo import http
import logging

_logger = logging.getLogger(__name__)

class WorkcenterAPIController(http.Controller):
    
    @http.route('/api/update_energy_consumption', type='json', auth='none', methods=['POST'], csrf=False)
    def update_energy_consumption(self, **kw):
        try:
            # Obtener datos del JSON
            data = http.request.jsonrequest
            _logger.info(f"Solicitud recibida: {data}")
            
            # Validar campos requeridos
            centro = data.get('centro')
            valor = data.get('valor')
            
            if not centro or valor is None:
                return {
                    'status': 'error',
                    'message': 'Faltan campos requeridos (centro, valor)'
                }
            
            # Buscar el centro de trabajo
            workcenter = http.request.env['mrp.workcenter'].sudo().search([
                ('name', '=', centro.upper())
            ], limit=1)
            
            if not workcenter:
                return {
                    'status': 'error',
                    'message': f'No se encontró el centro de trabajo: {centro}'
                }
            
            # Actualizar el valor de consumo energético
            try:
                valor_float = float(valor)
                workcenter.write({
                    'power_consumption_kw': valor_float
                })
                
                _logger.info(f"Actualizado consumo energético de {centro} a {valor_float} kW")
                
                return {
                    'status': 'success',
                    'message': f'Consumo energético actualizado correctamente a {valor_float} kW',
                    'centro': centro,
                    'nuevo_valor': valor_float
                }
                
            except ValueError:
                return {
                    'status': 'error',
                    'message': 'El valor debe ser un número válido'
                }
            
        except Exception as e:
            _logger.error(f"Error en el endpoint /api/update_energy_consumption: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'message': f'Error interno del servidor: {str(e)}'
            }
