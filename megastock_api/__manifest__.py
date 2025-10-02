{
    'name': 'MEGASTOCK API',
    'version': '16.0.1.0.0',
    'category': 'API',
    'summary': 'API para integraciones externas de MEGASTOCK',
    'description': """
Módulo de API para integraciones externas

Endpoints disponibles:
- /test (GET): Endpoint de prueba
- /api/update_category (POST): Actualiza la categoría de un producto
""",
    'author': 'MEGASTOCK',
    'website': 'https://megastock.com',
    'depends': ['base', 'mrp'],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
