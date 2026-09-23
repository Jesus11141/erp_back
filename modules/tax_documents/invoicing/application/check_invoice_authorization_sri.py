from ..domain.repositories import InvoiceRepository
from ..domain.invoice import Invoice
from ..infrastructure.external_clients.sri_cliente import consultar_autorizacion

class CheckInvoiceAuthorizationSRI:
    """Consulta si el SRI ya autorizÃ³ el comprobante"""
    def __init__(self, repo: InvoiceRepository):
        self.repo = repo

    def execute(self, invoice_id: int, tenant_id: int) -> Invoice:
        invoice = self.repo.find_by_id(invoice_id, tenant_id)
        if not invoice:
            raise ValueError('Factura no encontrada')
        if not invoice.access_key:
            raise ValueError('La factura no tiene clave de acceso')

        result = consultar_autorizacion(invoice.access_key, invoice.environment)

        if result['estado'] in ('AUTORIZADO', 'AUTORIZADA'):
            invoice.authorize(
                result['numero_autorizacion'],
                result['fecha_autorizacion'],
            )
        else:
            invoice.sri_status = result['estado']
            invoice.sri_message = ' | '.join(result.get('messages', []))
            if invoice.status != 'not_authorized':
                invoice.status = 'not_authorized'

        return self.repo.save(invoice)

