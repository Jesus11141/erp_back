from django.db import models
from django.utils import timezone


class ProveedorModel(models.Model):
    tenant_id = models.IntegerField(db_index=True)
    identification = models.CharField(max_length=20, db_column='identificacion', db_index=True)
    id_type = models.CharField(max_length=2, default='04', db_column='tipo_identificacion')
    business_name = models.CharField(max_length=200, db_column='razon_social')
    commercial_name = models.CharField(max_length=200, blank=True, default='', db_column='nombre_comercial')
    email = models.EmailField(blank=True, default='')
    phone = models.CharField(max_length=30, blank=True, default='', db_column='telefono')
    address = models.TextField(blank=True, default='', db_column='direccion')
    credit_days = models.IntegerField(default=0, db_column='dias_credito')
    active = models.BooleanField(default=True, db_column='activo')
    
    # Datos Bancarios para Pagos Masivos / Cash Management
    bank_name = models.CharField(max_length=100, blank=True, default='', db_column='banco_nombre')
    bank_account_type = models.CharField(max_length=10, blank=True, default='AHO', db_column='tipo_cuenta_banco') # AHO o CTE
    bank_account_number = models.CharField(max_length=50, blank=True, default='', db_column='numero_cuenta_banco')
    beneficiary_name = models.CharField(max_length=200, blank=True, default='', db_column='titular_cuenta')
    beneficiary_id = models.CharField(max_length=20, blank=True, default='', db_column='identificacion_titular')

    created_at = models.DateTimeField(default=timezone.now, db_column='fecha_creacion')

    class Meta:
        app_label = 'compras'
        db_table = 'compras_proveedores'
        unique_together = ('tenant_id', 'identification')
        ordering = ['business_name']

    def __str__(self):
        return f"{self.identification} - {self.business_name}"


class OrdenCompraModel(models.Model):
    STATUS_CHOICES = [
        ('borrador', 'Borrador'),
        ('solicitada', 'Solicitada'),
        ('aprobada', 'Aprobada'),
        ('recibida', 'Recibida'),
        ('cancelada', 'Cancelada'),
    ]

    tenant_id = models.IntegerField(db_index=True)
    number = models.CharField(max_length=50, db_column='numero')
    supplier = models.ForeignKey(ProveedorModel, on_delete=models.PROTECT, db_column='proveedor_id')
    supplier_name = models.CharField(max_length=200, db_column='proveedor_nombre')
    date = models.DateField(default=timezone.localdate, db_column='fecha')
    expected_delivery_date = models.DateField(null=True, blank=True, db_column='fecha_entrega_esperada')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='borrador', db_column='estado')
    payment_terms = models.CharField(max_length=255, blank=True, default='', db_column='terminos_pago')
    notes = models.TextField(blank=True, default='', db_column='notas')
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_column='subtotal')
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_column='descuento')
    vat = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_column='iva')
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_column='total')
    branch_id = models.IntegerField(null=True, blank=True, db_column='sucursal_id')
    created_at = models.DateTimeField(default=timezone.now, db_column='fecha_creacion')

    class Meta:
        app_label = 'compras'
        db_table = 'compras_ordenes'
        ordering = ['-created_at']


class OrdenCompraItemModel(models.Model):
    purchase_order = models.ForeignKey(OrdenCompraModel, on_delete=models.CASCADE, related_name='items', db_column='orden_id')
    product_id = models.IntegerField(null=True, blank=True, db_column='producto_id')
    description = models.CharField(max_length=255, db_column='descripcion')
    quantity = models.DecimalField(max_digits=12, decimal_places=2, db_column='cantidad')
    unit_price = models.DecimalField(max_digits=12, decimal_places=4, db_column='precio_unitario')
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_column='descuento')
    vat_rate = models.CharField(max_length=5, default='15', db_column='tarifa_iva')
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, db_column='subtotal')

    class Meta:
        app_label = 'compras'
        db_table = 'compras_orden_items'


class FacturaCompraModel(models.Model):
    TYPE_CHOICES = [('inventario', 'Mercadería / Inventario'), ('gasto', 'Gasto Operativo')]
    CONDITION_CHOICES = [('contado', 'Contado'), ('credito', 'Crédito')]
    STATUS_CHOICES = [('registrada', 'Registrada'), ('anulada', 'Anulada')]
    RECEPTION_CHOICES = [('pendiente', 'Pendiente de Recepción'), ('recibida', 'Recibida en Inventario'), ('no_aplica', 'No Aplica')]

    tenant_id = models.IntegerField(db_index=True)
    supplier = models.ForeignKey(ProveedorModel, on_delete=models.PROTECT, db_column='proveedor_id')
    supplier_name = models.CharField(max_length=200, db_column='proveedor_nombre')
    invoice_number = models.CharField(max_length=50, db_column='numero_factura')
    access_key = models.CharField(max_length=49, blank=True, default='', db_column='clave_acceso')
    date = models.DateField(default=timezone.localdate, db_column='fecha_emision')
    registration_date = models.DateField(default=timezone.localdate, db_column='fecha_registro')
    purchase_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='inventario', db_column='tipo_compra')
    payment_condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='contado', db_column='condicion_pago')
    credit_days = models.IntegerField(default=0, db_column='dias_credito')
    due_date = models.DateField(null=True, blank=True, db_column='fecha_vencimiento')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='registrada', db_column='estado')
    reception_status = models.CharField(max_length=20, choices=RECEPTION_CHOICES, default='pendiente', db_column='estado_recepcion')
    subtotal_0 = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_column='subtotal_0')
    subtotal_iva = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_column='subtotal_iva')
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_column='descuento')
    vat = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_column='iva')
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_column='total')
    branch_id = models.IntegerField(null=True, blank=True, db_column='sucursal_id')
    purchase_order_id = models.IntegerField(null=True, blank=True, db_column='orden_compra_id')
    journal_entry_id = models.IntegerField(null=True, blank=True, db_column='asiento_contable_id')
    created_at = models.DateTimeField(default=timezone.now, db_column='fecha_creacion')

    class Meta:
        app_label = 'compras'
        db_table = 'compras_facturas'
        ordering = ['-created_at']


class FacturaCompraItemModel(models.Model):
    invoice = models.ForeignKey(FacturaCompraModel, on_delete=models.CASCADE, related_name='items', db_column='factura_id')
    product_id = models.IntegerField(null=True, blank=True, db_column='producto_id')
    description = models.CharField(max_length=255, db_column='descripcion')
    quantity = models.DecimalField(max_digits=12, decimal_places=2, db_column='cantidad')
    unit_price = models.DecimalField(max_digits=12, decimal_places=4, db_column='precio_unitario')
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_column='descuento')
    vat_rate = models.CharField(max_length=5, default='15', db_column='tarifa_iva')
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, db_column='subtotal')

    class Meta:
        app_label = 'compras'
        db_table = 'compras_factura_items'


class AccountPayableModel(models.Model):
    STATUS_CHOICES = [('PENDING', 'Pendiente'), ('PARTIAL', 'Parcial'), ('PAID', 'Pagada')]

    tenant_id = models.IntegerField(db_index=True)
    supplier = models.ForeignKey(ProveedorModel, on_delete=models.PROTECT, db_column='proveedor_id')
    supplier_name = models.CharField(max_length=200, db_column='proveedor_nombre')
    invoice = models.ForeignKey(FacturaCompraModel, on_delete=models.CASCADE, related_name='account_payable', db_column='factura_id')
    invoice_number = models.CharField(max_length=50, db_column='numero_factura')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, db_column='monto_total')
    balance_due = models.DecimalField(max_digits=12, decimal_places=2, db_column='saldo_pendiente')
    due_date = models.DateField(null=True, blank=True, db_column='fecha_vencimiento')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', db_column='estado')
    created_at = models.DateTimeField(default=timezone.now, db_column='fecha_creacion')

    class Meta:
        app_label = 'compras'
        db_table = 'compras_cuentas_pagar'
        ordering = ['due_date', '-created_at']


class PayablePaymentModel(models.Model):
    METHOD_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia Bancaria'),
        ('cheque', 'Cheque'),
        ('tarjeta', 'Tarjeta'),
        ('otro', 'Otro'),
    ]

    tenant_id = models.IntegerField(db_index=True)
    account_payable = models.ForeignKey(AccountPayableModel, on_delete=models.CASCADE, related_name='payments', db_column='cuenta_pagar_id')
    amount = models.DecimalField(max_digits=12, decimal_places=2, db_column='monto')
    payment_date = models.DateField(default=timezone.localdate, db_column='fecha_pago')
    payment_method = models.CharField(max_length=50, choices=METHOD_CHOICES, default='transferencia', db_column='metodo_pago')
    reference = models.CharField(max_length=100, blank=True, default='', db_column='referencia')
    notes = models.TextField(blank=True, default='', db_column='notas')
    created_at = models.DateTimeField(default=timezone.now, db_column='fecha_creacion')

    class Meta:
        app_label = 'compras'
        db_table = 'compras_abonos_pagar'
        ordering = ['-created_at']
