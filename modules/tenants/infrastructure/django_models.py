from django.db import models

MODULE_CHOICES = [
    ('facturacion', 'Billing'),
    ('inventario', 'Inventory'),
    ('rrhh', 'Human Resources'),
    ('contabilidad', 'Accounting'),
    ('accounting', 'Fiscal & Accounting (SRI)'),
    ('compras', 'Purchasing'),
    ('ventas', 'Sales'),
    ('pos', 'Point of Sale'),
    ('clinica', 'Clinic and Lab'),
    ('technical_service', 'Technical Service'),
    ('auditoria', 'Audit Log'),
    ('usuarios', 'Gestión Usuarios'),
    ('roles', 'Roles Dinámicos'),
    ('centros_costos', 'Centros de Costos'),
    ('restaurantes', 'Restaurantes y Gastronomía'),
    ('sri_perfil', 'Consulta RUC Automática'),
    ('sri_facturas', 'Extracción Facturas (Robot)'),
    ('notas_venta', 'Notas de Venta / Cotizaciones'),
    ('reportes', 'Reportes Avanzados'),
]

from django.utils import timezone

class PlanModel(models.Model):
    key = models.CharField(max_length=50, unique=True, db_column='clave')
    name = models.CharField(max_length=100, db_column='nombre')
    price = models.DecimalField(max_digits=10, decimal_places=2, db_column='precio')
    max_users = models.IntegerField(default=1, db_column='max_usuarios')
    max_devices = models.IntegerField(default=1, db_column='max_dispositivos')
    modules = models.JSONField(default=list, db_column='modulos')
    created = models.DateTimeField(default=timezone.now, db_column='creado')

    class Meta:
        app_label = 'tenants'
        db_table = 'planes'

    def __str__(self):
        return self.name
class TenantModel(models.Model):
    SUBSCRIPTION_STATES = [('activa', 'Active'), ('suspendida', 'Suspended'), ('vencida', 'Expired'), ('demo', 'Demo')]
    name = models.CharField(max_length=100, default='', db_column='nombre')
    subdomain = models.CharField(max_length=50, unique=True, db_column='subdominio')
    ruc = models.CharField(max_length=13, blank=True, default='', db_column='ruc')
    contact_email = models.EmailField(blank=True, default='', db_column='email_contacto')
    contact_phone = models.CharField(max_length=20, blank=True, default='', db_column='telefono_contacto')
    contract_start_date = models.DateField(null=True, blank=True, db_column='fecha_inicio_contrato')
    expiration_date = models.DateField(null=True, blank=True, db_column='fecha_vencimiento')
    subscription_state = models.CharField(max_length=20, choices=SUBSCRIPTION_STATES, default='activa', db_column='estado_suscripcion')
    logo_url = models.CharField(max_length=255, blank=True, db_column='logo_url')
    primary_color = models.CharField(max_length=7, default='#1976D2', db_column='color_primario')
    secondary_color = models.CharField(max_length=7, default='#424242', db_column='color_secundario')
    is_active = models.BooleanField(default=True, db_column='activo')
    max_devices = models.IntegerField(default=1, db_column='max_dispositivos')
    created = models.DateTimeField(default=timezone.now, db_column='creado')

    class Meta:
        app_label = 'tenants'
        db_table = 'tenants'

    def __str__(self):
        return self.name

class TenantModuloModel(models.Model):
    tenant = models.ForeignKey(TenantModel, on_delete=models.CASCADE, related_name='modulos', db_column='tenant_id')
    module = models.CharField(max_length=50, choices=MODULE_CHOICES, db_column='modulo')
    is_active = models.BooleanField(default=True, db_column='activo')

    class Meta:
        app_label = 'tenants'
        db_table = 'tenant_modulos'
        unique_together = ('tenant', 'module')


class DeviceRegistrationModel(models.Model):
    user = models.ForeignKey('auth_module.UserModel', on_delete=models.CASCADE, related_name='devices', db_column='user_id', null=True, blank=True)
    device_uuid = models.CharField(max_length=100, db_column='dispositivo_uuid')
    device_name = models.CharField(max_length=100, blank=True, db_column='nombre_dispositivo')
    last_login = models.DateTimeField(auto_now=True, db_column='ultimo_login')
    created = models.DateTimeField(default=timezone.now, db_column='creado')

    class Meta:
        app_label = 'tenants'
        db_table = 'tenant_devices'
        unique_together = ('user', 'device_uuid')

class TenantFeatureToggleModel(models.Model):
    tenant = models.ForeignKey(TenantModel, on_delete=models.CASCADE, related_name='features', db_column='tenant_id')
    feature_key = models.CharField(max_length=100, db_column='feature_key')
    is_enabled = models.BooleanField(default=False, db_column='is_enabled')

    class Meta:
        app_label = 'tenants'
        db_table = 'tenant_feature_toggles'
        unique_together = ('tenant', 'feature_key')

