from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from .value_objects import TableStatus, OrderStatus, KitchenStatus

@dataclass
class RestaurantZone:
    id: int
    tenant_id: int
    name: str

@dataclass
class RestaurantTable:
    id: int
    tenant_id: int
    zone_id: int
    name: str
    seats: int
    status: TableStatus

@dataclass
class RestaurantOrderLine:
    id: int
    item_id: str
    item_name: str
    quantity: int
    unit_price: Decimal
    notes: str
    kitchen_status: KitchenStatus
    sent_to_kitchen_at: Optional[datetime] = None
    table_name: Optional[str] = None
    order_id: Optional[int] = None

@dataclass
class RestaurantOrder:
    id: int
    tenant_id: int
    table_id: int
    status: OrderStatus
    total: Decimal
    created_at: datetime
    lines: List[RestaurantOrderLine] = field(default_factory=list)
