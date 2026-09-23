from ..domain.entities import Parameter, CATALOG
from ..domain.repositories import ParameterRepository
from typing import Any


class GetAllParameters:
    def __init__(self, repo: ParameterRepository):
        self.repo = repo

    def execute(self, tenant_id: int) -> dict:
        result = {}
        for module, keys in CATALOG.items():
            result[module] = {}
            for key, info in keys.items():
                param = self.repo.get(tenant_id, module, key)
                value = param.value if (param and param.value) else info['default']
                if module == 'general' and key == 'logo_url' and not value:
                    logo = self.repo.get_tenant_logo_url(tenant_id)
                    if logo:
                        value = logo
                result[module][key] = {
                    'value': value,
                    'label': info['label'],
                    'type': info['type'],
                    'default': info['default'],
                    'options': info.get('options', None),
                }
        return result

