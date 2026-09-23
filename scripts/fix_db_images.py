import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
from modules.inventario.infrastructure.django_models import ProductModel

for p in ProductModel.objects.exclude(image=''):
    if p.image and p.image.name.startswith('/media/media/'):
        print(f"Fixing {p.name}: {p.image.name}")
        p.image.name = p.image.name.replace('/media/media/productos/', 'productos/')
        p.save()
    elif p.image and p.image.name.startswith('/media/'):
        print(f"Fixing {p.name}: {p.image.name}")
        p.image.name = p.image.name.replace('/media/productos/', 'productos/')
        p.save()

print("Finished fixing image paths in DB")
