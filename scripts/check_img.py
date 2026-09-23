import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
from modules.inventario.infrastructure.django_models import ProductModel

p = ProductModel.objects.exclude(image='').first()
if p:
    print(f"Product: {p.name}, p.image: {p.image}, p.image.url: {p.image.url}")
else:
    print("No products with images")
