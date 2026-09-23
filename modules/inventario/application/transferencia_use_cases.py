from decimal import Decimal
from modules.parametros.domain.repositories import ParameterRepository
from ..domain.repositories import StockTransferRepository

class TransferStockBetweenBranches:
    def __init__(self, transfer_repo: StockTransferRepository, param_repo: ParameterRepository = None, movement_repo = None):
        self.transfer_repo = transfer_repo
        self.param_repo = param_repo
        self.movement_repo = movement_repo

    def execute(self, tenant_id: int, product_id: int, source_branch_id: int,
                destination_branch_id: int, quantity: Decimal, user_id: int,
                observations: str = '') -> dict:
        if self.param_repo:
            param_multi = self.param_repo.get(tenant_id, 'inventario', 'permitir_movimiento_locales')
            multi_active = param_multi.value.lower() == 'true' if param_multi else False
            if not multi_active:
                raise ValueError("La parametrizaciÃ³n de movimientos entre locales estÃ¡ desactivada para esta empresa")

        if source_branch_id == destination_branch_id:
            raise ValueError("La sucursal de origen y destino no pueden ser la misma")

        if quantity <= 0:
            raise ValueError("La cantidad a transferir debe ser mayor a cero")

        return self.transfer_repo.transfer_stock(
            tenant_id=tenant_id,
            product_id=product_id,
            source_branch_id=source_branch_id,
            destination_branch_id=destination_branch_id,
            quantity=quantity,
            user_id=user_id,
            observations=observations
        )

