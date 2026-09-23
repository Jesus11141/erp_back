import os
import sys
import django

sys.path.append('c:/Users/Raul/Downloads/erp/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp_django.settings')
django.setup()

from modules.parametros.infrastructure.models import ParameterModel

for p in ParameterModel.objects.all():
    print(f"Tenant: {p.tenant_id}, Modulo: {p.modulo}, Clave: {p.clave}, Valor: {p.valor}")
