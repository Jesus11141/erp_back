from dataclasses import dataclass, field
from decimal import Decimal
from datetime import date
from typing import List

PLANS = {
    'basic': {
        'name': 'BÃ¡sico',
        'price': Decimal('299'),
        'modules': ['facturacion', 'ventas', 'pos'],
        'max_users': 3,
    },
    'professional': {
        'name': 'Profesional',
        'price': Decimal('699'),
        'modules': ['facturacion', 'ventas', 'inventario', 'compras', 'pos'],
        'max_users': 10,
    },
    'enterprise': {
        'name': 'Enterprise',
        'price': Decimal('1499'),
        'modules': ['facturacion', 'ventas', 'inventario', 'compras', 'rrhh', 'contabilidad', 'pos'],
        'max_users': 999,
    },
}

@dataclass
class Plan:
    key: str
    name: str
    price: Decimal
    modules: List[str]
    max_users: int

@dataclass
class Subscription:
    id: int
    tenant_id: int
    plan_key: str
    start_date: date
    end_date: date
    status: str  # active, expired, canceled

    @property
    def is_active(self) -> bool:
        return self.status == 'active' and self.end_date >= date.today()

    @property
    def remaining_days(self) -> int:
        return max(0, (self.end_date - date.today()).days)

