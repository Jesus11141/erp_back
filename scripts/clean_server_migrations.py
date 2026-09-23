import os
import sys
import django

# Setup Django environment
sys.path.append('/home/erp/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connection

migrations_configs = [
    {
        'dir': '/home/erp/backend/inventario/migrations',
        'keep': {'__init__.py', '0001_initial.py', '0002_productmodel_image.py'},
        'app': 'inventario'
    },
    {
        'dir': '/home/erp/backend/ventas/migrations',
        'keep': {'__init__.py', '0001_initial.py'},
        'app': 'ventas'
    },
    {
        'dir': '/home/erp/backend/rrhh/migrations',
        'keep': {'__init__.py', '0001_initial.py'},
        'app': 'rrhh'
    }
]

for config in migrations_configs:
    print(f"\n--- Limpiando app: {config['app']} ---")
    m_dir = config['dir']
    if os.path.exists(m_dir):
        for filename in os.listdir(m_dir):
            if filename.endswith('.py') and filename not in config['keep']:
                file_path = os.path.join(m_dir, filename)
                try:
                    os.remove(file_path)
                    print(f"Eliminado archivo viejo: {filename}")
                except Exception as e:
                    print(f"No se pudo eliminar {filename}: {e}")
                    
    print(f"Borrando historial de base de datos para '{config['app']}'...")
    with connection.cursor() as cursor:
        cursor.execute(f"DELETE FROM django_migrations WHERE app = '{config['app']}';")
        print(f"Historial de '{config['app']}' limpio en base de datos.")

print("\n¡Limpieza en el servidor completada con éxito!")
