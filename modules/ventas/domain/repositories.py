from abc import ABC, abstractmethod
from typing import Optional, List
from .entities import Customer, Quotation, Order

class CustomerRepository(ABC):
    @abstractmethod
    def save(self, customer: Customer) -> Customer: pass
    
    @abstractmethod
    def find_by_id(self, id: int, tenant_id: int) -> Optional[Customer]: pass
    
    @abstractmethod
    def list_by_tenant(self, tenant_id: int) -> List[Customer]: pass
    
    @abstractmethod
    def find_by_name(self, name: str, tenant_id: int) -> List[Customer]: pass

class QuotationRepository(ABC):
    @abstractmethod
    def save(self, quotation: Quotation) -> Quotation: pass
    
    @abstractmethod
    def find_by_id(self, id: int, tenant_id: int) -> Optional[Quotation]: pass
    
    @abstractmethod
    def list_by_tenant(self, tenant_id: int) -> List[Quotation]: pass
    
    @abstractmethod
    def next_number(self, tenant_id: int) -> str: pass

class OrderRepository(ABC):
    @abstractmethod
    def delete(self, order_id: int):
        pass

class PaymentMethodRepository(ABC):
    @abstractmethod
    def save(self, p: 'PaymentMethod') -> 'PaymentMethod':
        pass
    @abstractmethod
    def find_all(self, tenant_id: int, include_inactive: bool = False) -> List['PaymentMethod']:
        pass
    @abstractmethod
    def delete(self, method_id: int, tenant_id: int):
        pass
    @abstractmethod
    def find_by_id(self, id: int, tenant_id: int) -> Optional['PaymentMethod']: pass

class AccountReceivableRepository(ABC):
    @abstractmethod
    def save(self, ar: 'AccountReceivable') -> 'AccountReceivable': pass
    
    @abstractmethod
    def find_by_id(self, id: int, tenant_id: int) -> Optional['AccountReceivable']: pass
    
    @abstractmethod
    def list_by_tenant(self, tenant_id: int) -> List['AccountReceivable']: pass

    @abstractmethod
    def find_by_reference(self, reference_type: str, reference_id: int, tenant_id: int) -> Optional['AccountReceivable']: pass
    
    @abstractmethod
    def add_payment(self, payment: 'ReceivablePayment') -> 'ReceivablePayment': pass
    
    @abstractmethod
    def get_payments(self, account_receivable_id: int) -> List['ReceivablePayment']: pass
