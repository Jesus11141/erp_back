from abc import ABC, abstractmethod
from typing import Optional, List
from .entities import Parameter

class ParameterRepository(ABC):
    @abstractmethod
    def get(self, tenant_id: int, module: str, key: str) -> Optional[Parameter]: pass

    @abstractmethod
    def save(self, parameter: Parameter) -> Parameter:
        pass

    @abstractmethod
    def get_tenant_logo_url(self, tenant_id: int) -> Optional[str]:
        pass

    @abstractmethod
    def list_by_module(self, tenant_id: int, module: str) -> List[Parameter]: pass

    @abstractmethod
    def list_all(self, tenant_id: int) -> List[Parameter]: pass
