from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ventas', '0008_quotationmodel_branch_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentmethodmodel',
            name='sri_code',
            field=models.CharField(blank=True, db_column='codigo_sri', default='01', max_length=2, null=True),
        ),
    ]
