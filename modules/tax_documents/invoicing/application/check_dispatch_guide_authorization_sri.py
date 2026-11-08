from ..domain.repositories import DispatchGuideRepository
from ..domain.invoice import DispatchGuide
from ..infrastructure.external_clients.sri_cliente import consultar_autorizacion


class CheckDispatchGuideAuthorizationSRI:
    """Consulta al SRI la autorización de la Guía de Remisión electrónica"""
    def __init__(self, guide_repo: DispatchGuideRepository):
        self.guide_repo = guide_repo

    def execute(self, guide_id: int, tenant_id: int) -> DispatchGuide:
        guide = self.guide_repo.find_by_id(guide_id, tenant_id)
        if not guide:
            raise ValueError('Guía de Remisión no encontrada')
        if not guide.access_key:
            raise ValueError('La guía de remisión no posee clave de acceso')

        result = consultar_autorizacion(guide.access_key, guide.environment)

        if result.get('estado') == 'AUTORIZADA':
            guide.authorize(
                result.get('numero_autorizacion', ''),
                result.get('fecha_autorizacion', ''),
            )
            self.guide_repo.save(guide)
        else:
            guide.sri_status = result.get('estado', '')
            guide.sri_message = ' | '.join(result.get('messages', []))
            if guide.status != 'not_authorized':
                guide.status = 'not_authorized'
            self.guide_repo.save(guide)

        return guide
