from ..domain.repositories import SuperAdminRepository
from ..domain.entities import TenantSummary, AVAILABLE_MODULES, AVAILABLE_PLANS
from modules.planes.domain.entities import PLANS


class ToggleTenant:
    def __init__(self, repo: SuperAdminRepository):
        self.repo = repo

    def execute(self, tenant_id: int, activate: bool) -> TenantSummary:
        if activate:
            return self.repo.activate_tenant(tenant_id)
        return self.repo.deactivate_tenant(tenant_id)


