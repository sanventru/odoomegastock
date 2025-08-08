# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = 'res.company'
    
    # Campos adicionales para MEGASTOCK
    production_manager = fields.Char(
        string='Responsable de Producción',
        default='Gabriela Encarnación'
    )
    
    @api.model
    def _setup_megastock_config(self):
        """Configuración inicial para MEGASTOCK"""
        company = self.env.company
        if company.vat == '1792617443001':
            # Configurar parámetros específicos de MEGASTOCK
            company.write({
                'production_manager': 'Gabriela Encarnación',
            })