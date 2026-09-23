from typing import List, Dict, Any, Optional
from ..domain.repositories import ReportRepository
from ..domain.entities import Dashboard


class GetProfitMarginReport:
    """Calculates profitability and profit margins for POS sales."""
    def __init__(self, repo: ReportRepository):
        self.repo = repo
        
    def execute(self, tenant_id: int) -> List[Dict[str, Any]]:
        return self.repo.get_profit_margin_report(tenant_id)



