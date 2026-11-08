from abc import ABC, abstractmethod
from typing import Optional, List
from .invoice import Invoice, CreditNote, Withholding, DispatchGuide, PurchaseSettlement

class InvoiceRepository(ABC):
    @abstractmethod
    def save(self, invoice: Invoice) -> Invoice:
        pass

    @abstractmethod
    def find_by_id(self, id: int, tenant_id: int) -> Optional[Invoice]:
        pass

    @abstractmethod
    def list_by_tenant(self, tenant_id: int, page: int = 1, limit: int = 10) -> dict:
        pass

    @abstractmethod
    def next_number(self, tenant_id: int, estab: str = '001', pto_emi: str = '001', document_type: str = '01') -> str:
        pass


class CreditNoteRepository(ABC):
    @abstractmethod
    def save(self, credit_note: CreditNote) -> CreditNote:
        pass

    @abstractmethod
    def find_by_id(self, id: int, tenant_id: int) -> Optional[CreditNote]:
        pass

    @abstractmethod
    def list_by_tenant(self, tenant_id: int) -> List[CreditNote]:
        pass

    @abstractmethod
    def next_number(self, tenant_id: int, estab: str = '001', pto_emi: str = '001', document_type: str = '04') -> str:
        pass


class WithholdingRepository(ABC):
    @abstractmethod
    def save(self, withholding: Withholding) -> Withholding:
        pass

    @abstractmethod
    def find_by_id(self, id: int, tenant_id: int) -> Optional[Withholding]:
        pass

    @abstractmethod
    def list_by_tenant(self, tenant_id: int) -> List[Withholding]:
        pass

    @abstractmethod
    def next_number(self, tenant_id: int, estab: str = '001', pto_emi: str = '001', document_type: str = '07') -> str:
        pass


class DispatchGuideRepository(ABC):
    @abstractmethod
    def save(self, guide: DispatchGuide) -> DispatchGuide:
        pass

    @abstractmethod
    def find_by_id(self, id: int, tenant_id: int) -> Optional[DispatchGuide]:
        pass

    @abstractmethod
    def list_by_tenant(self, tenant_id: int) -> List[DispatchGuide]:
        pass

    @abstractmethod
    def next_number(self, tenant_id: int, estab: str = '001', pto_emi: str = '001', document_type: str = '06') -> str:
        pass


class PurchaseSettlementRepository(ABC):
    @abstractmethod
    def save(self, settlement: PurchaseSettlement) -> PurchaseSettlement:
        pass

    @abstractmethod
    def find_by_id(self, id: int, tenant_id: int) -> Optional[PurchaseSettlement]:
        pass

    @abstractmethod
    def list_by_tenant(self, tenant_id: int) -> List[PurchaseSettlement]:
        pass

    @abstractmethod
    def next_number(self, tenant_id: int, estab: str = '001', pto_emi: str = '001', document_type: str = '03') -> str:
        pass

