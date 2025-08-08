# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class StockQuant(models.Model):
    _inherit = 'stock.quant'
    
    # Campos adicionales para MEGASTOCK
    supplier_id = fields.Many2one(
        'res.partner',
        string='Proveedor',
        compute='_compute_supplier_info',
        store=True,
        help='Proveedor del lote'
    )
    
    purchase_date = fields.Date(
        string='Fecha de Compra',
        compute='_compute_supplier_info',
        store=True,
        help='Fecha de compra del lote'
    )
    
    expiry_alert = fields.Boolean(
        string='Alerta de Expiración',
        compute='_compute_expiry_alert',
        help='Producto próximo a expirar'
    )
    
    days_to_expiry = fields.Integer(
        string='Días para Expirar',
        compute='_compute_expiry_alert',
        help='Días restantes hasta la expiración'
    )
    
    lot_origin = fields.Char(
        string='Origen del Lote',
        related='lot_id.name',
        help='Información sobre el origen del lote'
    )
    
    quality_status = fields.Selection([
        ('pending', 'Pendiente Inspección'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado'),
        ('quarantine', 'En Cuarentena'),
    ], string='Estado de Calidad', default='pending')
    
    @api.depends('lot_id.purchase_order_ids')
    def _compute_supplier_info(self):
        """Computar información del proveedor desde el lote"""
        for quant in self:
            if quant.lot_id and hasattr(quant.lot_id, 'purchase_order_ids') and quant.lot_id.purchase_order_ids:
                # Tomar la orden de compra más reciente
                po = quant.lot_id.purchase_order_ids.sorted('date_order', reverse=True)[0]
                quant.supplier_id = po.partner_id.id
                quant.purchase_date = po.date_order
            else:
                quant.supplier_id = False
                quant.purchase_date = False
    
    @api.depends('lot_id.expiration_date')
    def _compute_expiry_alert(self):
        """Computar alertas de expiración"""
        for quant in self:
            if quant.lot_id and hasattr(quant.lot_id, 'expiration_date') and quant.lot_id.expiration_date:
                today = fields.Date.today()
                expiry_date = quant.lot_id.expiration_date
                
                if expiry_date:
                    days_diff = (expiry_date - today).days
                    quant.days_to_expiry = days_diff
                    
                    # Alerta si quedan menos de 60 días (configurable)
                    alert_days = int(self.env['ir.config_parameter'].sudo().get_param(
                        'megastock.expiry_alert_days', '60'
                    ))
                    quant.expiry_alert = days_diff <= alert_days
                else:
                    quant.days_to_expiry = 0
                    quant.expiry_alert = False
            else:
                quant.days_to_expiry = 0
                quant.expiry_alert = False
    
    def action_quality_approve(self):
        """Aprobar calidad del lote"""
        self.write({'quality_status': 'approved'})
        
        # Mover a ubicación aprobada si está en cuarentena
        quarantine_location = self.env.ref('megastock_inventory_clean.stock_location_quarantine', False)
        if quarantine_location and self.location_id == quarantine_location:
            # Determinar ubicación destino según tipo de producto
            dest_location = self._get_approved_location()
            if dest_location:
                self.sudo()._update_reserved_quantity(
                    self.product_id, self.location_id, -self.quantity, lot_id=self.lot_id
                )
                self.sudo()._update_available_quantity(
                    self.product_id, dest_location, self.quantity, lot_id=self.lot_id
                )
    
    def action_quality_reject(self):
        """Rechazar calidad del lote"""
        self.write({'quality_status': 'rejected'})
        
        # Mover a ubicación de desperdicios
        scrap_location = self.env.ref('megastock_inventory_clean.stock_location_scrap', False)
        if scrap_location:
            self.sudo()._update_reserved_quantity(
                self.product_id, self.location_id, -self.quantity, lot_id=self.lot_id
            )
            self.sudo()._update_available_quantity(
                self.product_id, scrap_location, self.quantity, lot_id=self.lot_id
            )
    
    def action_quarantine(self):
        """Poner en cuarentena"""
        self.write({'quality_status': 'quarantine'})
        
        # Mover a ubicación de cuarentena
        quarantine_location = self.env.ref('megastock_inventory_clean.stock_location_quarantine', False)
        if quarantine_location:
            self.sudo()._update_reserved_quantity(
                self.product_id, self.location_id, -self.quantity, lot_id=self.lot_id
            )
            self.sudo()._update_available_quantity(
                self.product_id, quarantine_location, self.quantity, lot_id=self.lot_id
            )
    
    def _get_approved_location(self):
        """Obtener ubicación aprobada según el tipo de producto"""
        if self.product_id.megastock_category == 'materias_primas':
            # Determinar ubicación según material
            if self.product_id.material_type == 'kraft':
                return self.env.ref('megastock_inventory_clean.stock_location_kraft', False)
            elif 'medium' in self.product_id.name.lower():
                return self.env.ref('megastock_inventory_clean.stock_location_medium', False)
            elif 'liner' in self.product_id.name.lower():
                return self.env.ref('megastock_inventory_clean.stock_location_liner', False)
            elif 'tinta' in self.product_id.name.lower():
                return self.env.ref('megastock_inventory_clean.stock_location_inks_cmyk', False)
            elif any(word in self.product_id.name.lower() for word in ['almidon', 'pva', 'adhesiv']):
                return self.env.ref('megastock_inventory_clean.stock_location_adhesives', False)
        
        # Ubicación por defecto
        return self.env.ref('megastock_inventory_clean.stock_location_raw_materials', False)
    
    @api.model
    def _cron_check_expiry_alerts(self):
        """Cron para verificar alertas de expiración"""
        # Buscar productos próximos a expirar
        expiring_quants = self.search([
            ('expiry_alert', '=', True),
            ('quantity', '>', 0)
        ])
        
        if expiring_quants:
            # Enviar notificación
            self._send_expiry_notification(expiring_quants)
    
    def _send_expiry_notification(self, quants):
        """Enviar notificación de productos próximos a expirar"""
        # Obtener email de configuración
        alert_email = self.env['ir.config_parameter'].sudo().get_param(
            'megastock.stock_alert_email', 'gabriela.encarnacion@megastock.ec'
        )
        
        # Preparar lista de productos
        product_list = []
        for quant in quants:
            product_list.append({
                'product': quant.product_id.name,
                'location': quant.location_id.name,
                'quantity': quant.quantity,
                'lot': quant.lot_id.name if quant.lot_id else 'Sin lote',
                'days': quant.days_to_expiry,
                'expiry_date': getattr(quant.lot_id, 'expiration_date', 'N/A') if quant.lot_id else 'N/A'
            })
        
        # Crear mensaje de email
        subject = f'MEGASTOCK - Alerta de Expiración ({len(product_list)} productos)'
        body = self._generate_expiry_email_body(product_list)
        
        # Enviar email (implementar según configuración SMTP)
        mail_values = {
            'subject': subject,
            'body_html': body,
            'email_to': alert_email,
            'email_from': 'sistema@megastock.ec',
        }
        
        mail = self.env['mail.mail'].create(mail_values)
        mail.send()
    
    def _generate_expiry_email_body(self, product_list):
        """Generar cuerpo del email de alerta"""
        html = """
        <h2>Alerta de Expiración - MEGASTOCK</h2>
        <p>Los siguientes productos están próximos a expirar:</p>
        <table border="1" style="border-collapse: collapse; width: 100%;">
            <tr style="background-color: #f0f0f0;">
                <th>Producto</th>
                <th>Ubicación</th>
                <th>Cantidad</th>
                <th>Lote</th>
                <th>Días para Expirar</th>
                <th>Fecha de Expiración</th>
            </tr>
        """
        
        for product in product_list:
            color = 'red' if product['days'] <= 15 else 'orange'
            html += f"""
            <tr style="color: {color};">
                <td>{product['product']}</td>
                <td>{product['location']}</td>
                <td>{product['quantity']}</td>
                <td>{product['lot']}</td>
                <td>{product['days']}</td>
                <td>{product['expiry_date']}</td>
            </tr>
            """
        
        html += """
        </table>
        <p><strong>Acción requerida:</strong> Revisar estos productos y tomar las medidas necesarias.</p>
        <p>Sistema MEGASTOCK</p>
        """
        
        return html