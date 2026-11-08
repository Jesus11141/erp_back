from django.db import models
from modules.tenants.infrastructure.django_models import TenantModel
import uuid

class ZonaModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(TenantModel, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100)
    
    class Meta:
        db_table = 'restaurantes_zona'
        app_label = 'restaurantes'
        
class MesaModel(models.Model):
    ESTADOS = [
        ('libre', 'Libre'),
        ('ocupada', 'Ocupada'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(TenantModel, on_delete=models.CASCADE)
    zona = models.ForeignKey(ZonaModel, on_delete=models.CASCADE, related_name='mesas')
    nombre = models.CharField(max_length=50)
    asientos = models.IntegerField(default=4)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='libre')
    
    class Meta:
        db_table = 'restaurantes_mesa'
        app_label = 'restaurantes'
        
class PedidoRestauranteModel(models.Model):
    ESTADOS = [
        ('abierto', 'Abierto'),
        ('cerrado', 'Cerrado'),
        ('cancelado', 'Cancelado'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(TenantModel, on_delete=models.CASCADE)
    mesa = models.ForeignKey(MesaModel, on_delete=models.CASCADE, related_name='pedidos_activos')
    estado = models.CharField(max_length=20, choices=ESTADOS, default='abierto')
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    factura_id = models.IntegerField(null=True, blank=True)
    factura_numero = models.CharField(max_length=50, null=True, blank=True)
    clave_acceso = models.CharField(max_length=49, null=True, blank=True)
    cliente_nombre = models.CharField(max_length=200, null=True, blank=True)
    cliente_identificacion = models.CharField(max_length=20, null=True, blank=True)
    metodo_pago = models.CharField(max_length=10, default='01')
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'restaurantes_pedido'
        app_label = 'restaurantes'
        
class LineaPedidoRestauranteModel(models.Model):
    ESTADOS_COCINA = [
        ('pendiente', 'Pendiente'),
        ('preparando', 'Preparando'),
        ('listo', 'Listo'),
        ('entregado', 'Entregado'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pedido = models.ForeignKey(PedidoRestauranteModel, on_delete=models.CASCADE, related_name='lineas')
    # Use generic CharField for item name/id or link to an inventory item. For now, name and price.
    item_id = models.CharField(max_length=100)
    item_nombre = models.CharField(max_length=200)
    cantidad = models.IntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    notas = models.TextField(blank=True, null=True)
    estado_cocina = models.CharField(max_length=20, choices=ESTADOS_COCINA, default='pendiente')
    enviado_cocina_en = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'restaurantes_linea_pedido'
        app_label = 'restaurantes'

class PlatoModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(TenantModel, on_delete=models.CASCADE)
    categoria = models.CharField(max_length=100, default='General')
    nombre = models.CharField(max_length=200)
    precio = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    disponible = models.BooleanField(default=True)
    # Hidden inventory product (type 'dish') that holds the recipe; created lazily on first recipe save
    product_id = models.IntegerField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'restaurantes_plato'
        app_label = 'restaurantes'
