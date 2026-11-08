import os
from ..domain.repositories import WithholdingRepository
from ..domain.invoice import Withholding
from ..infrastructure.external_clients.sri_xml_retencion import generate_xml_retencion
from ..infrastructure.external_clients.electrodocs_client import sign_invoice_via_go, send_receipt_via_go


class EmitWithholdingSRI:
    """Genera XML 2.0.0, firma digitalmente vía Go y envía al SRI"""
    def __init__(self, withholding_repo: WithholdingRepository):
        self.withholding_repo = withholding_repo

    def execute(self, ret_id: int, tenant_id: int, issuer: dict, cert_path: str, cert_pass: str) -> Withholding:
        withholding = self.withholding_repo.find_by_id(ret_id, tenant_id)
        if not withholding:
            raise ValueError('Comprobante de Retención no encontrado')
        if withholding.status not in ('draft', 'not_authorized'):
            raise ValueError('Solo se puede emitir una retención en estado borrador o no autorizada')

        # 1. Generar XML en formato oficial SRI 2.0.0
        xml_str = generate_xml_retencion(withholding, issuer)

        # 2. Guardar temporalmente en storage del facturador Go
        erp_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
        base_path = os.path.join(erp_dir, 'facturador', 'storage')
        os.makedirs(os.path.join(base_path, 'temp'), exist_ok=True)

        storage_url = f"temp/ret_{ret_id}_{tenant_id}.xml"
        xml_path = os.path.join(base_path, storage_url)

        with open(xml_path, 'w', encoding='utf-8') as f:
            f.write(xml_str)

        # 3. Firmar XML mediante el microservicio Go (.p12)
        try:
            signed_storage_url = sign_invoice_via_go(storage_url, cert_path, cert_pass)
            withholding.signed_xml = signed_storage_url
        except Exception as e:
            raise ValueError(f'Error al firmar XML de retención en Go: {e}')

        # 4. Enviar comprobante al SRI vía Go
        result = send_receipt_via_go(
            signed_storage_url=signed_storage_url,
            environment=withholding.environment,
            issuer=issuer,
            tenant_id=tenant_id,
            invoice_id=withholding.id,
            doc_type='withholding',
            comprobant_code='07'
        )

        withholding.sri_status = result.get('estado', '')
        withholding.sri_message = ' | '.join(result.get('messages', []))

        if result.get('estado') == 'RECIBIDA':
            withholding.status = 'sent_to_sri'
        else:
            withholding.status = 'not_authorized'

        return self.withholding_repo.save(withholding)
