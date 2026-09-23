from ..domain.entities import Parameter, CATALOG
from ..domain.repositories import ParameterRepository
from typing import Any


class GetParameter:
    def __init__(self, repo: ParameterRepository):
        self.repo = repo

    def execute(self, tenant_id: int, module: str, key: str, default: str = None) -> Any:
        param = self.repo.get(tenant_id, module, key)
        if param:
            return param.typed_value()
        # If it doesn't exist, return the catalog default
        catalog_default = CATALOG.get(module, {}).get(key, {}).get('default', default or '')
        p = Parameter(tenant_id=tenant_id, module=module, key=key, value=catalog_default)
        return p.typed_value()


