import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
from django.db import connection

with connection.cursor() as cursor:
    cursor.execute('CREATE TABLE IF NOT EXISTS puestos(id SERIAL PRIMARY KEY, tenant_id INTEGER NOT NULL, nombre VARCHAR(150) NOT NULL, activo BOOLEAN NOT NULL)')

from modules.rrhh.infrastructure.django_models import JobPositionModel
from modules.tenants.infrastructure.django_models import TenantModel

for tenant in TenantModel.objects.all():
    if not JobPositionModel.objects.filter(tenant_id=tenant.id, name="Cajero").exists():
        JobPositionModel.objects.create(tenant_id=tenant.id, name="Cajero", active=True)
    if not JobPositionModel.objects.filter(tenant_id=tenant.id, name="Gerente").exists():
        JobPositionModel.objects.create(tenant_id=tenant.id, name="Gerente", active=True)
print("Table created and defaults added!")
