from ..domain.entities import Parameter, CATALOG
from ..domain.repositories import ParameterRepository
from typing import Any


class SaveParameter:
    def __init__(self, repo: ParameterRepository):
        self.repo = repo

    def execute(self, tenant_id: int, module: str, key: str, value: str) -> Parameter:
        if module not in CATALOG:
            raise ValueError(f"Module '{module}' does not exist in the catalog")
        if key not in CATALOG[module]:
            raise ValueError(f"Parameter '{key}' does not exist in module '{module}'")
        param = Parameter(tenant_id=tenant_id, module=module, key=key, value=str(value))
        return self.repo.save(param)


