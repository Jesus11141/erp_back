from django.db import models

class WorkOrderModel(models.Model):
    STATUS_CHOICES = [
        ('RECEIVED', 'Received'),
        ('IN_REPAIR', 'In Repair'),
        ('READY', 'Ready'),
        ('DELIVERED', 'Delivered')
    ]
    
    tenant_id = models.IntegerField()
    customer_id = models.IntegerField(db_column='cliente_id')
    customer_name = models.CharField(max_length=150, db_column='cliente_nombre')
    device_type = models.CharField(max_length=50, db_column='tipo_dispositivo')
    device_model = models.CharField(max_length=100, db_column='modelo_dispositivo', default='Generic')
    device_identifier = models.CharField(max_length=100, db_column='identificador_dispositivo')
    physical_conditions = models.TextField(blank=True, db_column='condiciones_fisicas')
    reported_fault = models.TextField(db_column='falla_reportada')
    advance_payment = models.DecimalField(max_digits=10, decimal_places=2, default=0, db_column='abono')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='RECEIVED', db_column='estado')
    created_at = models.DateTimeField(auto_now_add=True, db_column='fecha_creacion')
    updated_at = models.DateTimeField(auto_now=True, db_column='fecha_actualizacion')

    class Meta:
        app_label = 'technical_service'
        db_table = 'ordenes_trabajo'
        ordering = ['-created_at']

class WorkOrderItemModel(models.Model):
    work_order = models.ForeignKey(WorkOrderModel, on_delete=models.CASCADE, related_name='items', db_column='orden_id')
    product_id = models.IntegerField(null=True, blank=True, db_column='producto_id')
    description = models.CharField(max_length=200, db_column='descripcion')
    quantity = models.DecimalField(max_digits=10, decimal_places=2, db_column='cantidad')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, db_column='precio_unitario')
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column='descuento')

    class Meta:
        app_label = 'technical_service'
        db_table = 'ordenes_trabajo_items'
