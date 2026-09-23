from ..domain.repositories import TenantRepository
from ..domain.entities import Tenant


class DeactivateModule:
    def __init__(self, repo: TenantRepository):
        self.repo = repo

    def execute(self, subdomain: str, module: str) -> Tenant:
        tenant = self.repo.find_by_subdomain(subdomain)
        if not tenant:
            raise ValueError("Tenant not found")
        tenant.deactivate_module(module)
        return self.repo.save(tenant)

