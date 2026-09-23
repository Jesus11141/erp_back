from dataclasses import dataclass, field
from typing import List

@dataclass
class User:
    id: int
    tenant_id: int
    name: str
    email: str
    role: str
    is_active: bool = True
    custom_permissions: List[str] = field(default_factory=list)

    def has_permission(self, permission: str) -> bool:
        if self.role == 'superadmin':
            return True
        if '*' in self.custom_permissions:
            return True
        module = permission.split('.')[0]
        return permission in self.custom_permissions or f'{module}.*' in self.custom_permissions

    def can_view(self, module: str) -> bool:
        return self.has_permission(f'{module}.view') or self.has_permission(f'{module}.*')

