from django.db import models

class AccountModel(models.Model):
    TYPES = [
        ('is_active', 'Activo'),
        ('pasivo', 'Pasivo'),
        ('patrimonio', 'Patrimonio'),
        ('ingreso', 'Ingreso'),
        ('egreso', 'Egreso'),
    ]
    tenant_id = models.IntegerField()
    code = models.CharField(max_length=50, db_column='codigo') # ej: '1.1.01.01'
    name = models.CharField(max_length=150, db_column='nombre')
    type = models.CharField(max_length=20, choices=TYPES, db_column='tipo')
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children', db_column='padre_id')

    class Meta:
        app_label = 'contabilidad'
        db_table = 'cuentas_contables'
        unique_together = ('tenant_id', 'code')

class JournalEntryModel(models.Model):
    tenant_id = models.IntegerField()
    date = models.DateField(db_column='fecha')
    description = models.TextField(db_column='descripcion')
    type = models.CharField(max_length=20, default='diario', db_column='tipo') # diario, ingreso, egreso
    reference = models.CharField(max_length=100, blank=True, db_column='referencia') # ej: 'venta_15', 'nomina_2'
    created_at = models.DateTimeField(auto_now_add=True, db_column='creado_en')

    class Meta:
        app_label = 'contabilidad'
        db_table = 'asientos_contables'

class JournalEntryLineModel(models.Model):
    entry = models.ForeignKey(JournalEntryModel, on_delete=models.CASCADE, related_name='lines', db_column='asiento_id')
    account = models.ForeignKey(AccountModel, on_delete=models.PROTECT, db_column='cuenta_id')
    debit = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_column='debit')
    credit = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_column='credit')
    cost_center = models.ForeignKey('CentroCostoModel', on_delete=models.SET_NULL, null=True, blank=True, db_column='centro_costo_id')

    class Meta:
        app_label = 'contabilidad'
        db_table = 'asiento_detalles'

class CentroCostoModel(models.Model):
    tenant_id = models.IntegerField()
    code = models.CharField(max_length=50, db_column='codigo') # ej: '100'
    name = models.CharField(max_length=150, db_column='nombre') # ej: 'Ventas'
    description = models.TextField(blank=True, null=True, db_column='descripcion')
    is_active = models.BooleanField(default=True, db_column='activo')
    created_at = models.DateTimeField(auto_now_add=True, db_column='creado_en')

    class Meta:
        app_label = 'contabilidad'
        db_table = 'centros_costos'
        unique_together = ('tenant_id', 'code')

