from decimal import Decimal
from datetime import datetime
from ..domain.entities import Product, StockMovement
from ..domain.repositories import ProductRepository, StockMovementRepository, BranchStockRepository, KardexRepository


class ListProducts:
    def __init__(self, repo: ProductRepository):
        self.repo = repo

    def execute(self, tenant_id: int, query: str = None, low_stock: bool = False) -> list:
        if low_stock:
            return self.repo.list_low_stock(tenant_id)
        if query:
            return self.repo.search(query, tenant_id)
        return self.repo.list_by_tenant(tenant_id)



