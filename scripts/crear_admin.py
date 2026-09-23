from django.contrib.auth import get_user_model
U = get_user_model()
if not U.objects.filter(username='admin').exists():
    U.objects.create_superuser('admin', 'admin@erp.com', 'admin123')
    print('Superusuario creado')
else:
    print('Ya existe')
