from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='ParametroModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tenant_id', models.IntegerField()),
                ('modulo', models.CharField(max_length=50)),
                ('clave', models.CharField(max_length=100)),
                ('valor', models.TextField()),
            ],
            options={
                'db_table': 'parametros',
                'unique_together': {('tenant_id', 'modulo', 'clave')},
            },
        ),
    ]
