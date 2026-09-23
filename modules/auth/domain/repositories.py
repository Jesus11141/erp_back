from abc import ABC, abstractmethod
from typing import Optional
from .entities import User

class UserRepository(ABC):
    @abstractmethod
    def find_by_email(self, email: str, tenant_id: int) -> Optional[User]:
        pass

    @abstractmethod
    def find_by_id(self, id: int) -> Optional[User]:
        pass

    @abstractmethod
    def save(self, user: User, password: str = None) -> User:
        pass

    @abstractmethod
    def list_by_tenant(self, tenant_id: int) -> list[User]:
        pass

    @abstractmethod
    def verify_password(self, email: str, tenant_id: int, password: str) -> bool:
        pass

