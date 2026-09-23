from dataclasses import dataclass
from decimal import Decimal
from typing import List

@dataclass
class SalesMetrics:
    total_sales: Decimal
    total_quotes: int
    total_orders: int
    pending_orders: int
    top_clients: List[dict]

@dataclass
class InventoryMetrics:
    total_products: int
    low_stock_products: int
    inventory_value: Decimal

@dataclass
class HRMetrics:
    total_employees: int
    monthly_payroll: Decimal
    attendances_today: int

@dataclass
class Dashboard:
    tenant_name: str
    sales: SalesMetrics
    inventory: InventoryMetrics
    hr: HRMetrics
