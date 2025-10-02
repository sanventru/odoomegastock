from odoo import http
import json
import logging

_logger = logging.getLogger(__name__)

class ProductAPIController(http.Controller):
    
    @http.route('/test', type='http', auth='none', website=True)
    def test_endpoint(self, **kw):
        _logger.info("¡Se ha llamado al endpoint de prueba!")
        return "¡El endpoint de prueba está funcionando!"
    
    @http.route('/api/update_category', type='json', auth='none', methods=['POST'], csrf=False)
    def update_product_category(self, **kw):
        try:
            # Con type='json', Odoo parsea el body automáticamente
            data = http.request.jsonrequest
            _logger.info(f"Solicitud JSON recibida en /api/update_category: {data}")

            # Validar campos requeridos
            producto = data.get('producto')
            categoria = data.get('categoria')

            if not producto or not categoria:
                return {
                    'status': 'error',
                    'message': 'Faltan campos requeridos (producto, categoria)'
                }

            # Por ahora, solo devolvemos éxito si los datos son correctos
            return {
                'status': 'success',
                'message': 'Solicitud JSON recibida correctamente',
                'data_received': data
            }

        except Exception as e:
            _logger.error(f"Error en el endpoint /api/update_category: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'message': f'Error interno del servidor: {str(e)}'
            }
