import sys
from modules.tax_documents.invoicing.infrastructure.persistence.django_models import InvoiceSequentialModel

# Obtener o crear el secuencial para 001-001
seq, created = InvoiceSequentialModel.objects.get_or_create(
    tenant_id=1,
    estab='001',
    pto_emi='001',
    defaults={'ultimo': 510}
)

if not created:
    seq.ultimo = 510
    seq.save()

print(f"Secuencial actualizado a {seq.ultimo} exitosamente.")
