import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from tenants.models import Tenant
from auth_module.models import UsuarioModel

def crear_admin_empresa():
    try:
        # Buscamos la empresa que creamos antes
        empresa = Tenant.objects.get(subdominio='localhost')
        
        # Datos del usuario administrador para esta empresa
        email = 'admin@erp.com'
        password = 'admin123'
        
        # Verificamos si ya existe
        usuario, creado = UsuarioModel.objects.get_or_create(
            email=email,
            tenant_id=empresa.id,
            defaults={
                'username': f"{empresa.id}:{email}",
                'nombre': 'Administrador DJH',
                'rol': 'superadmin',
                'activo': True
            }
        )
        
        # Siempre le actualizamos la contraseña para estar seguros
        usuario.set_password(password)
        usuario.save()
        
        if creado:
            print(f"Usuario {email} creado exitosamente para la empresa {empresa.nombre}.")
        else:
            print(f"La contraseña de {email} fue actualizada exitosamente para la empresa {empresa.nombre}.")
            
    except Tenant.DoesNotExist:
        print("Error: No se encontró la empresa. Asegúrate de haber ejecutado crear_empresa.py primero.")

if __name__ == '__main__':
    crear_admin_empresa()
