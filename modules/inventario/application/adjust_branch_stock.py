from decimal import Decimal
from datetime import datetime
from ..domain.entities import Product, StockMovement
from ..domain.repositories import ProductRepository, StockMovementRepository, BranchStockRepository, KardexRepository


class AdjustBranchStock:
    def __init__(self, branch_stock_repo: BranchStockRepository, product_repo=None, movement_repo=None):
        self.branch_stock_repo = branch_stock_repo
        self.product_repo = product_repo
        self.movement_repo = movement_repo

    def execute(self, tenant_id: int, product_id: int, branch_id: int,
                 quantity: Decimal, type: str, reference: str = '', user_id: int = 0, allow_negative: bool = False) -> Decimal:
        new_stock = self.branch_stock_repo.adjust_branch_stock(
            tenant_id=tenant_id,
            product_id=product_id,
            branch_id=branch_id,
            quantity=quantity,
            type=type,
            allow_negative=allow_negative
        )
        return new_stock

