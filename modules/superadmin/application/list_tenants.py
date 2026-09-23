from ..domain.repositories import SuperAdminRepository
from ..domain.entities import TenantSummary, AVAILABLE_MODULES, AVAILABLE_PLANS
from modules.planes.domain.entities import PLANS


class ListTenants:
    def __init__(self, repo: SuperAdminRepository):
        self.repo = repo

    def execute(self) -> list:
        return self.repo.list_tenants()


