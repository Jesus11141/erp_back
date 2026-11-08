from typing import Optional
from ..domain.entities import User
from ..domain.repositories import UserRepository
from .django_models import UserModel

def _make_username(email: str, tenant_id: int) -> str:
    return f"{tenant_id}:{email}"

class DjangoUserRepository(UserRepository):

    def _to_entity(self, model: UserModel) -> User:
        perms = list(model.permissions) if model.permissions else []
        if model.custom_role and model.custom_role.permissions:
            perms.extend(model.custom_role.permissions)
            
        if not perms and model.role:
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
            perms.extend(permissions_by_role.get(model.role, []))

        perms = list(set(perms))
            
        return User(
            id=model.id,
            tenant_id=model.tenant_id,
            name=model.name,
            email=model.email,
            role=model.role,
            is_active=model.is_active,
            custom_permissions=perms,
        )

    def find_by_email(self, email: str, tenant_id: int) -> Optional[User]:
        try:
            m = UserModel.objects.get(email=email, tenant_id=tenant_id)
            return self._to_entity(m)
        except UserModel.DoesNotExist:
            return None

    def find_by_id(self, id: int) -> Optional[User]:
        try:
            return self._to_entity(UserModel.objects.get(id=id))
        except UserModel.DoesNotExist:
            return None

    def save(self, user: User, password: str = None) -> User:
        if user.id:
            m = UserModel.objects.get(id=user.id)
            m.name = user.name
            m.email = user.email
            m.username = _make_username(user.email, user.tenant_id)
            m.role = user.role
            m.is_active = user.is_active
            if password:
                m.set_password(password)
            m.save()
        else:
            m = UserModel.objects.create_user(
                username=_make_username(user.email, user.tenant_id),
                email=user.email,
                tenant_id=user.tenant_id,
                name=user.name,
                role=user.role,
                password=password,
            )
        return self._to_entity(m)

    def list_by_tenant(self, tenant_id: int) -> list[User]:
        return [self._to_entity(m) for m in UserModel.objects.filter(tenant_id=tenant_id)]

    def verify_password(self, email: str, tenant_id: int, password: str) -> bool:
        try:
            m = UserModel.objects.get(email=email, tenant_id=tenant_id)
            return m.check_password(password)
        except UserModel.DoesNotExist:
            return False
