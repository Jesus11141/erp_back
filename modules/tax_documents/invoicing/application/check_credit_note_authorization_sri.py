from ..domain.repositories import CreditNoteRepository
from ..domain.invoice import CreditNote
from ..infrastructure.external_clients.sri_cliente import consultar_autorizacion

class CheckCreditNoteAuthorizationSRI:
    def __init__(self, nc_repo: CreditNoteRepository, producto_repo=None, movimiento_repo=None):
        self.nc_repo = nc_repo
        self.producto_repo = producto_repo
        self.movimiento_repo = movimiento_repo

    def execute(self, nc_id: int, tenant_id: int) -> CreditNote:
        nc = self.nc_repo.find_by_id(nc_id, tenant_id)
        if not nc:
            raise ValueError('Nota de CrÃ©dito no encontrada')
        if not nc.access_key:
            raise ValueError('La Nota de CrÃ©dito no tiene clave de acceso')

        result = consultar_autorizacion(nc.access_key, nc.environment)

        if result['estado'] == 'AUTORIZADA':
            nc.authorize(
                result['numero_autorizacion'],
                result['fecha_autorizacion'],
            )
            self.nc_repo.save(nc)

            # Si el motivo es devoluciÃ³n o anulaciÃ³n, devolvemos el stock al inventario
            if nc.reason in ['return', 'cancellation'] and self.producto_repo and self.movimiento_repo:
                from modules.inventario.application.use_cases import AdjustStock
                for item in nc.items:
                    if not item.main_code:
                        continue
                    producto = self.producto_repo.find_by_code(item.main_code, tenant_id)
                    if producto:
                        try:
                            AdjustStock(self.producto_repo, self.movimiento_repo).execute(
                                tenant_id=tenant_id,
                                product_id=producto.id,
                                quantity=item.quantity,
                                type='in',
                                reference=f'DevoluciÃ³n Nota CrÃ©dito {nc.number}',
                                user_id=0,
                            )
                        except ValueError:
                            pass
        else:
            nc.sri_status = result['estado']
            nc.sri_message = ' | '.join(result.get('messages', []))
            if nc.status != 'not_authorized':
                nc.status = 'not_authorized'
            self.nc_repo.save(nc)

        return nc

