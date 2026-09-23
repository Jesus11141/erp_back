from typing import Optional, List
from ..domain.entities import Parameter
from ..domain.repositories import ParameterRepository
from .django_models import ParameterModel

class DjangoParameterRepository(ParameterRepository):

    def _to_entity(self, m: ParameterModel) -> Parameter:
        return Parameter(tenant_id=m.tenant_id, module=m.module, key=m.key, value=m.value)

    def get(self, tenant_id: int, module: str, key: str) -> Optional[Parameter]:
        try:
            return self._to_entity(ParameterModel.objects.get(tenant_id=tenant_id, module=module, key=key))
        except ParameterModel.DoesNotExist:
            return None

    def save(self, parameter: Parameter) -> Parameter:
        m, _ = ParameterModel.objects.update_or_create(
            tenant_id=parameter.tenant_id,
            module=parameter.module,
            key=parameter.key,
            defaults={'value': parameter.value}
        )
        return self._to_entity(m)

    def get_tenant_logo_url(self, tenant_id: int) -> Optional[str]:
        from modules.tenants.infrastructure.django_models import TenantModel
        t = TenantModel.objects.filter(id=tenant_id).first()
        if t and t.logo_url:
            return t.logo_url
        return None

    def list_by_module(self, tenant_id: int, module: str) -> List[Parameter]:
        return [self._to_entity(m) for m in ParameterModel.objects.filter(tenant_id=tenant_id, module=module)]

    def list_all(self, tenant_id: int) -> List[Parameter]:
        return [self._to_entity(m) for m in ParameterModel.objects.filter(tenant_id=tenant_id)]
