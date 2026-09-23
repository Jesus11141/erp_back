from dataclasses import dataclass, field
from decimal import Decimal
from datetime import date, datetime
from typing import List, Optional

AVAILABLE_MODULES = [
    'facturacion', 'ventas', 'inventario',
    'compras', 'rrhh', 'contabilidad', 'pos', 'clinica', 'technical_service', 'auditoria', 'usuarios', 'roles', 'centros_costos',
    'notas_venta', 'restaurantes', 'sri_perfil', 'sri_facturas'
]

AVAILABLE_PLANS = ['basic', 'professional', 'enterprise']

@dataclass
class TenantSummary:
    id: int
    name: str
    subdomain: str
    active: bool
    plan: str
    modules: List[str]
    primary_color: str
    secondary_color: str
    logo_url: str
    creation_date: Optional[datetime]
    total_users: int = 0
    ruc: str = ''
    contact_email: str = ''
    contact_phone: str = ''
    contract_start_date: Optional[date] = None
    expiration_date: Optional[date] = None
    subscription_status: str = 'active'
    admin_email: str = ''
    max_devices: int = 1

    @property
    def _expiration_date_obj(self) -> Optional[date]:
        if not self.expiration_date:
            return None
        if isinstance(self.expiration_date, str):
            try:
                s = self.expiration_date.strip()
                return date.fromisoformat(s[:10])
            except (ValueError, TypeError):
                return None
        if isinstance(self.expiration_date, datetime):
            return self.expiration_date.date()
        return self.expiration_date

    @property
    def is_expired(self) -> bool:
        v_date = self._expiration_date_obj
        if not v_date:
            return False
        return v_date < date.today()

    @property
    def remaining_days(self) -> Optional[int]:
        v_date = self._expiration_date_obj
        if not v_date:
            return None
        return max(0, (v_date - date.today()).days)

@dataclass
class GlobalStatistics:
    total_tenants: int
    active_tenants: int
    expired_tenants: int
    monthly_revenue: Decimal
    most_used_module: str
    new_this_month: int
