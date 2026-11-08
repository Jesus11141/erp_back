from abc import ABC, abstractmethod
from typing import List, Optional
from .entities import (
    Proveedor, OrdenCompra, FacturaCompra, CuentaPagar, AbonoCuentaPagar
)


class ProveedorRepository(ABC):
    @abstractmethod
    def save(self, proveedor: Proveedor) -> Proveedor: pass

    @abstractmethod
    def find_by_id(self, proveedor_id: int, tenant_id: int) -> Optional[Proveedor]: pass

    @abstractmethod
    def find_by_identification(self, identification: str, tenant_id: int) -> Optional[Proveedor]: pass

    @abstractmethod
    def list(self, tenant_id: int, query: str = None) -> List[Proveedor]: pass

    @abstractmethod
    def delete(self, proveedor_id: int, tenant_id: int) -> bool: pass


class OrdenCompraRepository(ABC):
    @abstractmethod
    def save(self, orden: OrdenCompra) -> OrdenCompra: pass

    @abstractmethod
    def find_by_id(self, orden_id: int, tenant_id: int) -> Optional[OrdenCompra]: pass

    @abstractmethod
    def list(self, tenant_id: int, status: str = None) -> List[OrdenCompra]: pass


class FacturaCompraRepository(ABC):
    @abstractmethod
    def save(self, factura: FacturaCompra) -> FacturaCompra: pass

    @abstractmethod
    def find_by_id(self, factura_id: int, tenant_id: int) -> Optional[FacturaCompra]: pass

    @abstractmethod
    def list(self, tenant_id: int) -> List[FacturaCompra]: pass


class CuentaPagarRepository(ABC):
    @abstractmethod
    def save(self, cuenta: CuentaPagar) -> CuentaPagar: pass

    @abstractmethod
    def find_by_id(self, cuenta_id: int, tenant_id: int) -> Optional[CuentaPagar]: pass

    @abstractmethod
    def list(self, tenant_id: int, status: str = None) -> List[CuentaPagar]: pass

    @abstractmethod
    def add_payment(self, abono: AbonoCuentaPagar) -> AbonoCuentaPagar: pass

    @abstractmethod
    def list_payments(self, cuenta_id: int, tenant_id: int) -> List[AbonoCuentaPagar]: pass
