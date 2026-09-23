from ..domain.repositories import CreditNoteRepository
from ..domain.invoice import CreditNote
from ..infrastructure.external_clients.sri_xml_nota_credito import generate_xml_nota_credito
from ..infrastructure.external_clients.sri_firma import sign_xml
from ..infrastructure.external_clients.sri_cliente import send_receipt

class EmitCreditNoteSRI:
    def __init__(self, nc_repo: CreditNoteRepository):
        self.nc_repo = nc_repo

    def execute(self, nc_id: int, tenant_id: int, issuer: dict, cert_path: str, cert_pass: str) -> CreditNote:
        nc = self.nc_repo.find_by_id(nc_id, tenant_id)
        if not nc:
            raise ValueError('Nota de Crédito no encontrada')
        if nc.status != 'draft':
            raise ValueError('Solo se puede emitir una Nota de Crédito en draft')

        # 1. Generar XML en Python
        xml_str = generate_xml_nota_credito(nc, issuer)
        
        # Guardar temporalmente el XML en el storage del Facturador Go
        import os
        from django.conf import settings
        erp_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
        base_path = os.path.join(erp_dir, 'facturador', 'storage')
        os.makedirs(os.path.join(base_path, 'temp'), exist_ok=True)
        
        storage_url = f"temp/nc_{nc_id}_{tenant_id}.xml"
        xml_path = os.path.join(base_path, storage_url)
        
        with open(xml_path, 'w', encoding='utf-8') as f:
            f.write(xml_str)

        # 2. Firmar XML a través del microservicio Go
        from modules.tax_documents.invoicing.infrastructure.external_clients.electrodocs_client import sign_invoice_via_go, send_receipt_via_go
        
        try:
            signed_storage_url = sign_invoice_via_go(storage_url, cert_path, cert_pass)
            nc.signed_xml = signed_storage_url
        except Exception as e:
            raise ValueError(f'Error al firmar XML en Go: {e}')

        # 3. Enviar al SRI a través de Go
        result = send_receipt_via_go(signed_storage_url, nc.environment, issuer, tenant_id, nc.id, doc_type='credit_note')
        nc.sri_status = result['estado']
        nc.sri_message = ' | '.join(result.get('messages', []))

        if result['estado'] == 'RECIBIDA':
            nc.status = 'sent_to_sri'
        else:
            nc.status = 'not_authorized'

        return self.nc_repo.save(nc)

