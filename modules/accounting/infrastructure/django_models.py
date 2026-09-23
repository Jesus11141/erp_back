from django.db import models
from django.utils import timezone

class SriInboxModel(models.Model):
    STATUS_CHOICES = [
        ('received', 'Received'),
        ('processed', 'Processed'),
        ('error', 'Error')
    ]
    
    tenant_id = models.IntegerField(db_column='tenant_id', db_index=True)
    supplier_name = models.CharField(max_length=255, db_column='proveedor_nombre')
    supplier_ruc = models.CharField(max_length=13, db_column='proveedor_ruc')
    document_type = models.CharField(max_length=50, null=True, blank=True, db_column='tipo_comprobante')
    document_number = models.CharField(max_length=50, null=True, blank=True, db_column='numero_comprobante')
    access_key = models.CharField(max_length=49, unique=True, db_column='clave_acceso')
    xml_content = models.TextField(db_column='xml_contenido')
    emission_date = models.DateField(db_column='fecha_emision')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, db_column='monto_total')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='received', db_column='estado')
    purchase_invoice = models.ForeignKey('PurchaseInvoiceModel', null=True, blank=True, on_delete=models.SET_NULL, related_name='sri_inbox_docs')
    created_at = models.DateTimeField(default=timezone.now, db_column='fecha_creacion')

    class Meta:
        app_label = 'accounting'
        db_table = 'sri_inbox'

class SriOutboxModel(models.Model):
    STATUS_CHOICES = [
        ('emitted', 'Emitted'),
        ('processed', 'Processed'),
        ('error', 'Error')
    ]
    
    tenant_id = models.IntegerField(db_column='tenant_id', db_index=True)
    customer_name = models.CharField(max_length=255, db_column='cliente_nombre')
    customer_ruc = models.CharField(max_length=13, db_column='cliente_ruc')
    document_type = models.CharField(max_length=50, null=True, blank=True, db_column='tipo_comprobante')
    document_number = models.CharField(max_length=50, null=True, blank=True, db_column='numero_comprobante')
    access_key = models.CharField(max_length=49, unique=True, db_column='clave_acceso')
    xml_content = models.TextField(db_column='xml_contenido')
    emission_date = models.DateField(db_column='fecha_emision')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, db_column='monto_total')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='emitted', db_column='estado')
    created_at = models.DateTimeField(default=timezone.now, db_column='fecha_creacion')

    class Meta:
        app_label = 'accounting'
        db_table = 'sri_outbox'

class SupplierModel(models.Model):
    tenant_id = models.IntegerField(db_index=True)
    ruc = models.CharField(max_length=13, db_index=True)
    business_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        app_label = 'accounting'
        db_table = 'sri_suppliers'
        unique_together = ('tenant_id', 'ruc')

class PurchaseInvoiceModel(models.Model):
    tenant_id = models.IntegerField(db_index=True)
    supplier = models.ForeignKey(SupplierModel, on_delete=models.PROTECT)
    access_key = models.CharField(max_length=49, unique=True)
    document_number = models.CharField(max_length=50)
    emission_date = models.DateField()
    
    # Valores Imponibles
    base_0 = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    base_12 = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    iva_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Contabilidad
    journal_entry_id = models.IntegerField(null=True, blank=True) # ID del Asiento en contabilidad
    
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        app_label = 'accounting'
        db_table = 'sri_purchase_invoices'

class TaxFormModel(models.Model):
    FORM_TYPES = [
        ('103', 'Formulario 103'),
        ('104', 'Formulario 104'),
        ('107', 'Formulario 107')
    ]
    
    tenant_id = models.IntegerField(db_column='tenant_id', db_index=True)
    form_type = models.CharField(max_length=10, choices=FORM_TYPES, db_column='tipo_formulario')
    period_month = models.IntegerField(db_column='mes_periodo', null=True, blank=True)
    period_year = models.IntegerField(db_column='anio_periodo')
    file_url = models.CharField(max_length=255, blank=True, null=True, db_column='archivo_url')
    created_at = models.DateTimeField(default=timezone.now, db_column='fecha_creacion')

    class Meta:
        app_label = 'accounting'
        db_table = 'sri_tax_forms'

class SriCredentialModel(models.Model):
    tenant_id = models.IntegerField(db_column='tenant_id', db_index=True)
    ruc = models.CharField(max_length=13, db_column='ruc')
    company_name = models.CharField(max_length=255, null=True, blank=True, db_column='razon_social')
    tax_status = models.CharField(max_length=50, null=True, blank=True, db_column='estado_tributario')
    tax_regime = models.CharField(max_length=100, null=True, blank=True, db_column='regimen_tributario')
    obligated_accounting = models.CharField(max_length=2, null=True, blank=True, db_column='obligado_contabilidad')
    
    # Nuevos campos del perfil RUC
    taxpayer_type = models.CharField(max_length=100, null=True, blank=True, db_column='tipo_contribuyente')
    tax_category = models.CharField(max_length=100, null=True, blank=True, db_column='categoria_tributaria')
    suspension_reason = models.CharField(max_length=255, null=True, blank=True, db_column='motivo_suspension')
    activity_start_date = models.CharField(max_length=50, null=True, blank=True, db_column='fecha_inicio_actividades')
    
    encrypted_password = models.TextField(db_column='contrasena_encriptada')
    last_sync = models.DateTimeField(null=True, blank=True, db_column='ultima_sincronizacion')
    created_at = models.DateTimeField(default=timezone.now, db_column='fecha_creacion')
    updated_at = models.DateTimeField(auto_now=True, db_column='fecha_actualizacion')

    class Meta:
        app_label = 'accounting'
        db_table = 'sri_credentials'

