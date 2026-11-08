from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('invoicing', '0005_ensure_document_type_in_secuenciales'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE facturas ADD COLUMN IF NOT EXISTS tipo_comprobante varchar(2) DEFAULT '01';
            ALTER TABLE facturas ADD COLUMN IF NOT EXISTS cliente_identificacion varchar(20) DEFAULT '9999999999999';
            ALTER TABLE facturas ADD COLUMN IF NOT EXISTS cliente_tipo_id varchar(2) DEFAULT '05';
            ALTER TABLE facturas ADD COLUMN IF NOT EXISTS cliente_direccion varchar(200) DEFAULT '';
            ALTER TABLE facturas ADD COLUMN IF NOT EXISTS cliente_email varchar(254) DEFAULT '';
            ALTER TABLE facturas ADD COLUMN IF NOT EXISTS forma_pago varchar(2) DEFAULT '01';
            ALTER TABLE facturas ADD COLUMN IF NOT EXISTS notas text DEFAULT '';
            ALTER TABLE facturas ADD COLUMN IF NOT EXISTS clave_acceso varchar(49) DEFAULT '';
            ALTER TABLE facturas ADD COLUMN IF NOT EXISTS numero_autorizacion varchar(49) DEFAULT '';
            ALTER TABLE facturas ADD COLUMN IF NOT EXISTS fecha_autorizacion varchar(30) DEFAULT '';
            ALTER TABLE facturas ADD COLUMN IF NOT EXISTS ambiente varchar(1) DEFAULT '1';
            ALTER TABLE facturas ADD COLUMN IF NOT EXISTS xml_firmado text DEFAULT '';
            ALTER TABLE facturas ADD COLUMN IF NOT EXISTS ride_url varchar(255) DEFAULT '';
            ALTER TABLE facturas ADD COLUMN IF NOT EXISTS sri_estado varchar(20) DEFAULT '';
            ALTER TABLE facturas ADD COLUMN IF NOT EXISTS sri_mensaje text DEFAULT '';
            ALTER TABLE facturas ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT NOW();
            ALTER TABLE factura_items ADD COLUMN IF NOT EXISTS codigo_principal varchar(50) DEFAULT '';
            ALTER TABLE factura_items ADD COLUMN IF NOT EXISTS codigo_auxiliar varchar(50) DEFAULT '';
            ALTER TABLE factura_items ADD COLUMN IF NOT EXISTS descuento numeric(12, 2) DEFAULT 0;
            ALTER TABLE factura_items ADD COLUMN IF NOT EXISTS tarifa_iva varchar(10) DEFAULT '15';
            ALTER TABLE factura_secuenciales ADD COLUMN IF NOT EXISTS document_type varchar(2) DEFAULT '01';
            """,
            reverse_sql=""
        ),
    ]
