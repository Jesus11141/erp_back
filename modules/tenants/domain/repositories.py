from abc import ABC, abstractmethod
from typing import Optional
from .entities import Tenant

class TenantRepository(ABC):
    @abstractmethod
    def find_by_subdomain(self, subdomain: str) -> Optional[Tenant]:
        pass

    @abstractmethod
    def save(self, tenant: Tenant) -> Tenant:
        pass

    @abstractmethod
    def list(self) -> list[Tenant]:
        pass
