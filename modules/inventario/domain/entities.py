from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from typing import Optional

@dataclass
class Category:
    id: int
    tenant_id: int
    name: str

@dataclass
class Product:
    id: int
    tenant_id: int
    code: str
    name: str
    description: str
    category: str
    purchase_price: Decimal
    sale_price: Decimal
    current_stock: Decimal
    minimum_stock: Decimal
    unit: str
    vat_rate: str = '15'   # SRI Ecuador: '0', '5', '8', '15'
    active: bool = True
    is_composite: bool = False
    image: Optional[str] = None

    # SRI Ecuador VAT rate codes mapping
    _VAT_RATE_CODES = {'0': '0', '5': '5', '8': '8', '15': '2', '12': '2'}

    @property
    def vat_rate_code(self) -> str:
        return self._VAT_RATE_CODES.get(str(self.vat_rate), '2')

    @property
    def low_stock(self) -> bool:
        return self.current_stock <= self.minimum_stock

    @property
    def margin(self) -> Decimal:
        if self.purchase_price == 0:
            return Decimal('0')
        return ((self.sale_price - self.purchase_price) / self.purchase_price * 100).quantize(Decimal('0.01'))

    def adjust_stock(self, quantity: Decimal, type: str):
        if type == 'in':
            self.current_stock += quantity
        elif type == 'out':
            if self.current_stock < quantity:
                raise ValueError(f"Insufficient stock. Available: {self.current_stock}")
            self.current_stock -= quantity
        elif type == 'adjustment':
            self.current_stock = quantity


@dataclass
class StockMovement:
    id: int
    tenant_id: int
    product_id: int
    product_name: str
    type: str
    quantity: Decimal
    previous_stock: Decimal
    new_stock: Decimal
    reference: str
    created_at: datetime
    user_id: int
