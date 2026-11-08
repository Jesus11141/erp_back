from decimal import Decimal
from datetime import date, datetime
from ..domain.repositories import PurchaseSettlementRepository
from ..domain.invoice import PurchaseSettlement, PurchaseSettlementItem
from ..infrastructure.external_clients.sri_xml_liquidacion_compra import generate_access_key_liquidacion
from .exceptions import BusinessError


class CreatePurchaseSettlement:
    def __init__(self, settlement_repo: PurchaseSettlementRepository):
        self.settlement_repo = settlement_repo

    def execute(self, tenant_id: int, data: dict, issuer: dict) -> PurchaseSettlement:
        estab = issuer.get('establecimiento')
        pto = issuer.get('punto_emision')
        if not estab:
            raise BusinessError('El parámetro "establecimiento" no está configurado en el sistema.', field='establecimiento', code='CONFIG_MISSING')
        if not pto:
            raise BusinessError('El parámetro "punto_emision" no está configurado en el sistema.', field='punto_emision', code='CONFIG_MISSING')

        supplier = data.get('supplier', '').strip()
        supplier_id = data.get('supplier_identification', '').strip()
        supplier_address = data.get('supplier_address', '').strip()
        supplier_email = data.get('supplier_email', '').strip()

        if not supplier:
            raise BusinessError('La razón social o nombre del proveedor es obligatorio.', field='supplier')
        if not supplier_id:
            raise BusinessError('La identificación del proveedor es obligatoria.', field='supplier_identification')

        supplier_id_type = data.get('supplier_id_type', '05').strip()

        # Validación SRI estricta: Liquidación de compra NO se puede emitir a poseedores de RUC
        if len(supplier_id) == 13 or supplier_id_type == '04':
            raise BusinessError(
                'Las Liquidaciones de Compra únicamente se pueden emitir a personas naturales sin RUC (cédula o pasaporte). Si el proveedor tiene RUC, debe emitir una Factura.',
                field='supplier_identification'
            )

        if len(supplier_id) == 10 and supplier_id_type != '06':
            supplier_id_type = '05'
        elif len(supplier_id) != 10 and supplier_id_type != '06':
            # Si no es cédula de 10 dígitos ni pasaporte explícito
            if len(supplier_id) < 3:
                raise BusinessError('Identificación de proveedor inválida.', field='supplier_identification')

        raw_items = data.get('items', [])
        if not raw_items:
            raise BusinessError('Debe agregar al menos un ítem o servicio a la liquidación de compra.', field='items')

        # Fecha de emisión
        doc_date = data.get('date')
        if isinstance(doc_date, str) and len(doc_date) >= 10:
            doc_date = datetime.strptime(doc_date[:10], '%Y-%m-%d').date()
        elif isinstance(doc_date, datetime):
            doc_date = doc_date.date()
        elif not doc_date:
            doc_date = date.today()

        # Control de Período Contable / Cierre Fiscal
        from modules.contabilidad.application.period_service import validate_accounting_period
        validate_accounting_period(tenant_id, doc_date, action_desc='emitir liquidaciones de compra')

        # Secuencial oficial tipo 03
        number = self.settlement_repo.next_number(tenant_id, estab, pto, document_type='03')

        items = []
        for i in raw_items:
            desc = i.get('description', '').strip()
            if not desc:
                raise BusinessError('La descripción del ítem es obligatoria.', field='items')
            qty = Decimal(str(i.get('quantity', 1)))
            price = Decimal(str(i.get('unit_price', 0)))
            disc = Decimal(str(i.get('discount', 0)))
            vat_rate = str(i.get('vat_rate', '15')).strip()

            if qty <= 0:
                raise BusinessError('La cantidad debe ser mayor a cero.', field='items')
            if price < 0:
                raise BusinessError('El precio unitario no puede ser negativo.', field='items')

            items.append(PurchaseSettlementItem(
                description=desc,
                quantity=qty,
                unit_price=price,
                discount=disc,
                vat_rate=vat_rate,
                product_code=i.get('product_code', '').strip()
            ))

        environment = issuer.get('environment', '1')
        settlement = PurchaseSettlement(
            id=0,
            tenant_id=tenant_id,
            number=number,
            supplier=supplier,
            supplier_identification=supplier_id,
            supplier_id_type=supplier_id_type,
            supplier_address=supplier_address,
            supplier_email=supplier_email,
            date=doc_date,
            payment_method=data.get('payment_method', '01'),
            status='draft',
            items=items,
            notes=data.get('notes', '').strip(),
            environment=environment,
        )

        # Generar clave de acceso SRI oficial tipo 03
        settlement.access_key = generate_access_key_liquidacion(
            fecha=settlement.date.strftime('%d/%m/%Y'),
            ruc=issuer.get('ruc', ''),
            environment=environment,
            serie=f"{estab}{pto}",
            secuencial=number.split('-')[-1],
        )

        return self.settlement_repo.save(settlement)
