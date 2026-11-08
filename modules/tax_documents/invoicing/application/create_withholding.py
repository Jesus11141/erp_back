from decimal import Decimal
from datetime import date, datetime
from ..domain.repositories import WithholdingRepository
from ..domain.invoice import Withholding, WithholdingItem
from ..infrastructure.external_clients.sri_xml_retencion import generate_access_key_retencion
from .exceptions import BusinessError


class CreateWithholding:
    def __init__(self, withholding_repo: WithholdingRepository):
        self.withholding_repo = withholding_repo

    def execute(self, tenant_id: int, data: dict, issuer: dict) -> Withholding:
        estab = issuer.get('establecimiento')
        pto = issuer.get('punto_emision')
        if not estab:
            raise BusinessError('El parámetro "establecimiento" no está configurado en el sistema.', field='establecimiento', code='CONFIG_MISSING')
        if not pto:
            raise BusinessError('El parámetro "punto_emision" no está configurado en el sistema.', field='punto_emision', code='CONFIG_MISSING')

        supplier = data.get('supplier', '').strip()
        supplier_id = data.get('supplier_identification', '').strip()
        if not supplier:
            raise BusinessError('El nombre o razón social del proveedor es obligatorio.', field='supplier')
        if not supplier_id:
            raise BusinessError('La identificación del proveedor es obligatoria.', field='supplier_identification')

        supplier_id_type = data.get('supplier_id_type', '04')
        if len(supplier_id) == 10 and supplier_id_type not in ('05', '06'):
            supplier_id_type = '05'
        elif len(supplier_id) == 13 and supplier_id_type not in ('04', '06'):
            supplier_id_type = '04'

        raw_items = data.get('items', [])
        if not raw_items:
            raise BusinessError('Debe agregar al menos un impuesto de retención (Renta o IVA).', field='items')

        # 1. Obtener siguiente secuencial de retención
        number = self.withholding_repo.next_number(tenant_id, estab, pto, document_type='07')

        # 2. Formatear fecha y período fiscal
        doc_date = data.get('date')
        if isinstance(doc_date, str):
            doc_date = datetime.strptime(doc_date[:10], '%Y-%m-%d').date()
        elif not doc_date:
            doc_date = date.today()

        # Control de Período Contable / Cierre Fiscal
        from modules.contabilidad.application.period_service import validate_accounting_period
        validate_accounting_period(tenant_id, doc_date, action_desc='emitir retenciones electrónicas')

        fiscal_period = data.get('fiscal_period')
        if not fiscal_period:
            fiscal_period = f"{doc_date.month:02d}/{doc_date.year}"

        items = []
        for i in raw_items:
            tax_base = Decimal(str(i.get('tax_base', 0)))
            pct = Decimal(str(i.get('percentage', 0)))
            if tax_base <= 0:
                raise BusinessError('La base imponible debe ser mayor a cero.', field='tax_base')
            
            items.append(WithholdingItem(
                type_code=str(i.get('type_code', '1')),
                withholding_code=str(i.get('withholding_code', '303')),
                tax_base=tax_base,
                percentage=pct,
            ))

        environment = issuer.get('environment', '1')
        withholding = Withholding(
            id=0,
            tenant_id=tenant_id,
            number=number,
            supplier=supplier,
            supplier_identification=supplier_id,
            supplier_id_type=supplier_id_type,
            origin_invoice_number=data.get('origin_invoice_number', '').strip(),
            fiscal_period=fiscal_period,
            date=doc_date,
            status='draft',
            items=items,
            environment=environment,
        )

        # 3. Generar clave de acceso SRI oficial para tipo 07
        withholding.access_key = generate_access_key_retencion(
            fecha=withholding.date.strftime('%d/%m/%Y'),
            ruc=issuer.get('ruc', ''),
            environment=environment,
            serie=f"{estab}{pto}",
            secuencial=number.split('-')[-1],
        )

        return self.withholding_repo.save(withholding)
