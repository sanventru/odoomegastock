# -*- coding: utf-8 -*-

from . import models
from . import wizard
from . import wizards

def post_init_hook(cr, registry):
    """Hook que se ejecuta después de instalar o actualizar el módulo"""
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})

    # Recalcular automáticamente los display_name de todas las bobinas
    bobinas = env['megastock.bobina'].search([])
    if bobinas:
        for bobina in bobinas:
            bobina._compute_display_name()
        print(f"[megastock_orders] Display names recalculados para {len(bobinas)} bobinas")
