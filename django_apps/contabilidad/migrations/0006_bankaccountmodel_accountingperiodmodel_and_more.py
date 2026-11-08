import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contabilidad', '0005_centrocostomodel_journalentrylinemodel_cost_center'),
    ]

    operations = [
        migrations.CreateModel(
            name='BankAccountModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tenant_id', models.IntegerField(db_index=True)),
                ('bank_name', models.CharField(db_column='banco_nombre', max_length=100)),
                ('bank_code', models.CharField(blank=True, db_column='codigo_banco', default='', max_length=20)),
                ('account_number', models.CharField(db_column='numero_cuenta', max_length=50)),
                ('account_type', models.CharField(choices=[('corriente', 'Cuenta Corriente'), ('ahorros', 'Cuenta de Ahorros')], db_column='tipo_cuenta', default='corriente', max_length=20)),
                ('currency', models.CharField(db_column='moneda', default='USD', max_length=10)),
                ('company_code', models.CharField(blank=True, db_column='codigo_empresa', default='', help_text='Código de empresa / contrato asignado por el banco para Cash Management', max_length=50)),
                ('description', models.CharField(blank=True, db_column='descripcion', default='', max_length=255)),
                ('is_active', models.BooleanField(db_column='activo', default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_column='creado_en')),
                ('account', models.ForeignKey(db_column='cuenta_contable_id', help_text='Cuenta del Plan de Cuentas asociada (Activo/Bancos)', on_delete=django.db.models.deletion.PROTECT, related_name='bank_accounts', to='contabilidad.accountmodel')),
            ],
            options={
                'db_table': 'cuentas_bancarias',
                'ordering': ['bank_name', 'account_number'],
            },
        ),
        migrations.CreateModel(
            name='BankReconciliationModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tenant_id', models.IntegerField(db_index=True)),
                ('period_start', models.DateField(db_column='periodo_inicio')),
                ('period_end', models.DateField(db_column='periodo_fin')),
                ('statement_balance', models.DecimalField(db_column='saldo_extracto', decimal_places=2, default=0, help_text='Saldo final según el extracto emitido por el banco', max_digits=14)),
                ('book_balance', models.DecimalField(db_column='saldo_libros', decimal_places=2, default=0, help_text='Saldo según el Libro Mayor de la cuenta contable', max_digits=14)),
                ('reconciled_balance', models.DecimalField(db_column='saldo_conciliado', decimal_places=2, default=0, max_digits=14)),
                ('difference', models.DecimalField(db_column='diferencia', decimal_places=2, default=0, max_digits=14)),
                ('status', models.CharField(choices=[('draft', 'Borrador / En Proceso'), ('reconciled', 'Conciliada'), ('closed', 'Cerrada / Aprobada')], db_column='estado', default='draft', max_length=20)),
                ('notes', models.TextField(blank=True, db_column='notas', default='')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_column='creado_en')),
                ('bank_account', models.ForeignKey(db_column='cuenta_bancaria_id', on_delete=django.db.models.deletion.CASCADE, related_name='reconciliations', to='contabilidad.bankaccountmodel')),
            ],
            options={
                'db_table': 'conciliaciones_bancarias',
                'ordering': ['-period_end', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='BankReconciliationItemModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source', models.CharField(choices=[('statement', 'Extracto Bancario'), ('book', 'Libro Mayor Contable')], db_column='origen', max_length=20)),
                ('date', models.DateField(db_column='fecha')),
                ('reference', models.CharField(blank=True, db_column='referencia', default='', max_length=100)),
                ('description', models.CharField(db_column='descripcion', default='', max_length=255)),
                ('amount', models.DecimalField(db_column='monto', decimal_places=2, max_digits=12)),
                ('movement_type', models.CharField(choices=[('debit', 'Débito / Retiro / Cheque'), ('credit', 'Crédito / Depósito')], db_column='tipo_movimiento', max_length=10)),
                ('is_matched', models.BooleanField(db_column='conciliado', default=False)),
                ('matched_with_id', models.IntegerField(blank=True, db_column='coincide_con_id', null=True)),
                ('match_method', models.CharField(blank=True, db_column='metodo_coincidencia', default='', max_length=30)),
                ('journal_entry_line', models.ForeignKey(blank=True, db_column='asiento_detalle_id', null=True, on_delete=django.db.models.deletion.SET_NULL, to='contabilidad.journalentrylinemodel')),
                ('reconciliation', models.ForeignKey(db_column='conciliacion_id', on_delete=django.db.models.deletion.CASCADE, related_name='items', to='contabilidad.bankreconciliationmodel')),
            ],
            options={
                'db_table': 'conciliacion_detalles',
                'ordering': ['date', 'id'],
            },
        ),
        migrations.CreateModel(
            name='AccountingPeriodModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tenant_id', models.IntegerField(db_index=True)),
                ('year', models.IntegerField(db_column='anio', db_index=True)),
                ('month', models.IntegerField(db_column='mes')),
                ('status', models.CharField(choices=[('open', 'Abierto'), ('locked', 'Bloqueo Operativo'), ('closed', 'Cerrado Definitivo')], db_column='estado', default='open', max_length=20)),
                ('closed_by', models.CharField(blank=True, db_column='cerrado_por', default='', max_length=150)),
                ('closed_at', models.DateTimeField(blank=True, db_column='cerrado_en', null=True)),
                ('reopened_by', models.CharField(blank=True, db_column='reabierto_por', default='', max_length=150)),
                ('reopened_at', models.DateTimeField(blank=True, db_column='reabierto_en', null=True)),
                ('notes', models.TextField(blank=True, db_column='notas', default='')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_column='creado_en')),
                ('updated_at', models.DateTimeField(auto_now=True, db_column='actualizado_en')),
            ],
            options={
                'db_table': 'periodos_contables',
                'ordering': ['year', 'month'],
                'unique_together': {('tenant_id', 'year', 'month')},
            },
        ),
    ]
