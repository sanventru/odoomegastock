# -*- coding: utf-8 -*-
{
    'name': 'MEGASTOCK Base Configuration',
    'version': '16.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Configuración base para MEGASTOCKEC DISTRIBUIDORA AGRICOLA S.A',
    'description': """
Módulo Base de Configuración para MEGASTOCK

Configuración principal del sistema:

* Configuración de empresa MEGASTOCKEC DISTRIBUIDORA AGRICOLA S.A
* RUC: 1792617443001
* Configuración fiscal Ecuador (IVA 15%)
* Usuarios y permisos por rol
* Categorías de productos específicas
* Configuración de centros de trabajo
    """,
    'author': 'MEGASTOCK',
    'website': 'https://megastock.com',
    'depends': [
        'base',
        'sale',
        'purchase', 
        'stock',
        'mrp',
        'account',
        'l10n_ec',
    ],
    'data': [
        'security/megastock_security.xml',
        'security/ir.model.access.csv',
        'data/company_data.xml',
        'data/product_categories.xml',
        'data/workcenter_data.xml',
        'data/users_data.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}