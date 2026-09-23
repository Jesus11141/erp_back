from typing import Optional
from modules.technical_service.domain.entities import WorkOrder
from modules.technical_service.domain.repositories import WorkOrderRepository

class UpdateWorkOrderStatusUseCase:
    def __init__(self, order_repo: WorkOrderRepository):
        self.order_repo = order_repo
        
    def execute(self, tenant_id: int, order_id: int, new_status: str) -> Optional[WorkOrder]:
        order = self.order_repo.find_by_id(order_id, tenant_id)
        if not order:
            return None
            
        order.change_status(new_status)
        return self.order_repo.save(order)
