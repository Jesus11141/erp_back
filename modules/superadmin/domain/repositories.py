from abc import ABC, abstractmethod
from typing import Optional, List
from .entities import TenantSummary, GlobalStatistics

class SuperAdminRepository(ABC):

    @abstractmethod
    def list_tenants(self) -> List[TenantSummary]: pass

    @abstractmethod
    def find_tenant(self, tenant_id: int) -> Optional[TenantSummary]: pass

    @abstractmethod
    def create_tenant(self, data: dict) -> TenantSummary: pass

    @abstractmethod
    def update_tenant(self, tenant_id: int, data: dict) -> TenantSummary: pass

    @abstractmethod
    def activate_tenant(self, tenant_id: int) -> TenantSummary: pass

    @abstractmethod
    def deactivate_tenant(self, tenant_id: int) -> TenantSummary: pass

    @abstractmethod
    def activate_module(self, tenant_id: int, module: str) -> TenantSummary: pass

    @abstractmethod
    def deactivate_module(self, tenant_id: int, module: str) -> TenantSummary: pass

    @abstractmethod
    def get_statistics(self) -> GlobalStatistics: pass
