import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connection

sql = """
CREATE TABLE IF NOT EXISTS metodos_pago (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    requiere_referencia BOOLEAN NOT NULL DEFAULT FALSE
);

ALTER TABLE ventas_pos ALTER COLUMN metodo_pago TYPE VARCHAR(100);
"""

with connection.cursor() as cursor:
    cursor.execute(sql)

print("Database updated successfully with raw SQL.")
