from ..domain.repositories import SuperAdminRepository
from ..domain.entities import TenantSummary, AVAILABLE_MODULES, AVAILABLE_PLANS
from modules.planes.domain.entities import PLANS


class GetStatistics:
    def __init__(self, repo: SuperAdminRepository):
        self.repo = repo

    def execute(self) -> dict:
        stats = self.repo.get_statistics()
        return {
            'total_tenants': stats.total_tenants,
            'active_tenants': stats.active_tenants,
            'expired_tenants': stats.expired_tenants,
            'monthly_revenue': str(stats.monthly_revenue),
            'most_used_module': stats.most_used_module,
            'new_this_month': stats.new_this_month,
        }

