from abc import ABC, abstractmethod
from typing import Optional, List
from decimal import Decimal
from .entities import Product, Category, StockMovement

class ProductRepository(ABC):
    @abstractmethod
    def save(self, product: Product) -> Product: pass
    @abstractmethod
    def find_by_id(self, id: int, tenant_id: int) -> Optional[Product]: pass
    @abstractmethod
    def find_by_code(self, code: str, tenant_id: int) -> Optional[Product]: pass
    @abstractmethod
    def list_by_tenant(self, tenant_id: int) -> List[Product]: pass
    @abstractmethod
    def list_low_stock(self, tenant_id: int) -> List[Product]: pass
    @abstractmethod
    def search(self, query: str, tenant_id: int) -> List[Product]: pass

class StockMovementRepository(ABC):
    @abstractmethod
    def register(self, movement: StockMovement) -> StockMovement: pass
    @abstractmethod
    def list_by_product(self, product_id: int, tenant_id: int) -> List[StockMovement]: pass

class VolumeDiscountRuleRepository(ABC):
    @abstractmethod
    def list_product_tiers(self, tenant_id: int, product_id: int) -> List[dict]: pass
    @abstractmethod
    def find_applicable_rule(self, tenant_id: int, product_id: int, quantity: float) -> Optional[dict]: pass

class KardexRepository(ABC):
    @abstractmethod
    def register(self, tenant_id: int, product_id: int, type: str, quantity: Decimal,
                 unit_cost: Decimal = None, reference: str = '', user_id: int = 0) -> dict: pass

class BranchStockRepository(ABC):
    @abstractmethod
    def adjust_branch_stock(self, tenant_id: int, product_id: int, branch_id: int,
                            quantity: Decimal, type: str, allow_negative: bool = False) -> Decimal:
        pass
    @abstractmethod
    def get_stock(self, tenant_id: int, product_id: int, branch_id: int) -> Decimal: pass

class StockTransferRepository(ABC):
    @abstractmethod
    def transfer_stock(self, tenant_id: int, product_id: int, source_branch_id: int,
                        destination_branch_id: int, quantity: Decimal, user_id: int,
                        observations: str = '') -> dict: pass
