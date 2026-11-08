from ..domain.repositories import InvoiceRepository
from ..domain.invoice import Invoice

class CancelInvoice:
    def __init__(self, repo: InvoiceRepository, producto_repo=None, movimiento_repo=None):
        self.repo = repo
        self.producto_repo = producto_repo
        self.movimiento_repo = movimiento_repo

    def execute(self, invoice_id: int, tenant_id: int) -> Invoice:
        invoice = self.repo.find_by_id(invoice_id, tenant_id)
        if not invoice:
            raise ValueError('Factura no encontrada')

        # Control de Período Contable / Cierre Fiscal
        from modules.contabilidad.application.period_service import validate_accounting_period
        validate_accounting_period(tenant_id, invoice.date, action_desc='anular facturas de venta')

        # Control Tributario: Validar vigencia en el SRI
        if invoice.access_key:
            from modules.tax_documents.invoicing.infrastructure.external_clients.sri_cliente import consultar_autorizacion
            try:
                res = consultar_autorizacion(invoice.access_key, invoice.environment)
                if res['estado'] == 'AUTORIZADA':
                    raise ValueError("La factura se encuentra autorizada, anule en el SRI y vuelva a intentarlo")
            except ValueError as e:
                raise e
            except Exception as e:
                # Si hay error de red o timeout, bloqueamos por seguridad fiscal
                raise ValueError(f"Error de conexiÃ³n con el SRI: {str(e)}. AnulaciÃ³n bloqueada para evitar descuadres fiscales.")

        estado_anterior = invoice.status
        invoice.cancel()
        self.repo.save(invoice)

        # Siempre devolver stock si la factura se anula, ya que POS lo descuenta al crearla
        # sin importar si llegó a autorizarse en el SRI o se quedó en borrador.
        if estado_anterior != 'canceled' and self.producto_repo and self.movimiento_repo:
            from modules.inventario.application.use_cases import AdjustStock
            for item in invoice.items:
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
                            reference=f'AnulaciÃ³n factura {invoice.number}',
                            user_id=0,
                        )
                    except ValueError:
                        pass

        return invoice

