from dataclasses import dataclass, field
from typing import List

@dataclass
class Tenant:
    id: int
    name: str
    subdomain: str
    primary_color: str
    secondary_color: str
    logo_url: str
    is_active: bool
    modules: List[str] = field(default_factory=list)

    def has_module(self, module: str) -> bool:
        return module in self.modules

    def activate_module(self, module: str):
        if module not in self.modules:
            self.modules.append(module)

    def deactivate_module(self, module: str):
        self.modules = [m for m in self.modules if m != module]
