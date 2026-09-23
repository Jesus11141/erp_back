import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
from modules.inventario.infrastructure.django_models import ProductModel

for p in ProductModel.objects.exclude(image=''):
    if p.image and 'productos/' in p.image.name:
        name = p.image.name
        new_name = 'productos/' + name.split('productos/')[-1]
        if name != new_name:
            print(f"Fixing {p.name}: {name} -> {new_name}")
            p.image.name = new_name
            p.save()
print("Finished fixing image paths in DB")
