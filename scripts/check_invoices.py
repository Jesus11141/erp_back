import sys
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from modules.tax_documents.invoicing.infrastructure.persistence.django_models import InvoiceModel, InvoiceSequentialModel

print("--- ÚLTIMAS FACTURAS ---")
for f in InvoiceModel.objects.all().order_by('-id')[:20]:
    print(f"ID: {f.id} | Numero: {f.number} | Cliente: {f.client} | Estado: {f.status} | Fecha: {f.date}")

print("\n--- SECUENCIALES ---")
for s in InvoiceSequentialModel.objects.all():
    print(f"Estab: {s.estab} | Pto: {s.pto_emi} | Ultimo: {s.ultimo}")
