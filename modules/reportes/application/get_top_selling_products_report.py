from typing import List, Dict, Any, Optional
from ..domain.repositories import ReportRepository
from ..domain.entities import Dashboard


class GetTopSellingProductsReport:
    """Calculates the best selling products by quantity and revenue."""
    def __init__(self, repo: ReportRepository):
        self.repo = repo
        
    def execute(self, tenant_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        return self.repo.get_top_selling_products_report(tenant_id, limit)



