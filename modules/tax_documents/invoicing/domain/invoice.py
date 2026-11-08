from dataclasses import dataclass, field
from decimal import Decimal
from datetime import date, datetime
from typing import List, Optional

# â”€â”€ Invoice â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@dataclass
class InvoiceItem:
    description: str
    quantity: Decimal
    unit_price: Decimal
    discount: Decimal = Decimal('0')
    main_code: str = ''
    auxiliary_code: str = ''
    vat_rate: str = '15'

    @property
    def subtotal(self) -> Decimal:
        base = self.quantity * self.unit_price
        return base - (base * self.discount / 100)

@dataclass
class Invoice:
    id: int
    tenant_id: int
    document_type: str   # '01' factura, '02' nota de venta
    number: str          # 001-001-000000001
    client: str
    client_identification: str
    client_id_type: str  # 04=RUC, 05=cedula, 06=pasaporte
    client_address: str
    client_email: str
    date: date
    status: str
    items: List[InvoiceItem] = field(default_factory=list)
    vat: Decimal = Decimal('12')
    payment_method: str = '01'   # código SRI: 01=efectivo, 19=crédito, etc.
    notes: str = ''
    # Campos SRI
    access_key: str = ''
    authorization_number: str = ''
    authorization_date: str = ''
    environment: str = '1'   # 1=pruebas, 2=produccion
    signed_xml: str = ''
    ride_url: str = ''
    sri_status: str = ''  # RECIBIDA, AUTORIZADA, NO_AUTORIZADA
    sri_message: str = ''
    created_at: datetime = None

    VALID_STATUSES = ['draft', 'sent_to_sri', 'authorized', 'not_authorized', 'canceled']

    @property
    def subtotal(self) -> Decimal:
        return sum(item.subtotal for item in self.items)

    @property
    def tax(self) -> Decimal:
        return self.subtotal * self.vat / 100

    @property
    def total(self) -> Decimal:
        return self.subtotal + self.tax

    def emit(self):
        if self.status != 'draft':
            raise ValueError('Solo se puede emitir una factura en draft')
        self.status = 'sent_to_sri'

    def authorize(self, authorization_number: str, date: str):
        self.authorization_number = authorization_number
        self.authorization_date = date
        self.status = 'authorized'
        self.sri_status = 'AUTORIZADA'

    def cancel(self):
        if self.status == 'canceled':
            raise ValueError('La factura ya estÃ¡ canceled')
        self.status = 'canceled'


# â”€â”€ Credit Note â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@dataclass
class CreditNoteItem:
    description: str
    quantity: Decimal
    unit_price: Decimal
    discount: Decimal = Decimal('0')
    main_code: str = ''
    vat_rate: str = '15'

    @property
    def subtotal(self) -> Decimal:
        base = self.quantity * self.unit_price
        return base - (base * self.discount / 100)


@dataclass
class CreditNote:
    id: int
    tenant_id: int
    number: str
    origin_invoice_number: str
    origin_invoice_key: str
    client: str
    client_identification: str
    client_id_type: str   # 04=RUC, 05=cedula, 07=consumidor final
    reason: str            # devolucion, descuento, anulacion
    date: date
    status: str
    items: List[CreditNoteItem] = field(default_factory=list)
    environment: str = '1'
    access_key: str = ''
    authorization_number: str = ''
    authorization_date: str = ''
    signed_xml: str = ''
    sri_status: str = ''
    sri_message: str = ''

    VALID_STATUSES = ['draft', 'sent_to_sri', 'authorized', 'not_authorized']
    VALID_REASONS = ['return', 'discount', 'cancellation']

    @property
    def subtotal(self) -> Decimal:
        return sum(item.subtotal for item in self.items)

    @property
    def tax(self) -> Decimal:
        return sum(
            item.subtotal * Decimal(item.vat_rate) / 100
            for item in self.items
        )

    @property
    def total(self) -> Decimal:
        return self.subtotal + self.tax

    def authorize(self, authorization_number: str, date: str):
        self.authorization_number = authorization_number
        self.authorization_date = date
        self.status = 'authorized'
        self.sri_status = 'AUTORIZADA'


# â”€â”€ Withholding â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@dataclass
class WithholdingItem:
    type_code: str        # 1=Renta, 2=IVA
    withholding_code: str   # ej. '303', '4x1000'
    tax_base: Decimal
    percentage: Decimal

    @property
    def withheld_value(self) -> Decimal:
        return (self.tax_base * self.percentage / 100).quantize(Decimal('0.01'))


@dataclass
class Withholding:
    id: int
    tenant_id: int
    number: str
    supplier: str
    supplier_identification: str
    supplier_id_type: str     # 04=RUC, 05=cedula
    origin_invoice_number: str
    fiscal_period: str        # MM/AAAA (ej: '07/2026')
    date: date
    status: str
    items: List[WithholdingItem] = field(default_factory=list)
    environment: str = '1'
    access_key: str = ''
    authorization_number: str = ''
    authorization_date: str = ''
    signed_xml: str = ''
    sri_status: str = ''
    sri_message: str = ''

    VALID_STATUSES = ['draft', 'sent_to_sri', 'authorized', 'not_authorized']

    @property
    def total_withheld(self) -> Decimal:
        return sum(item.withheld_value for item in self.items)

    def authorize(self, authorization_number: str, date: str):
        self.authorization_number = authorization_number
        self.authorization_date = date
        self.status = 'authorized'
        self.sri_status = 'AUTORIZADA'


# ── Guía de Remisión (Tipo 06) ────────────────────────────────

@dataclass
class DispatchGuideItem:
    description: str
    quantity: Decimal
    internal_code: str = ''


@dataclass
class DispatchGuide:
    id: int
    tenant_id: int
    number: str
    date_emission: date
    start_date: date
    end_date: date
    starting_address: str
    carrier_ruc: str
    carrier_name: str
    carrier_id_type: str
    vehicle_plate: str
    recipient_id: str
    recipient_id_type: str
    recipient_name: str
    recipient_address: str
    transfer_reason: str = 'Venta'
    route: str = ''
    origin_doc_type: str = '01'
    origin_doc_number: str = ''
    origin_doc_auth: str = ''
    origin_doc_date: Optional[date] = None
    status: str = 'draft'
    items: List[DispatchGuideItem] = field(default_factory=list)
    environment: str = '1'
    access_key: str = ''
    authorization_number: str = ''
    authorization_date: str = ''
    signed_xml: str = ''
    sri_status: str = ''
    sri_message: str = ''

    VALID_STATUSES = ['draft', 'sent_to_sri', 'authorized', 'not_authorized', 'canceled']

    def authorize(self, authorization_number: str, auth_date: str):
        self.authorization_number = authorization_number
        self.authorization_date = auth_date
        self.status = 'authorized'
        self.sri_status = 'AUTORIZADA'


# ── Liquidación de Compra (Tipo 03) ───────────────────────────

@dataclass
class PurchaseSettlementItem:
    description: str
    quantity: Decimal
    unit_price: Decimal
    discount: Decimal = Decimal('0.00')
    vat_rate: str = '15'
    product_code: str = ''

    @property
    def subtotal(self) -> Decimal:
        base = self.quantity * self.unit_price
        return base - self.discount


@dataclass
class PurchaseSettlement:
    id: int
    tenant_id: int
    number: str
    supplier: str
    supplier_identification: str
    supplier_id_type: str  # 05=cédula, 06=pasaporte
    supplier_address: str = ''
    supplier_email: str = ''
    date: date = field(default_factory=date.today)
    payment_method: str = '01'
    status: str = 'draft'
    items: List[PurchaseSettlementItem] = field(default_factory=list)
    notes: str = ''
    environment: str = '1'
    access_key: str = ''
    authorization_number: str = ''
    authorization_date: str = ''
    signed_xml: str = ''
    sri_status: str = ''
    sri_message: str = ''

    VALID_STATUSES = ['draft', 'sent_to_sri', 'authorized', 'not_authorized', 'canceled']

    @property
    def subtotal_0(self) -> Decimal:
        return sum(item.subtotal for item in self.items if str(item.vat_rate) == '0')

    @property
    def subtotal_iva(self) -> Decimal:
        return sum(item.subtotal for item in self.items if str(item.vat_rate) != '0')

    @property
    def total_discount(self) -> Decimal:
        return sum(item.discount for item in self.items)

    @property
    def vat(self) -> Decimal:
        return sum(
            item.subtotal * Decimal(str(item.vat_rate)) / Decimal('100')
            for item in self.items if str(item.vat_rate) != '0'
        )

    @property
    def total(self) -> Decimal:
        return self.subtotal_0 + self.subtotal_iva + self.vat

    def authorize(self, authorization_number: str, auth_date: str):
        self.authorization_number = authorization_number
        self.authorization_date = auth_date
        self.status = 'authorized'
        self.sri_status = 'AUTORIZADA'


