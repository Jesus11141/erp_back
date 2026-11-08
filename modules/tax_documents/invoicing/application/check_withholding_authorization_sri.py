from ..domain.repositories import WithholdingRepository
from ..domain.invoice import Withholding
from ..infrastructure.external_clients.sri_cliente import consultar_autorizacion


class CheckWithholdingAuthorizationSRI:
    """Consulta al SRI la autorización del comprobante de retención electrónico"""
    def __init__(self, withholding_repo: WithholdingRepository):
        self.withholding_repo = withholding_repo

    def execute(self, ret_id: int, tenant_id: int) -> Withholding:
        withholding = self.withholding_repo.find_by_id(ret_id, tenant_id)
        if not withholding:
            raise ValueError('Comprobante de Retención no encontrado')
        if not withholding.access_key:
            raise ValueError('El comprobante de retención no posee clave de acceso')

        result = consultar_autorizacion(withholding.access_key, withholding.environment)

        if result.get('estado') == 'AUTORIZADA':
            withholding.authorize(
                result.get('numero_autorizacion', ''),
                result.get('fecha_autorizacion', ''),
            )
            self.withholding_repo.save(withholding)
        else:
            withholding.sri_status = result.get('estado', '')
            withholding.sri_message = ' | '.join(result.get('messages', []))
            if withholding.status != 'not_authorized':
                withholding.status = 'not_authorized'
            self.withholding_repo.save(withholding)

        return withholding
