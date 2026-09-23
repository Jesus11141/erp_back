from typing import Optional
from ..domain.entities import Tenant
from ..domain.repositories import TenantRepository
from .django_models import TenantModel, TenantModuloModel

class DjangoTenantRepository(TenantRepository):

    def _to_entity(self, model: TenantModel) -> Tenant:
        modules = list(
            model.modulos.filter(is_active=True).values_list('module', flat=True)
        )
        return Tenant(
            id=model.id,
            name=model.name,
            subdomain=model.subdomain,
            primary_color=model.primary_color,
            secondary_color=model.secondary_color,
            logo_url=model.logo_url,
            is_active=model.is_active,
            modules=modules,
        )

    def find_by_subdomain(self, subdomain: str) -> Optional[Tenant]:
        try:
            model = TenantModel.objects.get(subdomain=subdomain)
            return self._to_entity(model)
        except TenantModel.DoesNotExist:
            return None

    def save(self, tenant: Tenant) -> Tenant:
        model, _ = TenantModel.objects.update_or_create(
            subdomain=tenant.subdomain,
            defaults={
                'name': tenant.name,
                'primary_color': tenant.primary_color,
                'secondary_color': tenant.secondary_color,
                'logo_url': tenant.logo_url,
                'is_active': tenant.is_active,
            }
        )
        TenantModuloModel.objects.filter(tenant=model).update(is_active=False)
        for module in tenant.modules:
            TenantModuloModel.objects.update_or_create(
                tenant=model, module=module,
                defaults={'is_active': True}
            )
        return self._to_entity(model)

    def list(self) -> list[Tenant]:
        return [self._to_entity(m) for m in TenantModel.objects.filter(is_active=True)]
