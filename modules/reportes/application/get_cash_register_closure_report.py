from typing import List, Dict, Any, Optional
from ..domain.repositories import ReportRepository
from ..domain.entities import Dashboard


class GetCashRegisterClosureReport:
    """Retrieves a consolidated summary of a specific closed cash session."""
    def __init__(self, repo: ReportRepository):
        self.repo = repo
        
    def execute(self, tenant_id: int, closure_id: int) -> Dict[str, Any]:
        return self.repo.get_cash_register_closure_report(tenant_id, closure_id)



