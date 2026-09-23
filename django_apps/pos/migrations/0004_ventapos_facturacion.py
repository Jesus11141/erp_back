from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0003_cierrecajamodel'),
    ]

    operations = [
        migrations.AddField(
            model_name='ventaposmodel',
            name='cliente',
            field=models.CharField(max_length=200, blank=True, default=''),
        ),
        migrations.AddField(
            model_name='ventaposmodel',
            name='cliente_identificacion',
            field=models.CharField(max_length=20, blank=True, default=''),
        ),
        migrations.AddField(
            model_name='ventaposmodel',
            name='cliente_tipo_id',
            field=models.CharField(max_length=2, blank=True, default='07'),
        ),
        migrations.AddField(
            model_name='ventaposmodel',
            name='factura_id',
            field=models.IntegerField(null=True, blank=True),
        ),
    ]
