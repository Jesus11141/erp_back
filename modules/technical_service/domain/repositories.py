from abc import ABC, abstractmethod
from typing import Optional, List
from .entities import WorkOrder

class WorkOrderRepository(ABC):
    @abstractmethod
    def save(self, order: WorkOrder) -> WorkOrder:
        pass
    
    @abstractmethod
    def find_by_id(self, id: int, tenant_id: int) -> Optional[WorkOrder]:
        pass
    
    @abstractmethod
    def list_by_tenant(self, tenant_id: int) -> List[WorkOrder]:
        pass
    
    @abstractmethod
    def delete(self, id: int, tenant_id: int):
        pass
