from decimal import Decimal
from datetime import date, datetime
from ..domain.repositories import DispatchGuideRepository
from ..domain.invoice import DispatchGuide, DispatchGuideItem
from ..infrastructure.external_clients.sri_xml_guia_remision import generate_access_key_guia
from .exceptions import BusinessError


class CreateDispatchGuide:
    def __init__(self, guide_repo: DispatchGuideRepository):
        self.guide_repo = guide_repo

    def execute(self, tenant_id: int, data: dict, issuer: dict) -> DispatchGuide:
        estab = issuer.get('establecimiento')
        pto = issuer.get('punto_emision')
        if not estab:
            raise BusinessError('El parámetro "establecimiento" no está configurado en el sistema.', field='establecimiento', code='CONFIG_MISSING')
        if not pto:
            raise BusinessError('El parámetro "punto_emision" no está configurado en el sistema.', field='punto_emision', code='CONFIG_MISSING')

        carrier_ruc = data.get('carrier_ruc', '').strip()
        carrier_name = data.get('carrier_name', '').strip()
        vehicle_plate = data.get('vehicle_plate', '').strip().upper()
        starting_address = data.get('starting_address', '').strip() or issuer.get('direccion', '').strip()

        if not carrier_name:
            raise BusinessError('La razón social o nombre del transportista es obligatorio.', field='carrier_name')
        if not carrier_ruc:
            raise BusinessError('El RUC o identificación del transportista es obligatorio.', field='carrier_ruc')
        if not vehicle_plate:
            raise BusinessError('La placa del vehículo es obligatoria.', field='vehicle_plate')
        if not starting_address:
            raise BusinessError('La dirección de partida es obligatoria.', field='starting_address')

        recipient_id = data.get('recipient_id', '').strip()
        recipient_name = data.get('recipient_name', '').strip()
        recipient_address = data.get('recipient_address', '').strip()

        if not recipient_id:
            raise BusinessError('La identificación del destinatario es obligatoria.', field='recipient_id')
        if not recipient_name:
            raise BusinessError('La razón social o nombre del destinatario es obligatorio.', field='recipient_name')
        if not recipient_address:
            raise BusinessError('La dirección de destino es obligatoria.', field='recipient_address')

        # Determinar tipo de identificación transportista
        carrier_id_type = data.get('carrier_id_type', '04')
        if len(carrier_ruc) == 10 and carrier_id_type not in ('05', '06'):
            carrier_id_type = '05'
        elif len(carrier_ruc) == 13 and carrier_id_type not in ('04', '06'):
            carrier_id_type = '04'

        # Determinar tipo de identificación destinatario
        recipient_id_type = data.get('recipient_id_type', '04')
        if len(recipient_id) == 10 and recipient_id_type not in ('05', '06'):
            recipient_id_type = '05'
        elif len(recipient_id) == 13 and recipient_id_type not in ('04', '06'):
            recipient_id_type = '04'

        raw_items = data.get('items', [])
        if not raw_items:
            raise BusinessError('Debe agregar al menos un ítem o mercadería a trasladar.', field='items')

        # Fechas de traslado
        def _parse_d(val, default):
            if isinstance(val, (date, datetime)):
                return val if isinstance(val, date) else val.date()
            if isinstance(val, str) and len(val) >= 10:
                return datetime.strptime(val[:10], '%Y-%m-%d').date()
            return default

        today = date.today()
        date_emission = _parse_d(data.get('date_emission'), today)
        start_date = _parse_d(data.get('start_date'), date_emission)
        end_date = _parse_d(data.get('end_date'), start_date)

        # Control de Período Contable / Cierre Fiscal
        from modules.contabilidad.application.period_service import validate_accounting_period
        validate_accounting_period(tenant_id, date_emission, action_desc='emitir guías de remisión')

        # Secuencial oficial
        number = self.guide_repo.next_number(tenant_id, estab, pto, document_type='06')

        items = []
        for i in raw_items:
            qty = Decimal(str(i.get('quantity', 1)))
            desc = i.get('description', '').strip()
            if not desc:
                raise BusinessError('La descripción del ítem a trasladar es obligatoria.', field='items')
            if qty <= 0:
                raise BusinessError('La cantidad a trasladar debe ser mayor a cero.', field='items')
            items.append(DispatchGuideItem(
                description=desc,
                quantity=qty,
                internal_code=i.get('internal_code', '').strip()
            ))

        origin_doc_date_raw = data.get('origin_doc_date')
        origin_doc_date = _parse_d(origin_doc_date_raw, None) if origin_doc_date_raw else None

        environment = issuer.get('environment', '1')
        guide = DispatchGuide(
            id=0,
            tenant_id=tenant_id,
            number=number,
            date_emission=date_emission,
            start_date=start_date,
            end_date=end_date,
            starting_address=starting_address,
            carrier_ruc=carrier_ruc,
            carrier_name=carrier_name,
            carrier_id_type=carrier_id_type,
            vehicle_plate=vehicle_plate,
            recipient_id=recipient_id,
            recipient_id_type=recipient_id_type,
            recipient_name=recipient_name,
            recipient_address=recipient_address,
            transfer_reason=data.get('transfer_reason', 'Venta').strip() or 'Venta',
            route=data.get('route', '').strip(),
            origin_doc_type=data.get('origin_doc_type', '01'),
            origin_doc_number=data.get('origin_doc_number', '').strip(),
            origin_doc_auth=data.get('origin_doc_auth', '').strip(),
            origin_doc_date=origin_doc_date,
            status='draft',
            items=items,
            environment=environment,
        )

        # Generar clave de acceso SRI oficial tipo 06
        guide.access_key = generate_access_key_guia(
            fecha=guide.date_emission.strftime('%d/%m/%Y'),
            ruc=issuer.get('ruc', ''),
            environment=environment,
            serie=f"{estab}{pto}",
            secuencial=number.split('-')[-1],
        )

        return self.guide_repo.save(guide)
