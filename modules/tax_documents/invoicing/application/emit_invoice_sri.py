from ..domain.repositories import InvoiceRepository
from ..domain.invoice import Invoice

class EmitInvoiceSRI:
    """Genera XML, firma y envÃ­a al SRI"""
    def __init__(self, repo: InvoiceRepository):
        self.repo = repo

    def execute(self, invoice_id: int, tenant_id: int, issuer: dict, cert_path: str, cert_pass: str) -> Invoice:
        invoice = self.repo.find_by_id(invoice_id, tenant_id)
        if not invoice:
            raise ValueError('Factura no encontrada')
        if invoice.status not in ('draft', 'not_authorized'):
            raise ValueError('Solo se puede emitir una factura en draft o no_autorizada')

        # Si falló anteriormente por secuencial duplicado, asignarle uno nuevo
        if invoice.status == 'not_authorized' and invoice.sri_message and 'SECUENCIAL REGISTRADO' in invoice.sri_message.upper():
            try:
                estab, pto, _ = invoice.number.split('-')
                new_number = self.repo.next_number(tenant_id, estab, pto)
                invoice.number = new_number
                
                # Regenerar la clave de acceso
                from modules.tax_documents.invoicing.infrastructure.external_clients.sri_xml import generate_access_key
                invoice.access_key = generate_access_key(
                    fecha=invoice.date.strftime('%d/%m/%Y'),
                    ruc=issuer.get('ruc', ''),
                    environment=invoice.environment,
                    serie=f"{estab}{pto}",
                    secuencial=new_number.split('-')[-1],
                )
                self.repo.save(invoice)
            except Exception as e:
                print(f"Error regenerando secuencial: {e}")

        # 1. Generar Factura en el microservicio de Go
        from modules.tax_documents.invoicing.infrastructure.external_clients.electrodocs_client import build_invoice_via_go, sign_invoice_via_go, send_receipt_via_go
        storage_url = build_invoice_via_go(invoice, issuer)

        # Leer el XML local para sincronizar la clave de acceso y el nÃºmero que generÃ³ Go
        import os
        import xml.etree.ElementTree as ET
        try:
            # Resolving facturador directory relative to backend (they are siblings in erp folder)
            backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
            default_storage_path = os.path.join(backend_dir, 'facturador', 'storage')
            base_path = os.environ.get('LOCAL_STORAGE_PATH', default_storage_path)
            
            # Normalize slashes for Windows
            normalized_url = storage_url.replace('\\', '/')
            xml_path = os.path.join(base_path, normalized_url)
            xml_path = os.path.normpath(xml_path)
            
            tree = ET.parse(xml_path)
            clave = tree.find('.//claveAcceso')
            if clave is not None:
                invoice.access_key = clave.text
            
            estab = tree.find('.//estab')
            pto_emi = tree.find('.//ptoEmi')
            secuencial = tree.find('.//secuencial')
            if estab is not None and pto_emi is not None and secuencial is not None:
                invoice.number = f"{estab.text}-{pto_emi.text}-{secuencial.text}"
        except Exception as e:
            print(f"Error extracting access key and number from XML: {e}")

        # 2. Firmar XML a travÃ©s de Go
        signed_storage_url = sign_invoice_via_go(storage_url, cert_path, cert_pass)
        invoice.signed_xml = signed_storage_url

        # 3. Enviar al SRI a travÃ©s de Go
        result = send_receipt_via_go(signed_storage_url, invoice.environment, issuer, tenant_id, invoice.id)
        invoice.sri_status = result['estado']
        invoice.sri_message = ' | '.join(result.get('messages', []))

        if result['estado'] == 'RECIBIDA':
            invoice.status = 'sent_to_sri'
        else:
            invoice.status = 'not_authorized'

        return self.repo.save(invoice)

