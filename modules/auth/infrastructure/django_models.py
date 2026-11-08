from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils import timezone

class RoleModel(models.Model):
    tenant_id = models.IntegerField(db_index=True)
    name = models.CharField(max_length=100)
    permissions = models.JSONField(default=list) # Array of permission strings like 'pos.sell'
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'auth_module'
        db_table = 'roles'

class UserManager(BaseUserManager):
    def create_user(self, username, email, tenant_id, name, role, password=None):
        user = self.model(username=username, email=email, tenant_id=tenant_id, name=name, role=role)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password, **extra):
        user = self.model(
            username=username, email=extra.get('email', ''),
            name=extra.get('name', 'Admin'), role='superadmin', tenant_id=0
        )
        user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

class UserModel(AbstractBaseUser, PermissionsMixin):
    # username = tenant_id:email  → garantiza unicidad global
    username = models.CharField(max_length=255, unique=True, db_column='username')
    tenant_id = models.IntegerField(default=0, db_column='tenant_id')
    name = models.CharField(max_length=150, db_column='nombre')
    email = models.EmailField(db_column='email')
    role = models.CharField(max_length=100, default='custom', db_column='rol')
    custom_role = models.ForeignKey('RoleModel', on_delete=models.SET_NULL, null=True, blank=True, db_column='custom_role_id')
    permissions = models.JSONField(default=list, blank=True, db_column='permisos')
    is_active = models.BooleanField(default=True, db_column='activo')
    is_staff = models.BooleanField(default=False, db_column='is_staff')
    created = models.DateTimeField(default=timezone.now, db_column='creado')

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        app_label = 'auth_module'
        db_table = 'usuarios'
        unique_together = ('email', 'tenant_id')

    def __str__(self):
        return f"{self.name} ({self.email})"

    def has_permission(self, permission: str) -> bool:
        if self.permissions and isinstance(self.permissions, list) and len(self.permissions) > 0:
            if '*' in self.permissions:
                return True
            module = permission.split('.')[0]
            return permission in self.permissions or f"{module}.*" in self.permissions
            
        if self.custom_role:
            permissions = self.custom_role.permissions
            if '*' in permissions:
                return True
            module = permission.split('.')[0]
            return permission in permissions or f"{module}.*" in permissions

        permissions_by_role = {
            'superadmin': ['*'],
            'admin':       ['facturacion.*', 'inventario.*', 'ventas.*', 'rrhh.*', 'compras.*', 'reportes.*', 'restaurante.*'],
            'vendedor':    ['ventas.*', 'facturacion.ver', 'facturacion.crear'],
            'contador':    ['facturacion.*', 'contabilidad.*'],
            'almacenista': ['inventario.*'],
            'rrhh':        ['rrhh.*'],
            'mesero':      ['restaurante.mesas', 'restaurante.pedidos'],
            'cajero':      ['restaurante.mesas', 'restaurante.cobrar', 'ventas.pos', 'facturacion.ver', 'facturacion.crear'],
            'cocinero':    ['restaurante.cocina'],
        }
        permissions = permissions_by_role.get(self.role, [])
        if '*' in permissions:
            return True
        module = permission.split('.')[0]
        return permission in permissions or f"{module}.*" in permissions



