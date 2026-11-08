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


class BankAccountModel(models.Model):
    """
    Cuentas bancarias de la empresa (sin datos quemados).
    El usuario configura sus cuentas reales y las asocia al Plan de Cuentas.
    """
    ACCOUNT_TYPES = [
        ('corriente', 'Cuenta Corriente'),
        ('ahorros', 'Cuenta de Ahorros')
    ]

    tenant_id = models.IntegerField(db_index=True)
    bank_name = models.CharField(max_length=100, db_column='banco_nombre') # ej: Banco Pichincha, Banco Guayaquil
    bank_code = models.CharField(max_length=20, blank=True, default='', db_column='codigo_banco') # ej: 0010, 0017
    account_number = models.CharField(max_length=50, db_column='numero_cuenta')
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES, default='corriente', db_column='tipo_cuenta')
    currency = models.CharField(max_length=10, default='USD', db_column='moneda')
    account = models.ForeignKey(
        AccountModel,
        on_delete=models.PROTECT,
        related_name='bank_accounts',
        db_column='cuenta_contable_id',
        help_text="Cuenta del Plan de Cuentas asociada (Activo/Bancos)"
    )
    company_code = models.CharField(
        max_length=50,
        blank=True,
        default='',
        db_column='codigo_empresa',
        help_text="Código de empresa / contrato asignado por el banco para Cash Management"
    )
    description = models.CharField(max_length=255, blank=True, default='', db_column='descripcion')
    is_active = models.BooleanField(default=True, db_column='activo')
    created_at = models.DateTimeField(auto_now_add=True, db_column='creado_en')

    class Meta:
        app_label = 'contabilidad'
        db_table = 'cuentas_bancarias'
        ordering = ['bank_name', 'account_number']

    def __str__(self):
        return f"{self.bank_name} - {self.account_number} ({self.get_account_type_display()})"


class BankReconciliationModel(models.Model):
    """
    Cabecera del proceso de Conciliación Bancaria.
    """
    STATUS_CHOICES = [
        ('draft', 'Borrador / En Proceso'),
        ('reconciled', 'Conciliada'),
        ('closed', 'Cerrada / Aprobada')
    ]

    tenant_id = models.IntegerField(db_index=True)
    bank_account = models.ForeignKey(
        BankAccountModel,
        on_delete=models.CASCADE,
        related_name='reconciliations',
        db_column='cuenta_bancaria_id'
    )
    period_start = models.DateField(db_column='periodo_inicio')
    period_end = models.DateField(db_column='periodo_fin')
    statement_balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        db_column='saldo_extracto',
        help_text="Saldo final según el extracto emitido por el banco"
    )
    book_balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        db_column='saldo_libros',
        help_text="Saldo según el Libro Mayor de la cuenta contable"
    )
    reconciled_balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        db_column='saldo_conciliado'
    )
    difference = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        db_column='diferencia'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', db_column='estado')
    notes = models.TextField(blank=True, default='', db_column='notas')
    created_at = models.DateTimeField(auto_now_add=True, db_column='creado_en')

    class Meta:
        app_label = 'contabilidad'
        db_table = 'conciliaciones_bancarias'
        ordering = ['-period_end', '-created_at']


class BankReconciliationItemModel(models.Model):
    """
    Líneas individuales de conciliación (partidas del extracto y partidas de libros).
    """
    SOURCE_CHOICES = [
        ('statement', 'Extracto Bancario'),
        ('book', 'Libro Mayor Contable')
    ]
    MOVEMENT_CHOICES = [
        ('debit', 'Débito / Retiro / Cheque'),
        ('credit', 'Crédito / Depósito')
    ]

    reconciliation = models.ForeignKey(
        BankReconciliationModel,
        on_delete=models.CASCADE,
        related_name='items',
        db_column='conciliacion_id'
    )
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, db_column='origen')
    date = models.DateField(db_column='fecha')
    reference = models.CharField(max_length=100, blank=True, default='', db_column='referencia')
    description = models.CharField(max_length=255, default='', db_column='descripcion')
    amount = models.DecimalField(max_digits=12, decimal_places=2, db_column='monto')
    movement_type = models.CharField(max_length=10, choices=MOVEMENT_CHOICES, db_column='tipo_movimiento')
    journal_entry_line = models.ForeignKey(
        JournalEntryLineModel,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_column='asiento_detalle_id'
    )
    is_matched = models.BooleanField(default=False, db_column='conciliado')
    matched_with_id = models.IntegerField(null=True, blank=True, db_column='coincide_con_id')
    match_method = models.CharField(max_length=30, blank=True, default='', db_column='metodo_coincidencia')

    class Meta:
        app_label = 'contabilidad'
        db_table = 'conciliacion_detalles'
        ordering = ['date', 'id']


class AccountingPeriodModel(models.Model):
    """
    Control y bloqueo de períodos fiscales mensuales por tenant.
    Estados:
      - open: Operación regular.
      - locked: Bloqueo operativo (solo el departamento contable puede realizar ajustes).
      - closed: Cerrado definitivo (candado total de auditoría para SRI).
    """
    STATUS_CHOICES = [
        ('open', 'Abierto'),
        ('locked', 'Bloqueo Operativo'),
        ('closed', 'Cerrado Definitivo')
    ]

    tenant_id = models.IntegerField(db_index=True)
    year = models.IntegerField(db_column='anio', db_index=True)
    month = models.IntegerField(db_column='mes') # 1 a 12
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open', db_column='estado')
    closed_by = models.CharField(max_length=150, blank=True, default='', db_column='cerrado_por')
    closed_at = models.DateTimeField(null=True, blank=True, db_column='cerrado_en')
    reopened_by = models.CharField(max_length=150, blank=True, default='', db_column='reabierto_por')
    reopened_at = models.DateTimeField(null=True, blank=True, db_column='reabierto_en')
    notes = models.TextField(blank=True, default='', db_column='notas')
    created_at = models.DateTimeField(auto_now_add=True, db_column='creado_en')
    updated_at = models.DateTimeField(auto_now=True, db_column='actualizado_en')

    class Meta:
        app_label = 'contabilidad'
        db_table = 'periodos_contables'
        unique_together = ('tenant_id', 'year', 'month')
        ordering = ['year', 'month']

    def __str__(self):
        return f"{self.year}-{self.month:02d} ({self.get_status_display()})"



