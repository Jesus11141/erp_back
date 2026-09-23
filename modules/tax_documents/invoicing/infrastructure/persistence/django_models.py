from django.db import models
from django.utils import timezone


class InvoiceSequentialModel(models.Model):
    """Contador atÃ³mico de secuenciales por tenant+serie. Evita race conditions."""
    tenant_id   = models.IntegerField(max_length=3, default='001', db_column='tenant_id')
    estab       = models.CharField(db_column='estab')
    pto_emi     = models.CharField(max_length=3, default='001', db_column='pto_emi')
    document_type = models.CharField(max_length=2, default='01', db_column='document_type')
    ultimo      = models.PositiveIntegerField(default=0, db_column='ultimo')

    class Meta:
        app_label = 'invoicing'
        db_table = 'factura_secuenciales'
        unique_together = ('tenant_id', 'estab', 'pto_emi', 'document_type')


class InvoiceModel(models.Model):
    ESTADOS = [
        ('draft', 'Draft'),
        ('sent_to_sri', 'Sent SRI'),
        ('authorized', 'Authorized'),
        ('not_authorized', 'Not Authorized'),
        ('canceled', 'Canceled'),
    ]
    TIPOS_ID = [('04', 'RUC'), ('05', 'ID Card'), ('06', 'Passport'), ('07', 'Final Consumer')]
    AMBIENTES = [('1', 'Testing'), ('2', 'Production')]

    TIPOS_COMPROBANTE = [('01', 'Factura'), ('02', 'Nota de Venta')]

    tenant_id         = models.IntegerField(max_length=20, db_column='tenant_id')
    document_type     = models.CharField(max_length=2, choices=TIPOS_COMPROBANTE, default='01', db_column='tipo_comprobante')
    number            = models.CharField(db_column='numero')   # 001-001-000000001
    client            = models.CharField(max_length=150, db_column='cliente')
    client_identification = models.CharField(max_length=20, default='9999999999999', db_column='cliente_identificacion')
    client_id_type    = models.CharField(max_length=2, choices=TIPOS_ID, default='05', db_column='cliente_tipo_id')
    client_address    = models.CharField(max_length=200, blank=True, db_column='cliente_direccion')
    client_email      = models.EmailField(blank=True, db_column='cliente_email')
    date              = models.DateField(default=timezone.localdate, db_column='fecha')
    status            = models.CharField(max_length=20, choices=ESTADOS, default='draft', db_column='estado')
    vat               = models.DecimalField(max_digits=5, decimal_places=2, default=12, db_column='iva')
    payment_method    = models.CharField(max_length=2, default='01', db_column='forma_pago')  # cÃ³digo SRI
    notes             = models.TextField(blank=True, db_column='notas')
    # Campos SRI
    access_key             = models.CharField(max_length=49, blank=True, db_column='clave_acceso')
    authorization_number   = models.CharField(max_length=49, blank=True, db_column='numero_autorizacion')
    authorization_date     = models.CharField(max_length=30, blank=True, db_column='fecha_autorizacion')
    environment            = models.CharField(max_length=1, choices=AMBIENTES, default='1', db_column='ambiente')
    signed_xml             = models.TextField(blank=True, db_column='xml_firmado')
    ride_url               = models.CharField(max_length=255, blank=True, db_column='ride_url')
    sri_status             = models.CharField(max_length=20, blank=True, db_column='sri_estado')
    sri_message            = models.TextField(blank=True, db_column='sri_mensaje')
    created_at             = models.DateTimeField(auto_now_add=True, null=True, db_column='created_at')

    class Meta:
        app_label = 'invoicing'
        db_table = 'facturas'
        ordering = ['-created_at']

class InvoiceItemModel(models.Model):
    invoice           = models.ForeignKey(InvoiceModel, on_delete=models.CASCADE, related_name='items', db_column='factura_id')
    main_code         = models.CharField(max_length=50, blank=True, db_column='codigo_principal')
    auxiliary_code    = models.CharField(max_length=50, blank=True, db_column='codigo_auxiliar')
    description       = models.CharField(max_length=200, db_column='descripcion')
    quantity          = models.DecimalField(max_digits=10, decimal_places=2, db_column='cantidad')
    unit_price        = models.DecimalField(max_digits=10, decimal_places=2, db_column='precio_unitario')
    discount          = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column='descuento')
    vat_rate          = models.CharField(max_length=5, default='15', db_column='tarifa_iva')

    class Meta:
        app_label = 'invoicing'
        db_table = 'factura_items'


class CreditNoteModel(models.Model):
    ESTADOS = [
        ('draft', 'Draft'),
        ('sent_to_sri', 'Sent SRI'),
        ('authorized', 'Authorized'),
        ('not_authorized', 'Not Authorized'),
    ]
    MOTIVOS = [
        ('return', 'Return'),
        ('discount', 'Discount'),
        ('cancellation', 'Cancellation'),
    ]
    TIPOS_ID = [('04', 'RUC'), ('05', 'ID Card'), ('06', 'Passport'), ('07', 'Final Consumer')]
    AMBIENTES = [('1', 'Testing'), ('2', 'Production')]

    tenant_id              = models.IntegerField(max_length=20, db_column='tenant_id')
    number                 = models.CharField(db_column='numero')   # 001-001-000000001
    origin_invoice_number  = models.CharField(max_length=20, db_column='factura_origen_numero')
    origin_invoice_key     = models.CharField(max_length=49, blank=True, db_column='factura_origen_clave')
    client                 = models.CharField(max_length=150, db_column='cliente')
    client_identification  = models.CharField(max_length=20, default='9999999999999', db_column='cliente_identificacion')
    client_id_type         = models.CharField(max_length=2, choices=TIPOS_ID, default='05', db_column='cliente_tipo_id')
    reason                 = models.CharField(max_length=20, choices=MOTIVOS, default='return', db_column='motivo')
    date                   = models.DateField(default=timezone.localdate, db_column='fecha')
    status                 = models.CharField(max_length=20, choices=ESTADOS, default='draft', db_column='estado')
    # Campos SRI
    access_key             = models.CharField(max_length=49, blank=True, db_column='clave_acceso')
    authorization_number   = models.CharField(max_length=49, blank=True, db_column='numero_autorizacion')
    authorization_date     = models.CharField(max_length=30, blank=True, db_column='fecha_autorizacion')
    environment            = models.CharField(max_length=1, choices=AMBIENTES, default='1', db_column='ambiente')
    signed_xml             = models.TextField(blank=True, db_column='xml_firmado')
    sri_status             = models.CharField(max_length=20, blank=True, db_column='sri_estado')
    sri_message            = models.TextField(blank=True, db_column='sri_mensaje')

    class Meta:
        app_label = 'invoicing'
        db_table = 'notas_credito'
        ordering = ['-date']


class CreditNoteItemModel(models.Model):
    credit_note       = models.ForeignKey(CreditNoteModel, on_delete=models.CASCADE, related_name='items', db_column='nota_credito_id')
    main_code         = models.CharField(max_length=50, blank=True, db_column='codigo_principal')
    description       = models.CharField(max_length=200, db_column='descripcion')
    quantity          = models.DecimalField(max_digits=10, decimal_places=2, db_column='cantidad')
    unit_price        = models.DecimalField(max_digits=10, decimal_places=2, db_column='precio_unitario')
    discount          = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column='descuento')
    vat_rate          = models.CharField(max_length=5, default='15', db_column='tarifa_iva')

    class Meta:
        app_label = 'invoicing'
        db_table = 'nota_credito_items'


class WithholdingModel(models.Model):
    ESTADOS = [
        ('draft', 'Borrador'),
        ('sent_to_sri', 'Enviada SRI'),
        ('authorized', 'Autorizada'),
        ('not_authorized', 'No Autorizada'),
    ]
    TIPOS_ID = [('04', 'RUC'), ('05', 'CÃ©dula')]
    AMBIENTES = [('1', 'Pruebas'), ('2', 'ProducciÃ³n')]

    tenant_id                  = models.IntegerField(max_length=20, db_column='tenant_id')
    number                     = models.CharField(db_column='numero')
    supplier                   = models.CharField(max_length=150, db_column='proveedor')
    supplier_identification    = models.CharField(max_length=20, db_column='proveedor_identificacion')
    supplier_id_type           = models.CharField(max_length=2, choices=TIPOS_ID, default='04', db_column='proveedor_tipo_id')
    origin_invoice_number      = models.CharField(max_length=20, blank=True, db_column='factura_origen_numero')
    fiscal_period              = models.CharField(max_length=7, db_column='periodo_fiscal')   # MM/AAAA
    date                       = models.DateField(default=timezone.localdate, db_column='fecha')
    status                     = models.CharField(max_length=20, choices=ESTADOS, default='draft', db_column='estado')
    # Campos SRI
    access_key                 = models.CharField(max_length=49, blank=True, db_column='clave_acceso')
    authorization_number       = models.CharField(max_length=49, blank=True, db_column='numero_autorizacion')
    authorization_date         = models.CharField(max_length=30, blank=True, db_column='fecha_autorizacion')
    environment                = models.CharField(max_length=1, choices=AMBIENTES, default='1', db_column='environment')
    signed_xml                 = models.TextField(blank=True, db_column='signed_xml')
    sri_status                 = models.CharField(max_length=20, blank=True, db_column='sri_estado')
    sri_message                = models.TextField(blank=True, db_column='sri_mensaje')

    class Meta:
        app_label = 'invoicing'
        db_table = 'retenciones'
        ordering = ['-date']


class WithholdingItemModel(models.Model):
    TIPOS_RETENCION = [('1', 'Renta'), ('2', 'IVA'), ('6', 'ISD')]
    withholding       = models.ForeignKey(WithholdingModel, on_delete=models.CASCADE, related_name='items', db_column='retencion_id')
    type_code         = models.CharField(max_length=2, choices=TIPOS_RETENCION, default='1', db_column='codigo_tipo')
    withholding_code  = models.CharField(max_length=10, db_column='codigo_retencion')   # ej. '303', '312'
    tax_base          = models.DecimalField(max_digits=12, decimal_places=2, db_column='base_imponible')
    percentage        = models.DecimalField(max_digits=5, decimal_places=2, db_column='porcentaje')
    withheld_value    = models.DecimalField(max_digits=12, decimal_places=2, db_column='valor_retenido')

    class Meta:
        app_label = 'invoicing'
        db_table = 'retencion_items'



