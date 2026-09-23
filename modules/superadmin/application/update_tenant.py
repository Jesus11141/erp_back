from ..domain.repositories import SuperAdminRepository
from ..domain.entities import TenantSummary, AVAILABLE_MODULES, AVAILABLE_PLANS
from modules.planes.domain.entities import PLANS


class UpdateTenant:
    def __init__(self, repo: SuperAdminRepository):
        self.repo = repo

    def execute(self, tenant_id: int, data: dict) -> TenantSummary:
        tenant = self.repo.find_tenant(tenant_id)
        if not tenant:
            raise ValueError("Company not found")
        return self.repo.update_tenant(tenant_id, data)


