from typing import List, Dict, Any, Optional
from ..domain.repositories import ReportRepository
from ..domain.entities import Dashboard


class GetCashRegisterClosureSummaryReport:
    """Calculates consolidated cash registers closure report or employee sales detailed report."""
    def __init__(self, repo: ReportRepository):
        self.repo = repo
        
    def execute(self, tenant_id: int, period_type: str, date_str: str,
                branch_id: Optional[int] = None, register_id: Optional[int] = None,
                employee_id: Optional[int] = None) -> Dict[str, Any]:
        return self.repo.get_cash_register_closure_summary_report(
            tenant_id, period_type, date_str, branch_id, register_id, employee_id
        )

