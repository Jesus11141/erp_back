from django.db import models

class CashRegisterModel(models.Model):
    STATUS_CHOICES = [('open', 'Abierta'), ('closed', 'Cerrada')]
    tenant_id = models.IntegerField()
    name = models.CharField(max_length=100, db_column='nombre')
    user_id = models.IntegerField(db_column='usuario_id')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='closed', db_column='estado')
    initial_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_column='saldo_inicial')
    final_balance = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, db_column='saldo_final')
    opened_at = models.DateTimeField(null=True, blank=True, db_column='fecha_apertura')
    closed_at = models.DateTimeField(null=True, blank=True, db_column='fecha_cierre')
    opening_breakdown = models.JSONField(null=True, blank=True, db_column='opening_breakdown')
    branch_id = models.IntegerField(null=True, blank=True, db_column='sucursal_id')
    emission_point = models.CharField(max_length=3, default='001', db_column='punto_emision')

    class Meta:
        app_label = 'pos'
        db_table = 'cajas'


class CashRegisterClosureModel(models.Model):
    tenant_id = models.IntegerField()
    register = models.OneToOneField(CashRegisterModel, on_delete=models.PROTECT, related_name='closing', db_column='caja_id')
    user_id = models.IntegerField(db_column='usuario_id')
    opened_at = models.DateTimeField(db_column='fecha_apertura')
    closed_at = models.DateTimeField(db_column='fecha_cierre')
    initial_balance = models.DecimalField(max_digits=12, decimal_places=2, db_column='saldo_inicial')
    total_cash = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_column='total_efectivo')
    total_card = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_column='total_tarjeta')
    total_transfer = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_column='total_transferencia')
    total_inflows = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_column='total_ingresos')
    total_outflows = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_column='total_egresos')
    sales_count = models.IntegerField(default=0, db_column='num_ventas')
    expected_balance = models.DecimalField(max_digits=12, decimal_places=2, db_column='saldo_esperado')
    counted_balance = models.DecimalField(max_digits=12, decimal_places=2, db_column='saldo_contado')
    difference = models.DecimalField(max_digits=12, decimal_places=2, db_column='diferencia')
    observations = models.TextField(blank=True, db_column='observaciones')
    closure_breakdown = models.JSONField(null=True, blank=True, db_column='closing_breakdown')

    class Meta:
        app_label = 'pos'
        db_table = 'cierres_caja'
        ordering = ['-closed_at']


class CashRegisterMovementModel(models.Model):
    TYPE_CHOICES = [('inflow', 'Ingreso'), ('outflow', 'Egreso')]
    tenant_id = models.IntegerField()
    register = models.ForeignKey(CashRegisterModel, on_delete=models.PROTECT, related_name='movements', db_column='caja_id')
    user_id = models.IntegerField(db_column='usuario_id')
    movement_type = models.CharField(max_length=10, choices=TYPE_CHOICES, db_column='tipo_movimiento')
    amount = models.DecimalField(max_digits=12, decimal_places=2, db_column='monto')
    reason = models.CharField(max_length=255, db_column='motivo')
    created_at = models.DateTimeField(auto_now_add=True, db_column='fecha')

    class Meta:
        app_label = 'pos'
        db_table = 'movimientos_caja'
        ordering = ['-created_at']


class POSSaleModel(models.Model):
    STATUS_CHOICES = [('pending', 'Pendiente'), ('completed', 'Completada'), ('canceled', 'Cancelada')]
    TIPOS_COMPROBANTE = [('01', 'Factura'), ('02', 'Nota de Venta')]
    tenant_id = models.IntegerField()
    register = models.ForeignKey(CashRegisterModel, on_delete=models.PROTECT, related_name='sales', db_column='caja_id')
    user_id = models.IntegerField(db_column='usuario_id')
    seller_id = models.IntegerField(null=True, blank=True, db_column='vendedor_id')
    document_type = models.CharField(max_length=2, choices=TIPOS_COMPROBANTE, default='01', db_column='tipo_comprobante')
    payment_method = models.CharField(max_length=100, db_column='metodo_pago')
    amount_received = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_column='monto_recibido')
    vat_rate = models.DecimalField(max_digits=5, decimal_places=4, default='0.1200', db_column='tasa_iva')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending', db_column='estado')
    created_at = models.DateTimeField(null=True, blank=True, db_column='fecha')
    customer_name = models.CharField(max_length=200, blank=True, default='', db_column='cliente')
    customer_identifier = models.CharField(max_length=20, blank=True, default='', db_column='cliente_identificacion')
    customer_id_type = models.CharField(max_length=2, blank=True, default='07', db_column='cliente_tipo_id')
    invoice_id = models.IntegerField(null=True, blank=True, db_column='factura_id')
    reference_number = models.CharField(max_length=100, null=True, blank=True, db_column='comprobante')

    class Meta:
        app_label = 'pos'
        db_table = 'ventas_pos'
        ordering = ['-created_at']


class POSSaleItemModel(models.Model):
    sale = models.ForeignKey(POSSaleModel, on_delete=models.CASCADE, related_name='items', db_column='venta_id')
    product_id = models.IntegerField(db_column='producto_id')
    code = models.CharField(max_length=50, db_column='codigo')
    description = models.CharField(max_length=200, db_column='descripcion')
    quantity = models.DecimalField(max_digits=10, decimal_places=2, db_column='cantidad')
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, db_column='precio_unitario')
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column='descuento')

    class Meta:
        app_label = 'pos'
        db_table = 'items_venta_pos'


class PhysicalCashRegisterModel(models.Model):
    tenant_id = models.IntegerField()
    branch_id = models.IntegerField(null=True, blank=True, db_column='sucursal_id')
    code = models.CharField(max_length=50, db_column='codigo')
    name = models.CharField(max_length=100, db_column='nombre')
    primary_cashier_id = models.IntegerField(null=True, blank=True, db_column='cajero_principal_id')
    active = models.BooleanField(default=True, db_column='activa')
    emission_point = models.CharField(max_length=3, default='001', db_column='punto_emision')

    class Meta:
        app_label = 'pos'
        db_table = 'cajas_registradas'
        ordering = ['code', 'name']

