#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script para verificar que megastock_products_clean funciona correctamente
"""

import os
import sys

# Agregar el directorio del servidor Odoo al path
sys.path.append('C:\\Program Files\\Odoo 16.0.20250630\\server')

try:
    import odoo
    from odoo import api, registry
    
    # Configurar Odoo
    odoo.tools.config.parse_config(['-d', 'megastock_clean'])
    
    # Obtener registro de la base de datos
    db = registry('megastock_clean')
    
    # Crear un entorno
    with db.cursor() as cr:
        env = api.Environment(cr, 1, {})  # Usuario admin
        
        print("=== TEST MEGASTOCK PRODUCTS CLEAN ===")
        print()
        
        # Verificar que el modelo product.template existe y tiene los campos MEGASTOCK
        product_model = env['product.template']
        
        # Verificar campos MEGASTOCK
        campos_megastock = [
            'megastock_category',
            'largo_cm', 
            'ancho_cm',
            'alto_cm',
            'flauta',
            'material_type'
        ]
        
        print("1. Verificando campos MEGASTOCK en product.template:")
        for campo in campos_megastock:
            if hasattr(product_model, campo):
                print(f"   ✓ Campo '{campo}' existe")
            else:
                print(f"   ✗ Campo '{campo}' NO EXISTE")
        
        print()
        
        # Intentar crear un producto de prueba
        print("2. Creando producto de prueba:")
        try:
            producto_test = product_model.create({
                'name': 'Caja Test MEGASTOCK',
                'detailed_type': 'product',
                'megastock_category': 'cajas',
                'largo_cm': 30.0,
                'ancho_cm': 20.0,
                'alto_cm': 15.0,
                'flauta': 'c',
                'material_type': 'kraft'
            })
            print(f"   ✓ Producto creado exitosamente: ID {producto_test.id}")
            
            # Verificar que se pueden leer los campos
            print("3. Verificando lectura de campos:")
            print(f"   - Categoría MEGASTOCK: {producto_test.megastock_category}")
            print(f"   - Dimensiones: {producto_test.largo_cm} x {producto_test.ancho_cm} x {producto_test.alto_cm} cm")
            print(f"   - Flauta: {producto_test.flauta}")
            print(f"   - Material: {producto_test.material_type}")
            
        except Exception as e:
            print(f"   ✗ Error creando producto: {e}")
        
        print()
        print("=== TEST COMPLETADO ===")
        
except Exception as e:
    print(f"ERROR GENERAL: {e}")
    sys.exit(1)