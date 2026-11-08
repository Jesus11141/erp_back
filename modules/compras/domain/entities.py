from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional


@dataclass
class Proveedor:
    id: int
    tenant_id: int
    identification: str
    id_type: str  # '04' RUC, '05' Cedula, '06' Pasaporte
    business_name: str
    commercial_name: str = ''
    email: str = ''
    phone: str = ''
    address: str = ''
    credit_days: int = 0
    active: bool = True
    bank_name: str = ''
    bank_account_type: str = 'AHO'
    bank_account_number: str = ''
    beneficiary_name: str = ''
    beneficiary_id: str = ''
    created_at: Optional[datetime] = None


@dataclass
class OrdenCompraItem:
    id: int
    product_id: Optional[int]
    description: str
    quantity: Decimal
    unit_price: Decimal
    discount: Decimal
    vat_rate: str
    subtotal: Decimal


@dataclass
class OrdenCompra:
    id: int
    tenant_id: int
    number: str
    supplier_id: int
    supplier_name: str
    date: date
    expected_delivery_date: Optional[date]
    status: str  # 'borrador', 'solicitada', 'aprobada', 'recibida', 'cancelada'
    payment_terms: str
    notes: str
    subtotal: Decimal
    discount: Decimal
    vat: Decimal
    total: Decimal
    branch_id: Optional[int] = None
    items: List[OrdenCompraItem] = field(default_factory=list)
    created_at: Optional[datetime] = None


@dataclass
class FacturaCompraItem:
    id: int
    product_id: Optional[int]
    description: str
    quantity: Decimal
    unit_price: Decimal
    discount: Decimal
    vat_rate: str
    subtotal: Decimal


@dataclass
class FacturaCompra:
    id: int
    tenant_id: int
    supplier_id: int
    supplier_name: str
    invoice_number: str  # Ej: 001-001-000012345
    access_key: str  # 49 digitos o autorizacion
    date: date
    registration_date: date
    purchase_type: str  # 'inventario', 'gasto'
    payment_condition: str  # 'contado', 'credito'
    credit_days: int
    due_date: Optional[date]
    status: str  # 'registrada', 'anulada'
    reception_status: str  # 'pendiente', 'recibida', 'no_aplica'
    subtotal_0: Decimal
    subtotal_iva: Decimal
    discount: Decimal
    vat: Decimal
    total: Decimal
    branch_id: Optional[int] = None
    purchase_order_id: Optional[int] = None
    journal_entry_id: Optional[int] = None
    items: List[FacturaCompraItem] = field(default_factory=list)
    created_at: Optional[datetime] = None


@dataclass
class CuentaPagar:
    id: int
    tenant_id: int
    supplier_id: int
    supplier_name: str
    invoice_id: int
    invoice_number: str
    total_amount: Decimal
    balance_due: Decimal
    due_date: Optional[date]
    status: str  # 'PENDING', 'PARTIAL', 'PAID'
    created_at: Optional[datetime] = None


@dataclass
class AbonoCuentaPagar:
    id: int
    tenant_id: int
    account_payable_id: int
    amount: Decimal
    payment_date: date
    payment_method: str  # 'efectivo', 'transferencia', 'cheque', 'otro'
    reference: str
    notes: str
    created_at: Optional[datetime] = None
