from typing import List, Dict, Any, Optional
from ..domain.repositories import ReportRepository
from ..domain.entities import Dashboard


class GetDashboard:
    def __init__(self, repo: ReportRepository):
        self.repo = repo

    def execute(self, tenant_id: int, tenant_name: str, active_modules: list) -> Dashboard:
        sales = self.repo.get_dashboard_sales(tenant_id) if 'ventas' in active_modules else None
        inventory = self.repo.get_dashboard_inventory(tenant_id) if 'inventario' in active_modules else None
        hr = self.repo.get_dashboard_hr(tenant_id) if 'rrhh' in active_modules else None
        return Dashboard(tenant_name=tenant_name, sales=sales, inventory=inventory, hr=hr)



