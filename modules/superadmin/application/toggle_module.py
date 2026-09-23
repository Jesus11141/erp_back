from ..domain.repositories import SuperAdminRepository
from ..domain.entities import TenantSummary, AVAILABLE_MODULES, AVAILABLE_PLANS
from modules.planes.domain.entities import PLANS


class ToggleModule:
    def __init__(self, repo: SuperAdminRepository):
        self.repo = repo

    def execute(self, tenant_id: int, module: str, activate: bool) -> TenantSummary:
        if module not in AVAILABLE_MODULES:
            raise ValueError(f"Invalid module. Options: {AVAILABLE_MODULES}")
        if activate:
            return self.repo.activate_module(tenant_id, module)
        return self.repo.deactivate_module(tenant_id, module)


