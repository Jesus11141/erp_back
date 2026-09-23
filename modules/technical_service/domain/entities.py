from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime
from typing import List, Optional

@dataclass
class WorkOrderItem:
    id: Optional[int]
    product_id: Optional[int]  # Can be None if it's purely labor/custom charge
    description: str
    quantity: Decimal
    unit_price: Decimal
    discount: Decimal = Decimal('0')

    @property
    def subtotal(self) -> Decimal:
        base = self.quantity * self.unit_price
        return base - (base * self.discount / 100)

@dataclass
class WorkOrder:
    id: Optional[int]
    tenant_id: int
    customer_id: int
    customer_name: str
    device_type: str
    device_model: str
    device_identifier: str  # e.g., IMEI, Serial Number
    physical_conditions: str
    reported_fault: str
    advance_payment: Decimal
    status: str
    items: List[WorkOrderItem] = field(default_factory=list)
    vat: Decimal = Decimal('12')
    created_at: Optional[datetime] = None

    STATUS_CHOICES = ['RECEIVED', 'IN_REPAIR', 'READY', 'DELIVERED']

    @property
    def subtotal(self) -> Decimal:
        return sum(i.subtotal for i in self.items)

    @property
    def vat_amount(self) -> Decimal:
        # If prices include VAT, we don't add it on top. 
        # If we need to extract the VAT amount from the total for accounting:
        # return self.subtotal - (self.subtotal / (1 + self.vat / 100))
        return Decimal('0')

    @property
    def total(self) -> Decimal:
        # Total is exactly the subtotal because prices already include VAT
        return self.subtotal

    @property
    def balance_due(self) -> Decimal:
        """Total minus the advance payment"""
        balance = self.total - self.advance_payment
        return balance if balance > 0 else Decimal('0')

    def change_status(self, new_status: str):
        if new_status not in self.STATUS_CHOICES:
            raise ValueError(f"Invalid status. Must be one of: {self.STATUS_CHOICES}")
        self.status = new_status
