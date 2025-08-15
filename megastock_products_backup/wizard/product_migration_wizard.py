# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import csv
import base64
import io
import re


class ProductMigrationWizard(models.TransientModel):
    _name = 'megastock.product.migration.wizard'
    _description = 'Wizard para Migración de Códigos de Productos MEGASTOCK'
    
    migration_type = fields.Selection([
        ('manual', 'Migración Manual'),
        ('csv_import', 'Importar desde CSV'),
        ('auto_detect', 'Detección Automática'),
    ], string='Tipo de Migración', default='manual', required=True)
    
    csv_file = fields.Binary(
        string='Archivo CSV',
        help='Archivo CSV con códigos existentes. Formato: codigo_antiguo,codigo_nuevo,categoria'
    )
    csv_filename = fields.Char(string='Nombre del Archivo')
    
    old_code = fields.Char(
        string='Código Antiguo',
        help='Código existente que se desea migrar'
    )
    new_code = fields.Char(
        string='Código Nuevo MEGASTOCK',
        help='Nuevo código MEGASTOCK (se puede generar automáticamente)'
    )
    
    product_ids = fields.Many2many(
        'product.template',
        string='Productos a Migrar',
        domain=[('megastock_code', '=', False)]
    )
    
    migration_log = fields.Text(
        string='Log de Migración',
        readonly=True
    )
    
    @api.onchange('migration_type')
    def _onchange_migration_type(self):
        """Limpiar campos según el tipo de migración"""
        if self.migration_type != 'csv_import':
            self.csv_file = False
            self.csv_filename = False
        if self.migration_type != 'manual':
            self.old_code = False
            self.new_code = False
    
    def action_migrate_products(self):
        """Ejecutar migración según el tipo seleccionado"""
        if self.migration_type == 'manual':
            return self._migrate_manual()
        elif self.migration_type == 'csv_import':
            return self._migrate_from_csv()
        elif self.migration_type == 'auto_detect':
            return self._migrate_auto_detect()
    
    def _migrate_manual(self):
        """Migración manual de un producto"""
        if not self.old_code:
            raise ValidationError(_('Debe especificar el código antiguo.'))
        
        # Buscar producto por código antiguo
        product = self.env['product.template'].search([
            '|',
            ('default_code', '=', self.old_code),
            ('name', 'ilike', self.old_code)
        ], limit=1)
        
        if not product:
            raise ValidationError(_('No se encontró producto con código "%s".') % self.old_code)
        
        # Generar nuevo código si no se especifica
        if not self.new_code:
            if not product.megastock_category:
                raise ValidationError(_('El producto debe tener una categoría MEGASTOCK asignada.'))
            self.new_code = product._generate_megastock_code(product.megastock_category)
        
        # Aplicar migración
        product.write({
            'megastock_code': self.new_code,
            'default_code': self.new_code
        })
        
        log_msg = f"✓ Migrado: {self.old_code} → {self.new_code} ({product.name})\n"
        self.migration_log = log_msg
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'megastock.product.migration.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def _migrate_from_csv(self):
        """Migración masiva desde archivo CSV"""
        if not self.csv_file:
            raise ValidationError(_('Debe cargar un archivo CSV.'))
        
        try:
            # Decodificar archivo CSV
            csv_data = base64.b64decode(self.csv_file)
            csv_text = csv_data.decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(csv_text))
            
            log_lines = []
            success_count = 0
            error_count = 0
            
            for row in csv_reader:
                try:
                    old_code = row.get('codigo_antiguo', '').strip()
                    new_code = row.get('codigo_nuevo', '').strip()
                    category = row.get('categoria', '').strip()
                    
                    if not old_code:
                        continue
                    
                    # Buscar producto
                    product = self.env['product.template'].search([
                        '|',
                        ('default_code', '=', old_code),
                        ('name', 'ilike', old_code)
                    ], limit=1)
                    
                    if not product:
                        log_lines.append(f"✗ No encontrado: {old_code}")
                        error_count += 1
                        continue
                    
                    # Asignar categoría si se especifica
                    if category and not product.megastock_category:
                        category_mapping = {
                            'cajas': 'cajas',
                            'laminas': 'laminas',
                            'láminas': 'laminas',
                            'papel': 'papel',
                            'planchas': 'planchas',
                            'separadores': 'separadores',
                            'materias_primas': 'materias_primas',
                        }
                        megastock_cat = category_mapping.get(category.lower())
                        if megastock_cat:
                            product.megastock_category = megastock_cat
                    
                    # Generar código nuevo si no se especifica
                    if not new_code and product.megastock_category:
                        new_code = product._generate_megastock_code(product.megastock_category)
                    
                    if new_code:
                        # Aplicar migración
                        product.write({
                            'megastock_code': new_code,
                            'default_code': new_code
                        })
                        log_lines.append(f"✓ Migrado: {old_code} → {new_code} ({product.name})")
                        success_count += 1
                    else:
                        log_lines.append(f"✗ Sin código: {old_code} - No se pudo generar código")
                        error_count += 1
                        
                except Exception as e:
                    log_lines.append(f"✗ Error: {old_code} - {str(e)}")
                    error_count += 1
            
            # Actualizar log
            summary = f"RESUMEN: {success_count} migrados, {error_count} errores\n\n"
            self.migration_log = summary + "\n".join(log_lines)
            
        except Exception as e:
            raise ValidationError(_('Error procesando CSV: %s') % str(e))
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'megastock.product.migration.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def _migrate_auto_detect(self):
        """Migración automática detectando patrones"""
        products = self.env['product.template'].search([
            ('megastock_code', '=', False),
            ('categ_id', 'child_of', [
                self.env.ref('megastock_base.product_category_cajas').id,
                self.env.ref('megastock_base.product_category_laminas').id,
                self.env.ref('megastock_base.product_category_papel_periodico').id,
                self.env.ref('megastock_base.product_category_planchas').id,
                self.env.ref('megastock_base.product_category_separadores').id,
                self.env.ref('megastock_base.product_category_materias_primas').id,
            ])
        ])
        
        log_lines = []
        success_count = 0
        error_count = 0
        
        for product in products:
            try:
                # Detectar categoría MEGASTOCK
                if not product.megastock_category:
                    megastock_cat = product._get_megastock_category_from_categ(product.categ_id.id)
                    if megastock_cat:
                        product.megastock_category = megastock_cat
                
                if product.megastock_category:
                    # Generar código MEGASTOCK
                    new_code = product._generate_megastock_code(product.megastock_category)
                    if new_code:
                        old_code = product.default_code or product.name[:20]
                        product.write({
                            'megastock_code': new_code,
                            'default_code': new_code
                        })
                        log_lines.append(f"✓ Auto-migrado: {old_code} → {new_code} ({product.name})")
                        success_count += 1
                    else:
                        log_lines.append(f"✗ Sin código: {product.name} - No se pudo generar")
                        error_count += 1
                else:
                    log_lines.append(f"✗ Sin categoría: {product.name}")
                    error_count += 1
                    
            except Exception as e:
                log_lines.append(f"✗ Error: {product.name} - {str(e)}")
                error_count += 1
        
        # Actualizar log
        summary = f"DETECCIÓN AUTOMÁTICA\nRESUMEN: {success_count} migrados, {error_count} errores\n\n"
        self.migration_log = summary + "\n".join(log_lines)
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'megastock.product.migration.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def action_download_template(self):
        """Descargar plantilla CSV para migración"""
        template_content = """codigo_antiguo,codigo_nuevo,categoria
30170728,,cajas
30170062,,laminas
PAPEL001,,papel
PLANCHA001,,planchas
SEP001,,separadores
KRAFT125,,materias_primas"""
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'data:text/csv;charset=utf-8;base64,{base64.b64encode(template_content.encode()).decode()}',
            'target': 'self'
        }