from abc import ABC, abstractmethod
from typing import Optional, List
from decimal import Decimal
from .entities import CashRegister, POSSale, POSSaleItem, CashRegisterClosure, POSCustomer, CashRegisterMovement

class CashRegisterRepository(ABC):
    @abstractmethod
    def save(self, register: CashRegister) -> CashRegister:
        pass

    @abstractmethod
    def get_by_id(self, register_id: int, tenant_id: int) -> Optional[CashRegister]:
        pass

    @abstractmethod
    def get_open_register(self, tenant_id: int, user_id: int) -> Optional[CashRegister]:
        pass

    @abstractmethod
    def save_closure(self, closure: CashRegisterClosure) -> CashRegisterClosure:
        pass

    @abstractmethod
    def has_active_physical_registers(self, tenant_id: int) -> bool:
        pass

    @abstractmethod
    def save_movement(self, movement: CashRegisterMovement) -> CashRegisterMovement:
        pass

    @abstractmethod
    def get_movements_by_register(self, register_id: int, tenant_id: int) -> List[CashRegisterMovement]:
        pass

class POSSaleRepository(ABC):
    @abstractmethod
    def save(self, sale: POSSale) -> POSSale:
        pass

    @abstractmethod
    def get_by_id(self, sale_id: int, tenant_id: int) -> Optional[POSSale]:
        pass

    @abstractmethod
    def list_by_register(self, register_id: int, tenant_id: int) -> List[POSSale]:
        pass

    @abstractmethod
    def get_sales_totals_by_register(self, register_id: int) -> dict:
        pass

class POSDependencyRepository(ABC):
    @abstractmethod
    def has_active_employees(self, tenant_id: int) -> bool:
        pass

    @abstractmethod
    def ensure_customer_exists(self, tenant_id: int, customer: POSCustomer) -> None:
        pass

class POSInventoryService(ABC):
    @abstractmethod
    def adjust_stock(self, tenant_id: int, product_id: int, quantity: Decimal, type: str, reference: str, user_id: int, branch_id: Optional[int] = None) -> None:
        pass

    @abstractmethod
    def get_stock_available(self, tenant_id: int, product_id: int, branch_id: Optional[int] = None) -> Decimal:
        pass

    @abstractmethod
    def get_product_details(self, tenant_id: int, product_id: int) -> dict:
        pass

class POSBillingService(ABC):
    @abstractmethod
    def get_issuer(self, tenant_id: int) -> dict:
        pass

    @abstractmethod
    def create_invoice(self, tenant_id: int, customer: POSCustomer, items: List[POSSaleItem], sale_id: int, issuer: dict, vat_rate: Decimal, document_type: str = '01') -> dict:
        pass

    @abstractmethod
    def emit_invoice(self, tenant_id: int, invoice_id: int, issuer: dict) -> None:
        pass

class POSAccountingService(ABC):
    @abstractmethod
    def register_sale_entry(self, tenant_id: int, sale: POSSale) -> None:
        pass
