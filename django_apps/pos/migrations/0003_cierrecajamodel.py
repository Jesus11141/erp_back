import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0002_ventaposmodel_tasa_iva'),
    ]

    operations = [
        migrations.CreateModel(
            name='CierreCajaModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('tenant_id', models.IntegerField()),
                ('caja', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT,
                    related_name='cierre', to='pos.cajamodel')),
                ('usuario_id', models.IntegerField()),
                ('fecha_apertura', models.DateTimeField()),
                ('fecha_cierre', models.DateTimeField()),
                ('saldo_inicial', models.DecimalField(max_digits=12, decimal_places=2)),
                ('total_efectivo', models.DecimalField(max_digits=12, decimal_places=2, default=0)),
                ('total_tarjeta', models.DecimalField(max_digits=12, decimal_places=2, default=0)),
                ('total_transferencia', models.DecimalField(max_digits=12, decimal_places=2, default=0)),
                ('num_ventas', models.IntegerField(default=0)),
                ('saldo_esperado', models.DecimalField(max_digits=12, decimal_places=2)),
                ('saldo_contado', models.DecimalField(max_digits=12, decimal_places=2)),
                ('diferencia', models.DecimalField(max_digits=12, decimal_places=2)),
                ('observaciones', models.TextField(blank=True)),
            ],
            options={'db_table': 'cierres_caja', 'app_label': 'pos', 'ordering': ['-fecha_cierre']},
        ),
    ]
