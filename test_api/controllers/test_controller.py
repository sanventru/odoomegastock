from odoo import http
import logging

_logger = logging.getLogger(__name__)

class TestController(http.Controller):
    @http.route('/test/hello', type='http', auth='none', website=False, csrf=False)
    def test_hello(self, **kw):
        _logger.info("¡Se ha llamado al endpoint de prueba!")
        return "¡Hola desde el controlador de prueba!"
