from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('invoicing', '0004_dispatchguidemodel_purchasesettlementmodel_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE factura_secuenciales ADD COLUMN IF NOT EXISTS document_type varchar(2) DEFAULT '01';
            ALTER TABLE facturas ADD COLUMN IF NOT EXISTS tipo_comprobante varchar(2) DEFAULT '01';
            """,
            reverse_sql=""
        ),
    ]
