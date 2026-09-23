from decimal import Decimal
from ..domain.repositories import KardexRepository

class RegisterKardexWAC:
    def __init__(self, repo: KardexRepository):
        self.repo = repo

    def execute(self, tenant_id: int, product_id: int, type: str, quantity: Decimal,
                unit_cost: Decimal = None, reference: str = '', user_id: int = 0) -> dict:
        return self.repo.register(
            tenant_id=tenant_id,
            product_id=product_id,
            type=type,
            quantity=quantity,
            unit_cost=unit_cost,
            reference=reference,
            user_id=user_id
        )
