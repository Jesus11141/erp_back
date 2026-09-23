from typing import List
from modules.technical_service.domain.entities import WorkOrder
from modules.technical_service.domain.repositories import WorkOrderRepository

class ListWorkOrdersUseCase:
    def __init__(self, order_repo: WorkOrderRepository):
        self.order_repo = order_repo
        
    def execute(self, tenant_id: int) -> List[WorkOrder]:
        return self.order_repo.list_by_tenant(tenant_id)
