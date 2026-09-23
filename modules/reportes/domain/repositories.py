from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from .entities import SalesMetrics, InventoryMetrics, HRMetrics

class ReportRepository(ABC):
    @abstractmethod
    def get_dashboard_sales(self, tenant_id: int) -> SalesMetrics:
        pass

    @abstractmethod
    def get_dashboard_inventory(self, tenant_id: int) -> InventoryMetrics:
        pass

    @abstractmethod
    def get_dashboard_hr(self, tenant_id: int) -> HRMetrics:
        pass

    @abstractmethod
    def get_profit_margin_report(self, tenant_id: int) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_top_selling_products_report(self, tenant_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_cash_register_closure_report(self, tenant_id: int, closure_id: int) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_cash_register_closure_summary_report(
        self, 
        tenant_id: int, 
        period_type: str, 
        date_str: str,
        branch_id: Optional[int] = None, 
        register_id: Optional[int] = None,
        employee_id: Optional[int] = None
    ) -> Dict[str, Any]:
        pass
