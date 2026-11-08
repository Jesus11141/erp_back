from ..domain.repositories import PurchaseSettlementRepository
from ..domain.invoice import PurchaseSettlement
from ..infrastructure.external_clients.sri_cliente import consultar_autorizacion


class CheckPurchaseSettlementAuthorizationSRI:
    """Consulta al SRI la autorización de la Liquidación de Compra electrónica"""
    def __init__(self, settlement_repo: PurchaseSettlementRepository):
        self.settlement_repo = settlement_repo

    def execute(self, settlement_id: int, tenant_id: int) -> PurchaseSettlement:
        settlement = self.settlement_repo.find_by_id(settlement_id, tenant_id)
        if not settlement:
            raise ValueError('Liquidación de Compra no encontrada')
        if not settlement.access_key:
            raise ValueError('La liquidación de compra no posee clave de acceso')

        result = consultar_autorizacion(settlement.access_key, settlement.environment)

        if result.get('estado') == 'AUTORIZADA':
            settlement.authorize(
                result.get('numero_autorizacion', ''),
                result.get('fecha_autorizacion', ''),
            )
            self.settlement_repo.save(settlement)
        else:
            settlement.sri_status = result.get('estado', '')
            settlement.sri_message = ' | '.join(result.get('messages', []))
            if settlement.status != 'not_authorized':
                settlement.status = 'not_authorized'
            self.settlement_repo.save(settlement)

        return settlement
