import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connection

def run():
    with connection.cursor() as cur:
        # Add max_dispositivos
        try:
            cur.execute('ALTER TABLE tenants ADD COLUMN max_dispositivos integer NOT NULL DEFAULT 1;')
            print("Added max_dispositivos")
        except Exception as e:
            print(f"max_dispositivos error (might already exist): {e}")
            connection.rollback()
            
        # Add estado_suscripcion
        try:
            cur.execute("ALTER TABLE tenants ADD COLUMN estado_suscripcion varchar(20) NOT NULL DEFAULT 'activa';")
            print("Added estado_suscripcion")
        except Exception as e:
            print(f"estado_suscripcion error (might already exist): {e}")
            connection.rollback()
            
        # Create planes
        try:
            cur.execute('''
            CREATE TABLE IF NOT EXISTS planes (
                id serial PRIMARY KEY,
                clave varchar(50) NOT NULL UNIQUE,
                nombre varchar(100) NOT NULL,
                precio numeric(10, 2) NOT NULL,
                max_usuarios integer NOT NULL,
                max_dispositivos integer NOT NULL,
                modulos jsonb NOT NULL,
                creado timestamp with time zone NOT NULL
            );
            ''')
            print("Created planes table")
        except Exception as e:
            print(f"planes table error: {e}")
            connection.rollback()

        # Create tenant_devices
        try:
            cur.execute('''
            CREATE TABLE IF NOT EXISTS tenant_devices (
                id serial PRIMARY KEY,
                tenant_id integer NOT NULL REFERENCES tenants(id) DEFERRABLE INITIALLY DEFERRED,
                dispositivo_uuid varchar(100) NOT NULL,
                nombre_dispositivo varchar(100) NOT NULL,
                ultimo_login timestamp with time zone NOT NULL,
                creado timestamp with time zone NOT NULL,
                CONSTRAINT tenant_devices_tenant_id_dispositivo_uuid_key UNIQUE (tenant_id, dispositivo_uuid)
            );
            ''')
            print("Created tenant_devices table")
        except Exception as e:
            print(f"tenant_devices table error: {e}")
            connection.rollback()

if __name__ == '__main__':
    run()
