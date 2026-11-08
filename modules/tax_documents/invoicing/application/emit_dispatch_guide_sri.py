import os
from ..domain.repositories import DispatchGuideRepository
from ..domain.invoice import DispatchGuide
from ..infrastructure.external_clients.sri_xml_guia_remision import generate_xml_guia_remision
from ..infrastructure.external_clients.electrodocs_client import sign_invoice_via_go, send_receipt_via_go


class EmitDispatchGuideSRI:
    """Genera XML 1.1.0 tipo 06, firma digitalmente vía Go (.p12) y envía al SRI"""
    def __init__(self, guide_repo: DispatchGuideRepository):
        self.guide_repo = guide_repo

    def execute(self, guide_id: int, tenant_id: int, issuer: dict, cert_path: str, cert_pass: str) -> DispatchGuide:
        guide = self.guide_repo.find_by_id(guide_id, tenant_id)
        if not guide:
            raise ValueError('Guía de Remisión no encontrada')
        if guide.status not in ('draft', 'not_authorized'):
            raise ValueError('Solo se puede emitir una guía de remisión en estado borrador o no autorizada')

        # 1. Generar XML en formato oficial SRI 1.1.0 tipo 06
        xml_str = generate_xml_guia_remision(guide, issuer)

        # 2. Guardar temporalmente en storage del facturador Go
        erp_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
        base_path = os.path.join(erp_dir, 'facturador', 'storage')
        os.makedirs(os.path.join(base_path, 'temp'), exist_ok=True)

        storage_url = f"temp/guia_{guide_id}_{tenant_id}.xml"
        xml_path = os.path.join(base_path, storage_url)

        with open(xml_path, 'w', encoding='utf-8') as f:
            f.write(xml_str)

        # 3. Firmar XML mediante el microservicio Go (.p12)
        try:
            signed_storage_url = sign_invoice_via_go(storage_url, cert_path, cert_pass)
            guide.signed_xml = signed_storage_url
        except Exception as e:
            raise ValueError(f'Error al firmar XML de guía de remisión en Go: {e}')

        # 4. Enviar comprobante al SRI vía Go
        result = send_receipt_via_go(
            signed_storage_url=signed_storage_url,
            environment=guide.environment,
            issuer=issuer,
            tenant_id=tenant_id,
            invoice_id=guide.id,
            doc_type='dispatch_guide',
            comprobant_code='06'
        )

        guide.sri_status = result.get('estado', '')
        guide.sri_message = ' | '.join(result.get('messages', []))

        if result.get('estado') == 'RECIBIDA':
            guide.status = 'sent_to_sri'
        else:
            guide.status = 'not_authorized'

        return self.guide_repo.save(guide)
