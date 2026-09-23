from ..domain.repositories import TenantRepository
from ..domain.entities import Tenant


class GetTenantConfig:
    def __init__(self, repo: TenantRepository):
        self.repo = repo

    def execute(self, subdomain: str) -> Tenant:
        tenant = self.repo.find_by_subdomain(subdomain)
        if not tenant:
            raise ValueError(f"Tenant '{subdomain}' not found")
        if not tenant.is_active:
            raise PermissionError("Inactive tenant")
        return tenant


