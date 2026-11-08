from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional
from datetime import datetime

@dataclass
class POSCustomer:
    name: str
    identifier: str
    id_type: str
    address: str = ""
    email: str = ""
    payment_form: str = "01"

    @classmethod
    def default_final_consumer(cls) -> "POSCustomer":
        return cls(
            name="CONSUMIDOR FINAL",
            identifier="9999999999999",
            id_type="07",
            address="",
            email="",
            payment_form="01"
        )

@dataclass
class CashRegister:
    id: int
    tenant_id: int
    name: str          # e.g., "Cash Register 1"
    user_id: int
    status: str        # 'open', 'closed'
    initial_balance: Decimal
    final_balance: Optional[Decimal]
    opened_at: Optional[datetime]
    closed_at: Optional[datetime]
    opening_breakdown: Optional[dict] = None
    branch_id: Optional[int] = None
    emission_point: str = '001'

    def open(self, initial_balance: Decimal, user_id: int, opening_breakdown: Optional[dict] = None):
        if self.status == 'open':
            raise ValueError("The register is already open")
        self.status = 'open'
        self.initial_balance = initial_balance
        self.user_id = user_id
        self.opened_at = datetime.now()
        self.opening_breakdown = opening_breakdown

    def close(self, final_balance: Decimal):
        if self.status == 'closed':
            raise ValueError("The register is already closed")
        self.status = 'closed'
        self.final_balance = final_balance
        self.closed_at = datetime.now()

    @property
    def balance_difference(self) -> Optional[Decimal]:
        if self.final_balance is None:
            return None
        return self.final_balance - self.initial_balance

@dataclass
class POSSaleItem:
    product_id: Optional[int]
    code: str
    description: str
    quantity: Decimal
    unit_price: Decimal
    discount: Decimal = Decimal('0')

    @property
    def subtotal(self) -> Decimal:
        base = self.quantity * self.unit_price
        return base - (base * self.discount / 100)

@dataclass
class POSSale:
    id: int
    tenant_id: int
    register_id: int
    user_id: int
    customer: POSCustomer
    seller_id: Optional[int] = None
    items: List[POSSaleItem] = field(default_factory=list)
    payment_method: str = 'cash'     # 'cash', 'card', 'transfer'
    amount_received: Decimal = Decimal('0')
    status: str = 'pending'          # 'pending', 'completed', 'cancelled'
    created_at: Optional[datetime] = None
    invoice_id: Optional[int] = None
    invoice_number: Optional[str] = None
    access_key: Optional[str] = None
    reference_number: Optional[str] = None
    vat_rate: Decimal = Decimal('0.12')
    document_type: str = '01'

    @property
    def subtotal(self) -> Decimal:
        return sum(i.subtotal for i in self.items)

    @property
    def vat_amount(self) -> Decimal:
        return (self.subtotal * self.vat_rate).quantize(Decimal('0.01'))

    @property
    def total(self) -> Decimal:
        return self.subtotal + self.vat_amount

    @property
    def change(self) -> Decimal:
        if self.payment_method != 'cash':
            return Decimal('0')
        return max(Decimal('0'), self.amount_received - self.total)

    def complete(self):
        if self.status != 'pending':
            raise ValueError("The sale has already been processed")
        if not self.items:
            raise ValueError("No products in the sale")
        if self.payment_method == 'cash' and self.amount_received < self.total:
            raise ValueError(f"Insufficient amount received. Total: {self.total}, Received: {self.amount_received}")
        self.status = 'completed'
        self.created_at = datetime.now()

    def cancel(self):
        if self.status == 'completed':
            raise ValueError("Cannot cancel a completed sale")
        self.status = 'cancelled'

@dataclass
class POSSaleSummary:
    sale_id: int
    created_at: Optional[datetime]
    customer_name: str
    payment_method: str
    reference_number: str
    total: Decimal

@dataclass
class CashRegisterMovement:
    id: int
    tenant_id: int
    register_id: int
    user_id: int
    movement_type: str # 'inflow' (ingreso), 'outflow' (egreso)
    amount: Decimal
    reason: str
    created_at: Optional[datetime] = None

@dataclass
class CashRegisterClosure:
    id: int
    tenant_id: int
    register_id: int
    user_id: int
    opened_at: datetime
    closed_at: datetime
    initial_balance: Decimal
    total_cash: Decimal
    total_card: Decimal
    total_transfer: Decimal
    total_inflows: Decimal
    total_outflows: Decimal
    sales_count: int
    expected_balance: Decimal
    counted_balance: Decimal
    difference: Decimal
    observations: str
    closure_breakdown: Optional[dict] = None

@dataclass
class PhysicalCashRegister:
    id: int
    tenant_id: int
    branch_id: Optional[int]
    code: str
    name: str
    primary_cashier_id: Optional[int]
    active: bool = True
