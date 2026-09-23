import os, sys, django
sys.path.insert(0, r"C:\Users\Raul\Downloads\erp\backend")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from modules.tax_documents.invoicing.infrastructure.persistence.django_models import CreditNoteModel
for nc in CreditNoteModel.objects.all():
    print(f"ID: {nc.id}, Number: {nc.number}, Status: {nc.status}, SRI: {nc.sri_status}")
