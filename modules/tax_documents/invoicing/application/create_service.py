from decimal import Decimal
from datetime import date
from ..domain.repositories import InvoiceRepository
from ..domain.invoice import Invoice, InvoiceItem
from ..infrastructure.external_clients.sri_xml import generate_access_key
from .exceptions import BusinessError

class CreateInvoice:
    def __init__(self, repo: InvoiceRepository):
        self.repo = repo

    def execute(self, tenant_id: int, data: dict, issuer: dict, vat=12, document_type='01') -> Invoice:
        """Crea una nueva factura en estado borrador y genera su clave de acceso.

        Args:
            tenant_id (int): El identificador del inquilino (tenant) de la base de datos.
            data (dict): Los datos de la petición, incluyendo cliente y los items a facturar.
            issuer (dict): Las configuraciones del emisor (establecimiento, punto_emision, ruc, etc.).
            vat (int, optional): El porcentaje del IVA a aplicar. Por defecto es 12.

        Returns:
            Invoice: La entidad factura creada y guardada en el repositorio.

        Raises:
            BusinessError: Si los parámetros 'establecimiento' o 'punto_emision' no existen en la configuración del emisor.
        """
        import re
        raw_estab = str(issuer.get('establecimiento') or '')
        raw_pto = str(issuer.get('punto_emision') or '')
        
        # Extraer solo números para evitar ValueError: invalid literal for int() si el usuario escribió "Caja A"
        estab_digits = re.sub(r'\D', '', raw_estab)
        pto_digits = re.sub(r'\D', '', raw_pto)
        
        estab = estab_digits.rjust(3, '0')[-3:] if estab_digits else '001'
        pto = pto_digits.rjust(3, '0')[-3:] if pto_digits else '001'
        
        if estab == '000':
            raise BusinessError('El parámetro "establecimiento" no está configurado en el sistema.', field='establecimiento', code='CONFIG_MISSING')
        if pto == '000':
            raise BusinessError('El parámetro "punto_emision" no está configurado en el sistema.', field='punto_emision', code='CONFIG_MISSING')

        target_date = data.get('date') or date.today()
        user_role = data.get('user_role', 'vendedor')
        from modules.contabilidad.application.period_service import validate_accounting_period
        validate_accounting_period(tenant_id, target_date, user_role=user_role, action_desc='emitir facturas de venta')

        number = self.repo.next_number(
            tenant_id,
            estab,
            pto,
            document_type=document_type
        )
        items = [
            InvoiceItem(
                description=i['description'],
                quantity=Decimal(str(i['quantity'])),
                unit_price=Decimal(str(i['unit_price'])),
                discount=Decimal(str(i.get('discount', 0))),
                main_code=i.get('main_code', ''),
                auxiliary_code=i.get('auxiliary_code', ''),
                vat_rate=str(i.get('vat_rate', '15')),
            ) for i in data.get('items', [])
        ]
        environment = issuer.get('environment', '1')
        invoice = Invoice(
            id=0,
            tenant_id=tenant_id,
            document_type=document_type,
            number=number,
            client=data.get('client') or ('CONSUMIDOR FINAL' if data.get('client_id_type') == '07' else 'CLIENTE'),
            client_identification=data.get('client_identification') or ('9999999999999' if data.get('client_id_type') == '07' else '9999999999999'),
            client_id_type=data.get('client_id_type', '07'),
            client_address=data.get('client_address') or 'S/N',
            client_email=data.get('client_email') or '',
            date=date.today(),
            status='draft',
            items=items,
            vat=Decimal(str(vat)),
            payment_method=data.get('payment_method', '01'),
            notes=data.get('notes', ''),
            environment=environment,
        )
        # Generar clave de acceso
        invoice.access_key = generate_access_key(
            fecha=invoice.date.strftime('%d/%m/%Y'),
            ruc=issuer.get('ruc', ''),
            environment=environment,
            serie=f"{estab}{pto}",
            secuencial=number.split('-')[-1],
        )
        return self.repo.save(invoice)
