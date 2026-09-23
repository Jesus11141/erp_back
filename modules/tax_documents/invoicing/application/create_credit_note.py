from decimal import Decimal
from datetime import date
from ..domain.repositories import InvoiceRepository, CreditNoteRepository
from ..domain.invoice import CreditNote, CreditNoteItem
from ..infrastructure.external_clients.sri_xml_nota_credito import generate_access_key_nota_credito
from .exceptions import BusinessError

class CreateCreditNote:
    def __init__(self, nc_repo: CreditNoteRepository, factura_repo: InvoiceRepository):
        self.nc_repo = nc_repo
        self.factura_repo = factura_repo

    def execute(self, tenant_id: int, data: dict, issuer: dict) -> CreditNote:
        invoice = self.factura_repo.find_by_id(data['invoice_id'], tenant_id)
        if not invoice:
            raise ValueError("Factura de origen no encontrada")

        if invoice.status != 'authorized':
            raise BusinessError("Solo se puede emitir una Nota de Crédito sobre una factura autorizada ante el SRI", code='INVALID_STATUS')

        estab = issuer.get('establecimiento')
        pto = issuer.get('punto_emision')
        if not estab:
            raise BusinessError('El parÃ¡metro "establecimiento" no estÃ¡ configurado en el sistema.', field='establecimiento', code='CONFIG_MISSING')
        if not pto:
            raise BusinessError('El parÃ¡metro "punto_emision" no estÃ¡ configurado en el sistema.', field='punto_emision', code='CONFIG_MISSING')

        # 1. Obtener siguiente nÃºmero secuencial
        number = self.nc_repo.next_number(
            tenant_id,
            estab,
            pto,
        )

        items = [
            CreditNoteItem(
                description=i['description'],
                quantity=Decimal(str(i['quantity'])),
                unit_price=Decimal(str(i['unit_price'])),
                discount=Decimal(str(i.get('discount', 0))),
                main_code=i.get('main_code', ''),
                vat_rate=i.get('vat_rate', '15'),
            ) for i in data.get('items', [])
        ]

        environment = issuer.get('environment', '1')
        credit_note = CreditNote(
            id=0,
            tenant_id=tenant_id,
            number=number,
            origin_invoice_number=invoice.number,
            origin_invoice_key=invoice.access_key,
            client=invoice.client,
            client_identification=invoice.client_identification,
            client_id_type=invoice.client_id_type,
            reason=data.get('reason', 'void'),
            date=date.today(),
            status='draft',
            items=items,
            environment=environment,
        )

        # 2. Generar clave de acceso
        credit_note.access_key = generate_access_key_nota_credito(
            fecha=credit_note.date.strftime('%d/%m/%Y'),
            ruc=issuer.get('ruc', ''),
            environment=environment,
            serie=f"{estab}{pto}",
            secuencial=number.split('-')[-1],
        )

        return self.nc_repo.save(credit_note)

