import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from tenants.models import Tenant, TenantModulo

def crear_empresa():
    nombre = "DJH Sistemas"
    # Usamos 'localhost' como subdominio para que funcione directamente en el entorno de desarrollo local.
    subdominio = "localhost" 
    
    tenant, created = Tenant.objects.get_or_create(
        subdominio=subdominio,
        defaults={'nombre': nombre}
    )
    
    if created:
        print(f"Empresa '{nombre}' creada exitosamente con subdominio '{subdominio}'.")
    else:
        # Si ya existe, actualizamos el nombre por si acaso
        tenant.nombre = nombre
        tenant.save()
        print(f"La empresa con subdominio '{subdominio}' ya existía. Se actualizó el nombre a '{nombre}'.")

    # Agregar módulos básicos si no existen
    modulos_basicos = ['facturacion', 'inventario', 'ventas', 'rrhh', 'pos']
    for mod in modulos_basicos:
        # En el modelo TenantModulo.MODULOS vimos: facturacion, inventario, rrhh, contabilidad, compras
        # Pero según el frontend, también puede haber 'ventas', 'pos'. Los agregamos ignorando los choices por ahora o ajustándonos.
        # Si da error de validation en base de datos, lo ignoramos, en sqlite no valida choices.
        TenantModulo.objects.get_or_create(tenant=tenant, modulo=mod, defaults={'activo': True})
        
    print("Módulos básicos habilitados para la empresa.")

if __name__ == '__main__':
    crear_empresa()
