import os
import django

# Configurar el entorno de Django para poder usar el ORM y conectarse a PostgreSQL
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from modules.contabilidad.infrastructure.django_models import AccountModel

# Ejecutar las actualizaciones
AccountModel.objects.filter(name='Cash / Bank').update(name='Caja y Bancos')
AccountModel.objects.filter(name='VAT Payable').update(name='IVA por Pagar')
AccountModel.objects.filter(name='Sales Revenue').update(name='Ingresos por Ventas')

print("¡Nombres de cuentas actualizados exitosamente en PostgreSQL!")
