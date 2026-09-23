from django.db import models
from django.utils import timezone

class ProductModel(models.Model):
    tenant_id = models.IntegerField()
    code = models.CharField(max_length=50, db_column='codigo')
    name = models.CharField(max_length=200, db_column='nombre')
    description = models.TextField(blank=True, db_column='descripcion')
    category = models.CharField(max_length=100, blank=True, null=True, db_column='categoria')
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_column='precio_compra')
    sale_price = models.DecimalField(max_digits=12, decimal_places=2, db_column='precio_venta')
    current_stock = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_column='stock_actual')
    minimum_stock = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_column='stock_minimo')
    unit = models.CharField(max_length=20, default='pza', db_column='unidad')
    vat_rate = models.CharField(max_length=5, default='15', db_column='tarifa_iva')
    active = models.BooleanField(default=True, db_column='activo')
    is_composite = models.BooleanField(default=False, db_column='es_compuesto')
    image = models.ImageField(upload_to='productos/', blank=True, null=True, db_column='imagen')

    class Meta:
        app_label = 'inventario'
        db_table = 'productos'
        unique_together = ('code', 'tenant_id')


class ProductComponentModel(models.Model):
    tenant_id = models.IntegerField()
    product = models.ForeignKey(ProductModel, on_delete=models.CASCADE, related_name='components', db_column='producto_id')
    component = models.ForeignKey(ProductModel, on_delete=models.RESTRICT, related_name='used_in', db_column='componente_id')
    quantity = models.DecimalField(max_digits=12, decimal_places=4, db_column='cantidad')

    class Meta:
        app_label = 'inventario'
        db_table = 'producto_componentes'
        unique_together = ('product', 'component', 'tenant_id')



class StockMovementModel(models.Model):
    TYPE_CHOICES = [('in', 'Entrada'), ('out', 'Salida'), ('adjustment', 'Ajuste')]
    tenant_id = models.IntegerField()
    product = models.ForeignKey(ProductModel, on_delete=models.PROTECT, db_column='producto_id')
    product_name = models.CharField(max_length=200, db_column='producto_nombre')
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, db_column='tipo')
    quantity = models.DecimalField(max_digits=12, decimal_places=2, db_column='cantidad')
    previous_stock = models.DecimalField(max_digits=12, decimal_places=2, db_column='stock_anterior')
    new_stock = models.DecimalField(max_digits=12, decimal_places=2, db_column='stock_nuevo')
    reference = models.CharField(max_length=100, blank=True, db_column='referencia')
    created_at = models.DateTimeField(auto_now_add=True, db_column='fecha')
    user_id = models.IntegerField(default=0, db_column='usuario_id')

    class Meta:
        app_label = 'inventario'
        db_table = 'movimientos_stock'
        ordering = ['-created_at']


class BranchModel(models.Model):
    tenant_id = models.IntegerField()
    name = models.CharField(max_length=150, db_column='nombre')
    address = models.CharField(max_length=250, blank=True, db_column='direccion')
    phone = models.CharField(max_length=20, blank=True, db_column='telefono')
    establishment = models.CharField(max_length=3, db_column='establecimiento')  # SRI establishment: '001', '002'
    active = models.BooleanField(default=True, db_column='activo')

    class Meta:
        app_label = 'inventario'
        db_table = 'sucursales'


class BranchStockModel(models.Model):
    tenant_id = models.IntegerField()
    product = models.ForeignKey(ProductModel, on_delete=models.CASCADE, related_name='branch_stocks', db_column='producto_id')
    branch = models.ForeignKey(BranchModel, on_delete=models.PROTECT, related_name='branch_product_stocks', db_column='sucursal_id')
    current_stock = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_column='stock_actual')

    class Meta:
        app_label = 'inventario'
        db_table = 'stock_sucursales'
        unique_together = ('product', 'branch', 'tenant_id')


class StockTransferModel(models.Model):
    STATUS_CHOICES = [('pending', 'Pendiente'), ('in_transit', 'En TrÃ¡nsito'), ('completed', 'Completada'), ('canceled', 'Cancelada')]
    tenant_id = models.IntegerField()
    product = models.ForeignKey(ProductModel, on_delete=models.PROTECT, db_column='producto_id')
    source_branch = models.ForeignKey(BranchModel, on_delete=models.PROTECT, related_name='transfers_sent', db_column='sucursal_origen_id')
    destination_branch = models.ForeignKey(BranchModel, on_delete=models.PROTECT, related_name='transfers_received', db_column='sucursal_destino_id')
    quantity = models.DecimalField(max_digits=12, decimal_places=2, db_column='cantidad')
    created_at = models.DateTimeField(auto_now_add=True, db_column='fecha')
    user_id = models.IntegerField(db_column='usuario_id')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_column='estado')
    observations = models.TextField(blank=True, db_column='observations')

    class Meta:
        app_label = 'inventario'
        db_table = 'transferencias_stock'


class KardexModel(models.Model):
    tenant_id = models.IntegerField()
    product = models.ForeignKey(ProductModel, on_delete=models.PROTECT, related_name='kardex', db_column='producto_id')
    created_at = models.DateTimeField(default=timezone.now, db_column='fecha')
    detail = models.CharField(max_length=200, db_column='detalle')
    
    # Entries
    entry_quantity = models.DecimalField(max_digits=12, decimal_places=4, default=0, db_column='cant_entrada')
    entry_unit_cost = models.DecimalField(max_digits=12, decimal_places=4, default=0, db_column='costo_unit_entrada')
    entry_total_cost = models.DecimalField(max_digits=12, decimal_places=4, default=0, db_column='costo_total_entrada')
    
    # Exits
    exit_quantity = models.DecimalField(max_digits=12, decimal_places=4, default=0, db_column='cant_salida')
    exit_unit_cost = models.DecimalField(max_digits=12, decimal_places=4, default=0, db_column='costo_unit_salida')
    exit_total_cost = models.DecimalField(max_digits=12, decimal_places=4, default=0, db_column='costo_total_salida')
    
    # Balances
    balance_quantity = models.DecimalField(max_digits=12, decimal_places=4, default=0, db_column='saldo_cantidad')
    balance_unit_cost = models.DecimalField(max_digits=12, decimal_places=4, default=0, db_column='saldo_costo_unitario')
    balance_total_cost = models.DecimalField(max_digits=12, decimal_places=4, default=0, db_column='saldo_costo_total')
    
    user_id = models.IntegerField(default=0, db_column='usuario_id')

    class Meta:
        app_label = 'inventario'
        db_table = 'kardex'
        ordering = ['created_at', 'id']


class VolumeDiscountRuleModel(models.Model):
    tenant_id = models.IntegerField()
    product = models.ForeignKey(ProductModel, on_delete=models.CASCADE, related_name='discount_rules', db_column='producto_id')
    minimum_quantity = models.DecimalField(max_digits=12, decimal_places=2, db_column='cantidad_minima')
    maximum_quantity = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, db_column='cantidad_maxima')
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, db_column='precio_unitario')
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column='porcentaje_descuento')
    active = models.BooleanField(default=True, db_column='activo')

    class Meta:
        app_label = 'inventario'
        db_table = 'reglas_descuento_volumen'
        ordering = ['minimum_quantity']

