from dataclasses import dataclass, field
from decimal import Decimal
from datetime import date
from typing import List, Optional

@dataclass
class Customer:
    id: int
    tenant_id: int
    name: str
    email: str
    phone: str
    address: str
    rfc: str = ''
    active: bool = True

@dataclass
class SaleProduct:
    product_id: int
    description: str
    quantity: Decimal
    unit_price: Decimal
    discount: Decimal = Decimal('0')

    @property
    def subtotal(self) -> Decimal:
        base = self.quantity * self.unit_price
        return base - (base * self.discount / 100)

@dataclass
class PaymentMethod:
    id: Optional[int]
    tenant_id: int
    name: str
    active: bool = True
    requires_reference: bool = False
    sri_code: Optional[str] = '01'

@dataclass
class Quotation:
    id: int
    tenant_id: int
    customer_id: int
    customer_name: str
    date: date
    status: str
    items: List[SaleProduct] = field(default_factory=list)
    notes: str = ''
    vat: Decimal = Decimal('12')
    validity_days: int = 15
    payment_terms: str = ''
    delivery_time: str = ''
    print_style: str = 'corporativo'
    show_images: bool = False
    is_preinvoice: bool = False
    seller_id: int | None = None
    branch_id: int | None = None

    STATUS_CHOICES = ['draft', 'sent', 'accepted', 'rejected', 'expired']

    @property
    def subtotal(self) -> Decimal:
        return sum(i.subtotal for i in self.items)

    @property
    def vat_amount(self) -> Decimal:
        return self.subtotal * self.vat / 100

    @property
    def total(self) -> Decimal:
        return self.subtotal + self.vat_amount

    def accept(self):
        if self.status not in ['sent', 'draft']:
            raise ValueError("Only a sent or draft quotation can be accepted")
        self.status = 'accepted'

    def send(self):
        if self.status != 'draft':
            raise ValueError("Only a draft quotation can be sent")
        if not self.items:
            raise ValueError("The quotation has no products")
        self.status = 'sent'

@dataclass
class Order:
    id: int
    tenant_id: int
    customer_id: int
    customer_name: str
    quotation_id: Optional[int]
    date: date
    status: str
    items: List[SaleProduct] = field(default_factory=list)
    vat: Decimal = Decimal('12')

    STATUS_CHOICES = ['pending', 'in_progress', 'delivered', 'canceled']

    @property
    def subtotal(self) -> Decimal:
        return sum(i.subtotal for i in self.items)

    @property
    def vat_amount(self) -> Decimal:
        return self.subtotal * self.vat / 100

    @property
    def total(self) -> Decimal:
        return self.subtotal + self.vat_amount

    def deliver(self):
        if self.status != 'in_progress':
            raise ValueError("The order must be in progress to be delivered")
        self.status = 'delivered'

    def cancel(self):
        if self.status == 'delivered':
            raise ValueError("A delivered order cannot be canceled")
        self.status = 'canceled'

@dataclass
class AccountReceivable:
    id: Optional[int]
    tenant_id: int
    customer_id: int
    customer_name: str
    total_amount: Decimal
    balance_due: Decimal
    status: str = 'PENDING'
    reference_type: str = ''
    reference_id: Optional[int] = None

@dataclass
class ReceivablePayment:
    id: Optional[int]
    account_receivable_id: int
    amount: Decimal
    payment_method: str
    date: date
    notes: str = ''
