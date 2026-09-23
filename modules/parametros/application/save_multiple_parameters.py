from ..domain.entities import Parameter, CATALOG
from ..domain.repositories import ParameterRepository
from typing import Any


class SaveMultipleParameters:
    def __init__(self, repo: ParameterRepository):
        self.repo = repo

    def execute(self, tenant_id: int, module: str, parameters: dict) -> list:
        saved = []
        for key, value in parameters.items():
            if key in CATALOG.get(module, {}):
                param = Parameter(tenant_id=tenant_id, module=module, key=key, value=str(value))
                saved.append(self.repo.save(param))
        return saved


