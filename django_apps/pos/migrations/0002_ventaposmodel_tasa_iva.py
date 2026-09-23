from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='ventaposmodel',
            name='tasa_iva',
            field=models.DecimalField(decimal_places=4, default='0.1500', max_digits=5),
        ),
    ]
