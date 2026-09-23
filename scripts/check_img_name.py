import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
from modules.inventario.infrastructure.django_models import ProductModel

for p in ProductModel.objects.all():
    if p.image:
        try:
            print(f"Product: {p.name}, name: {p.image.name}")
        except Exception as e:
            print(f"Product {p.name} failed: {e}")
