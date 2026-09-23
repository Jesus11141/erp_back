from django.db import models
from django.utils import timezone

class CustomerModel(models.Model):
    tenant_id = models.IntegerField()
    name = models.CharField(max_length=150, db_column='nombre')
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True, db_column='telefono')
    address = models.TextField(blank=True, db_column='direccion')
    rfc = models.CharField(max_length=20, blank=True, db_column='rfc')
    active = models.BooleanField(default=True, db_column='activo')

    class Meta:
        app_label = 'ventas'
        db_table = 'clientes'

class QuotationModel(models.Model):
    STATUS_CHOICES = [('draft','Draft'),('sent','Sent'),('accepted','Accepted'),('rejected','Rejected'),('expired','Expired')]
    tenant_id = models.IntegerField()
    customer = models.ForeignKey(CustomerModel, on_delete=models.PROTECT, db_column='cliente_id')
    customer_name = models.CharField(max_length=150, db_column='cliente_nombre')
    date = models.DateField(default=timezone.localdate, db_column='fecha')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', db_column='estado')
    notes = models.TextField(blank=True, db_column='notas')
    
    # New professional fields
    validity_days = models.IntegerField(default=15, db_column='dias_validez')
    payment_terms = models.CharField(max_length=255, blank=True, db_column='terminos_pago')
    delivery_time = models.CharField(max_length=100, blank=True, db_column='tiempo_entrega')
    print_style = models.CharField(max_length=50, default='corporativo', db_column='estilo_impresion')
    show_images = models.BooleanField(default=False, db_column='mostrar_imagenes')
    is_preinvoice = models.BooleanField(default=False, db_column='es_pre_factura')
    seller_id = models.IntegerField(null=True, blank=True, db_column='vendedor_id')
    branch_id = models.IntegerField(null=True, blank=True, db_column='sucursal_id')

    class Meta:
        app_label = 'ventas'
        db_table = 'cotizaciones'
        ordering = ['-date']

class QuotationItemModel(models.Model):
    quotation = models.ForeignKey(QuotationModel, on_delete=models.CASCADE, related_name='items', db_column='cotizacion_id')
    product_id = models.IntegerField(default=0, db_column='producto_id')
    description = models.CharField(max_length=200, db_column='descripcion')
    quantity = models.DecimalField(max_digits=10, decimal_places=2, db_column='cantidad')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, db_column='precio_unitario')
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column='descuento')

    class Meta:
        app_label = 'ventas'
        db_table = 'cotizacion_items'

class OrderModel(models.Model):
    STATUS_CHOICES = [('pending','Pending'),('in_progress','In Progress'),('delivered','Delivered'),('canceled','Canceled')]
    tenant_id = models.IntegerField()
    customer = models.ForeignKey(CustomerModel, on_delete=models.PROTECT, db_column='cliente_id')
    customer_name = models.CharField(max_length=150, db_column='cliente_nombre')
    quotation = models.ForeignKey(QuotationModel, on_delete=models.SET_NULL, null=True, blank=True, db_column='cotizacion_id')
    date = models.DateField(default=timezone.localdate, db_column='fecha')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_column='estado')

    class Meta:
        app_label = 'ventas'
        db_table = 'pedidos'
        ordering = ['-date']

class OrderItemModel(models.Model):
    order = models.ForeignKey(OrderModel, on_delete=models.CASCADE, related_name='items', db_column='pedido_id')
    product_id = models.IntegerField(default=0, db_column='producto_id')
    description = models.CharField(max_length=200, db_column='descripcion')
    quantity = models.DecimalField(max_digits=10, decimal_places=2, db_column='cantidad')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, db_column='precio_unitario')
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column='descuento')

    class Meta:
        app_label = 'ventas'
        db_table = 'pedido_items'

class PaymentMethodModel(models.Model):
    tenant_id = models.IntegerField()
    name = models.CharField(max_length=100, db_column='nombre')
    active = models.BooleanField(default=True, db_column='activo')
    requires_reference = models.BooleanField(default=False, db_column='requiere_referencia')

    class Meta:
        app_label = 'ventas'
        db_table = 'metodos_pago'
        ordering = ['name']

class AccountReceivableModel(models.Model):
    STATUS_CHOICES = [('PENDING', 'Pending'), ('PARTIAL', 'Partial'), ('PAID', 'Paid')]
    tenant_id = models.IntegerField()
    customer = models.ForeignKey(CustomerModel, on_delete=models.PROTECT, db_column='cliente_id')
    customer_name = models.CharField(max_length=150, db_column='cliente_nombre')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, db_column='monto_total')
    balance_due = models.DecimalField(max_digits=10, decimal_places=2, db_column='saldo_pendiente')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', db_column='estado')
    reference_type = models.CharField(max_length=50, blank=True, null=True, db_column='tipo_referencia') # e.g., WORK_ORDER, INVOICE
    reference_id = models.IntegerField(blank=True, null=True, db_column='referencia_id')
    created_at = models.DateTimeField(auto_now_add=True, db_column='fecha_creacion')
    updated_at = models.DateTimeField(auto_now=True, db_column='fecha_actualizacion')

    class Meta:
        app_label = 'ventas'
        db_table = 'cuentas_por_cobrar'
        ordering = ['-created_at']

class ReceivablePaymentModel(models.Model):
    account_receivable = models.ForeignKey(AccountReceivableModel, on_delete=models.CASCADE, related_name='payments', db_column='cuenta_cobrar_id')
    amount = models.DecimalField(max_digits=10, decimal_places=2, db_column='monto')
    payment_method = models.CharField(max_length=100, db_column='metodo_pago')
    date = models.DateTimeField(auto_now_add=True, db_column='fecha_pago')
    notes = models.TextField(blank=True, db_column='notas')

    class Meta:
        app_label = 'ventas'
        db_table = 'abonos_cuentas_cobrar'
        ordering = ['-date']
