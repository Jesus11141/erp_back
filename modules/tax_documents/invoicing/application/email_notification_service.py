"""
Servicio de Notificación por Correo Electrónico (SMTP Multi-Tenant).
Envía automáticamente o a petición el RIDE en PDF oficial y el XML autorizado
a clientes y proveedores según el Art. 12 del Reglamento de Comprobantes Electrónicos del SRI.
"""

import os
import threading
from decimal import Decimal
from typing import Dict, Any, Optional

from django.conf import settings
from django.core.mail import EmailMessage, get_connection

from modules.parametros.infrastructure.repository_impl import DjangoParameterRepository
from modules.shared.crypto import descifrar
from modules.ventas.infrastructure.django_models import CustomerModel
from modules.compras.infrastructure.django_models import ProveedorModel
from modules.tenants.infrastructure.django_models import TenantModel
from modules.tax_documents.invoicing.infrastructure.persistence.django_models import (
    InvoiceModel, CreditNoteModel, WithholdingModel, DispatchGuideModel, PurchaseSettlementModel
)
from modules.reportes.infrastructure.pdf_generator import (
    generate_invoice_pdf, generate_credit_note_pdf,
    generate_withholding_pdf, generate_dispatch_guide_pdf,
    generate_purchase_settlement_pdf
)


class EmailNotificationService:

    @staticmethod
    def get_smtp_config(tenant_id: int) -> Dict[str, Any]:
        """
        Recupera la configuración SMTP del tenant desde la base de datos de Parámetros.
        Si no está configurada, utiliza los fallbacks globales de settings/.env.
        """
        repo_params = DjangoParameterRepository()
        params = {p.key: p.value for p in repo_params.list_by_module(tenant_id, 'correo')}
        general_params = {p.key: p.value for p in repo_params.list_by_module(tenant_id, 'general')}
        fact_params = {p.key: p.value for p in repo_params.list_by_module(tenant_id, 'facturacion')}

        tenant = TenantModel.objects.filter(id=tenant_id).first()
        company_name = general_params.get('empresa_nombre') or (tenant.name if tenant else 'Mi Empresa')
        logo_url = general_params.get('logo_url') or (tenant.logo_url if tenant else '')

        # Host
        host = params.get('smtp_host', '').strip() or getattr(settings, 'EMAIL_HOST', 'localhost')
        # Port
        try:
            port = int(params.get('smtp_port', '').strip() or getattr(settings, 'EMAIL_PORT', 587))
        except ValueError:
            port = 587

        # User & Password
        user = params.get('smtp_user', '').strip() or getattr(settings, 'EMAIL_HOST_USER', '')
        raw_pass = params.get('smtp_password', '').strip() or getattr(settings, 'EMAIL_HOST_PASSWORD', '')
        password = descifrar(raw_pass) if raw_pass else ''

        # TLS / SSL
        use_tls = params.get('smtp_use_tls', 'true').lower() == 'true'
        use_ssl = params.get('smtp_use_ssl', 'false').lower() == 'true'
        if port == 465:
            use_ssl = True
            use_tls = False

        from_name = params.get('smtp_from_name', '').strip() or company_name
        from_email = user or getattr(settings, 'DEFAULT_FROM_EMAIL', 'facturacion@sistema.com')
        full_from = f"{from_name} <{from_email}>" if from_name else from_email

        enviar_auto = params.get('enviar_automatico', 'true').lower() == 'true'

        return {
            'host': host,
            'port': port,
            'user': user,
            'password': password,
            'use_tls': use_tls,
            'use_ssl': use_ssl,
            'from_email': full_from,
            'sender_email': from_email,
            'company_name': company_name,
            'logo_url': logo_url,
            'enviar_automatico': enviar_auto,
            'params': {**general_params, **fact_params},
            'tenant': tenant,
        }

    @classmethod
    def test_smtp_connection(cls, tenant_id: int, test_email: str) -> Dict[str, Any]:
        """
        Envía un correo de prueba para validar que los datos SMTP ingresados funcionan correctamente.
        """
        cfg = cls.get_smtp_config(tenant_id)
        if not cfg['host'] or not cfg['user'] or not cfg['password']:
            return {
                'success': False,
                'error': 'Credenciales SMTP incompletas. Ingrese Servidor, Usuario y Contraseña en Parametrización.'
            }

        try:
            connection = get_connection(
                backend='django.core.mail.backends.smtp.EmailBackend',
                host=cfg['host'],
                port=cfg['port'],
                username=cfg['user'],
                password=cfg['password'],
                use_tls=cfg['use_tls'],
                use_ssl=cfg['use_ssl'],
                timeout=12,
            )

            html_body = f"""
            <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
                <h2 style="color: #16a34a; margin-top: 0;">✓ Conexión SMTP Exitosa</h2>
                <p>Este es un correo de prueba enviado desde <strong>{cfg['company_name']}</strong>.</p>
                <p>La configuración de tu servidor de correo ({cfg['host']}:{cfg['port']}) está operando correctamente y lista para despachar facturas electrónicas y comprobantes SRI.</p>
                <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 20px 0;">
                <small style="color: #64748b;">ERP Facturación Electrónica SRI Ecuador</small>
            </div>
            """

            msg = EmailMessage(
                subject=f"Prueba de Conexión SMTP - {cfg['company_name']}",
                body=html_body,
                from_email=cfg['from_email'],
                to=[test_email.strip()],
                connection=connection,
            )
            msg.content_subtype = 'html'
            msg.send(fail_silently=False)

            return {'success': True, 'message': f'Correo de prueba enviado con éxito a {test_email}'}

        except Exception as e:
            return {'success': False, 'error': f'Error conectando con el servidor SMTP: {str(e)}'}

    @classmethod
    def send_document_email(cls, tenant_id: int, doc_type: str, doc_id: int, recipient_override: Optional[str] = None) -> Dict[str, Any]:
        """
        Envía el comprobante electrónico autorizado (RIDE en PDF + XML) por correo electrónico.
        Soporta: 'invoice', 'credit_note', 'withholding', 'dispatch_guide', 'purchase_settlement'.
        """
        cfg = cls.get_smtp_config(tenant_id)
        tenant = cfg['tenant']
        tenant_dict = {
            'id': tenant.id if tenant else tenant_id,
            'name': cfg['company_name'],
            'logo_url': cfg['logo_url'],
            'primary_color': '#16a34a'
        }

        # 1. Obtener documento y datos de destinatario
        doc_type_norm = doc_type.lower().strip()
        doc_obj = None
        doc_name = "Comprobante Electrónico"
        recipient_email = (recipient_override or '').strip()
        recipient_name = ""
        numero = ""
        fecha = ""
        clave_acceso = ""
        total_str = "$0.00"
        pdf_bytes = None
        xml_bytes = None

        if doc_type_norm in ['invoice', 'factura']:
            doc_obj = InvoiceModel.objects.filter(id=doc_id, tenant_id=tenant_id).first()
            if not doc_obj: return {'success': False, 'error': 'Factura no encontrada'}
            doc_name = "Factura Electrónica"
            numero = doc_obj.number
            fecha = str(doc_obj.date)
            clave_acceso = doc_obj.access_key
            recipient_name = doc_obj.client

            # Email
            if not recipient_email:
                recipient_email = doc_obj.client_email or ''
            if not recipient_email and doc_obj.client_identification:
                c = CustomerModel.objects.filter(tenant_id=tenant_id, rfc=doc_obj.client_identification).first()
                if c and c.email: recipient_email = c.email

            # Calcular total
            subtotal = sum(Decimal(str(it.quantity)) * Decimal(str(it.unit_price)) - Decimal(str(it.discount)) for it in doc_obj.items.all())
            iva = subtotal * (Decimal(str(doc_obj.vat)) / Decimal('100'))
            total_str = f"${(subtotal + iva):,.2f}"

            # RIDE PDF
            inv_items = [
                {
                    'description': i.description,
                    'quantity': str(i.quantity),
                    'unit_price': str(i.unit_price),
                    'discount': str(i.discount or '0'),
                    'vat_rate': str(i.vat_rate or '15'),
                }
                for i in doc_obj.items.all()
            ]
            inv_dict = {
                'number': doc_obj.number,
                'date': str(doc_obj.date),
                'status': doc_obj.status,
                'client': doc_obj.client,
                'client_identification': doc_obj.client_identification,
                'client_address': getattr(doc_obj, 'client_address', ''),
                'client_email': recipient_email,
                'access_key': doc_obj.access_key,
                'authorization_number': doc_obj.authorization_number,
                'authorization_date': doc_obj.authorization_date,
                'environment': doc_obj.environment,
                'items': inv_items,
            }
            pdf_bytes = generate_invoice_pdf(inv_dict, cfg['params'], tenant_dict)

        elif doc_type_norm in ['credit_note', 'nota_credito']:
            doc_obj = CreditNoteModel.objects.filter(id=doc_id, tenant_id=tenant_id).first()
            if not doc_obj: return {'success': False, 'error': 'Nota de crédito no encontrada'}
            doc_name = "Nota de Crédito"
            numero = doc_obj.number
            fecha = str(doc_obj.date)
            clave_acceso = doc_obj.access_key
            recipient_name = doc_obj.client

            if not recipient_email and doc_obj.client_identification:
                c = CustomerModel.objects.filter(tenant_id=tenant_id, rfc=doc_obj.client_identification).first()
                if c and c.email: recipient_email = c.email

            total_str = f"${Decimal(str(doc_obj.total)):,.2f}"

            nc_items = [
                {
                    'main_code': i.main_code,
                    'description': i.description,
                    'quantity': str(i.quantity),
                    'unit_price': str(i.unit_price),
                    'discount': str(i.discount or '0'),
                    'vat_rate': str(i.vat_rate or '15'),
                }
                for i in doc_obj.items.all()
            ]
            nc_dict = {
                'number': doc_obj.number,
                'date': str(doc_obj.date),
                'status': doc_obj.status,
                'reason': doc_obj.get_reason_display() if hasattr(doc_obj, 'get_reason_display') else doc_obj.reason,
                'client': doc_obj.client,
                'client_identification': doc_obj.client_identification,
                'origin_invoice_number': doc_obj.origin_invoice_number,
                'origin_invoice_date': '',
                'access_key': doc_obj.access_key,
                'authorization_number': doc_obj.authorization_number,
                'authorization_date': doc_obj.authorization_date,
                'environment': doc_obj.environment,
                'items': nc_items,
            }
            pdf_bytes = generate_credit_note_pdf(nc_dict, cfg['params'], tenant_dict)

        elif doc_type_norm in ['withholding', 'retencion']:
            doc_obj = WithholdingModel.objects.filter(id=doc_id, tenant_id=tenant_id).first()
            if not doc_obj: return {'success': False, 'error': 'Comprobante de retención no encontrado'}
            doc_name = "Comprobante de Retención"
            numero = doc_obj.number
            fecha = str(doc_obj.date)
            clave_acceso = doc_obj.access_key
            recipient_name = doc_obj.supplier

            if not recipient_email and doc_obj.supplier_identification:
                p = ProveedorModel.objects.filter(tenant_id=tenant_id, identification=doc_obj.supplier_identification).first()
                if p and p.email: recipient_email = p.email

            total_ret = sum(Decimal(str(it.withheld_value)) for it in doc_obj.items.all())
            total_str = f"${total_ret:,.2f}"

            from modules.reportes.infrastructure.api.views import _tenant_dict, _get_params
            ret_dict = {
                'number': doc_obj.number,
                'date': str(doc_obj.date),
                'status': doc_obj.status,
                'supplier': doc_obj.supplier,
                'supplier_identification': doc_obj.supplier_identification,
                'origin_invoice_number': doc_obj.origin_invoice_number,
                'fiscal_period': doc_obj.fiscal_period,
                'access_key': doc_obj.access_key,
                'authorization_number': doc_obj.authorization_number,
                'authorization_date': doc_obj.authorization_date,
                'environment': doc_obj.environment,
                'items': [{'type_code': i.type_code, 'withholding_code': i.withholding_code, 'tax_base': str(i.tax_base), 'percentage': str(i.percentage), 'withheld_value': str(i.withheld_value)} for i in doc_obj.items.all()],
            }
            pdf_bytes = generate_withholding_pdf(ret_dict, cfg['params'], tenant_dict)

        elif doc_type_norm in ['dispatch_guide', 'guia_remision']:
            doc_obj = DispatchGuideModel.objects.filter(id=doc_id, tenant_id=tenant_id).first()
            if not doc_obj: return {'success': False, 'error': 'Guía de remisión no encontrada'}
            doc_name = "Guía de Remisión"
            numero = doc_obj.number
            fecha = str(doc_obj.date_emission)
            clave_acceso = doc_obj.access_key
            recipient_name = doc_obj.recipient_name
            if not recipient_email and doc_obj.recipient_id:
                c = CustomerModel.objects.filter(tenant_id=tenant_id, rfc=doc_obj.recipient_id).first()
                if c and c.email: recipient_email = c.email

            guide_dict = {
                'number': doc_obj.number, 'date_emission': str(doc_obj.date_emission),
                'start_date': str(doc_obj.start_date), 'end_date': str(doc_obj.end_date),
                'starting_address': doc_obj.starting_address, 'carrier_ruc': doc_obj.carrier_ruc,
                'carrier_name': doc_obj.carrier_name, 'vehicle_plate': doc_obj.vehicle_plate,
                'recipient_id': doc_obj.recipient_id, 'recipient_name': doc_obj.recipient_name,
                'recipient_address': doc_obj.recipient_address, 'transfer_reason': doc_obj.transfer_reason,
                'route': doc_obj.route, 'origin_doc_number': doc_obj.origin_doc_number,
                'origin_doc_auth': doc_obj.origin_doc_auth, 'status': doc_obj.status,
                'access_key': doc_obj.access_key, 'authorization_number': doc_obj.authorization_number,
                'authorization_date': doc_obj.authorization_date, 'environment': doc_obj.environment,
                'items': [{'internal_code': i.internal_code, 'description': i.description, 'quantity': str(i.quantity)} for i in doc_obj.items.all()],
            }
            pdf_bytes = generate_dispatch_guide_pdf(guide_dict, cfg['params'], tenant_dict)

        elif doc_type_norm in ['purchase_settlement', 'liquidacion_compra']:
            doc_obj = PurchaseSettlementModel.objects.filter(id=doc_id, tenant_id=tenant_id).first()
            if not doc_obj: return {'success': False, 'error': 'Liquidación de compra no encontrada'}
            doc_name = "Liquidación de Compra"
            numero = doc_obj.number
            fecha = str(doc_obj.date)
            clave_acceso = doc_obj.access_key
            recipient_name = doc_obj.supplier
            recipient_email = recipient_email or doc_obj.supplier_email
            total_str = f"${Decimal(str(doc_obj.total)):,.2f}"

            liq_dict = {
                'number': doc_obj.number, 'date': str(doc_obj.date), 'supplier': doc_obj.supplier,
                'supplier_identification': doc_obj.supplier_identification, 'supplier_address': doc_obj.supplier_address,
                'supplier_email': doc_obj.supplier_email, 'payment_method': doc_obj.payment_method,
                'notes': doc_obj.notes, 'subtotal_0': str(doc_obj.subtotal_0), 'subtotal_iva': str(doc_obj.subtotal_iva),
                'total_discount': '0.00', 'vat': str(doc_obj.vat), 'total': str(doc_obj.total),
                'status': doc_obj.status, 'access_key': doc_obj.access_key,
                'authorization_number': doc_obj.authorization_number, 'authorization_date': doc_obj.authorization_date,
                'environment': doc_obj.environment,
                'items': [{'product_code': i.product_code, 'description': i.description, 'quantity': str(i.quantity), 'unit_price': str(i.unit_price), 'discount': '0', 'vat_rate': str(i.vat_rate), 'subtotal': str(i.quantity * i.unit_price)} for i in doc_obj.items.all()]
            }
            pdf_bytes = generate_purchase_settlement_pdf(liq_dict, cfg['params'], tenant_dict)

        if not recipient_email or '@' not in recipient_email:
            return {
                'success': False,
                'error': f'El destinatario ({recipient_name or "Desconocido"}) no tiene correo electrónico registrado para el envío.'
            }

        # 2. Obtener XML firmado
        xml_content = getattr(doc_obj, 'signed_xml', '')
        if xml_content:
            if xml_content.startswith('<'):
                xml_bytes = xml_content.encode('utf-8')
            elif xml_content.endswith('.xml'):
                base_path = os.environ.get('LOCAL_STORAGE_PATH', os.path.join(settings.BASE_DIR, 'storage'))
                xml_path = os.path.join(base_path, xml_content.replace('\\', '/'))
                if os.path.exists(xml_path):
                    with open(xml_path, 'rb') as f:
                        xml_bytes = f.read()

        # 3. Construir Cuerpo HTML del Correo
        logo_html = f'<img src="{cfg["logo_url"]}" style="max-height: 55px; margin-bottom: 15px;" alt="Logo" /><br>' if cfg.get('logo_url') else ''
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: 'Helvetica Neue', Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px; }}
                .container {{ max-width: 620px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }}
                .header {{ background: #16a34a; color: #ffffff; padding: 25px 30px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 20px; font-weight: 700; letter-spacing: 0.5px; }}
                .content {{ padding: 30px; color: #334155; line-height: 1.6; font-size: 14px; }}
                .box {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 18px; margin: 20px 0; }}
                .box table {{ width: 100%; border-collapse: collapse; }}
                .box td {{ padding: 6px 0; font-size: 13px; }}
                .box td.label {{ color: #64748b; font-weight: 600; width: 38%; }}
                .box td.value {{ color: #0f172a; font-weight: 700; }}
                .access-key {{ font-family: monospace; font-size: 11px; background: #e2e8f0; padding: 4px 6px; border-radius: 4px; word-break: break-all; display: block; margin-top: 4px; }}
                .footer {{ background: #f1f5f9; padding: 20px; text-align: center; font-size: 12px; color: #64748b; border-top: 1px solid #e2e8f0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    {logo_html}
                    <h1>{cfg['company_name']}</h1>
                    <p style="margin: 5px 0 0 0; font-size: 13px; opacity: 0.9;">Comprobante Electrónico Autorizado por el SRI</p>
                </div>
                <div class="content">
                    <p>Estimado(a) <strong>{recipient_name}</strong>,</p>
                    <p>Le informamos que se ha emitido y autorizado ante el <strong>Servicio de Rentas Internas (SRI) del Ecuador</strong> su <strong>{doc_name}</strong> con el siguiente detalle:</p>
                    
                    <div class="box">
                        <table>
                            <tr>
                                <td class="label">Comprobante:</td>
                                <td class="value">{doc_name} N° {numero}</td>
                            </tr>
                            <tr>
                                <td class="label">Fecha de Emisión:</td>
                                <td class="value">{fecha}</td>
                            </tr>
                            <tr>
                                <td class="label">Valor Total:</td>
                                <td class="value" style="color: #16a34a; font-size: 15px;">{total_str}</td>
                            </tr>
                            <tr>
                                <td class="label" style="vertical-align: top;">Clave de Acceso SRI:</td>
                                <td class="value"><span class="access-key">{clave_acceso}</span></td>
                            </tr>
                        </table>
                    </div>

                    <p style="margin-bottom: 0;">Adjunto a este correo electrónico encontrará:</p>
                    <ul style="margin-top: 5px; padding-left: 20px;">
                        <li><strong>RIDE en PDF:</strong> Representación gráfica oficial con código de barras de 49 dígitos.</li>
                        <li><strong>Archivo XML:</strong> Documento digital firmado con validez tributaria oficial.</li>
                    </ul>
                </div>
                <div class="footer">
                    <p style="margin: 0 0 4px 0;">Este es un mensaje automático generado por el sistema de Facturación Electrónica de <strong>{cfg['company_name']}</strong>.</p>
                    <p style="margin: 0;">Conforme al Art. 12 del Reglamento de Comprobantes Electrónicos del SRI.</p>
                </div>
            </div>
        </body>
        </html>
        """

        # 4. Enviar mediante Django EmailMessage
        try:
            connection = get_connection(
                backend='django.core.mail.backends.smtp.EmailBackend',
                host=cfg['host'],
                port=cfg['port'],
                username=cfg['user'],
                password=cfg['password'],
                use_tls=cfg['use_tls'],
                use_ssl=cfg['use_ssl'],
                timeout=15,
            )

            subject = f"{doc_name} {numero} - {cfg['company_name']}"
            msg = EmailMessage(
                subject=subject,
                body=html_body,
                from_email=cfg['from_email'],
                to=[recipient_email],
                connection=connection,
            )
            msg.content_subtype = 'html'

            # Adjuntar PDF si se generó
            if pdf_bytes:
                clean_num = numero.replace('/', '_').replace('-', '_')
                msg.attach(f"{doc_type_norm}_{clean_num}.pdf", pdf_bytes, 'application/pdf')

            # Adjuntar XML si existe
            if xml_bytes:
                clean_num = numero.replace('/', '_').replace('-', '_')
                msg.attach(f"{doc_type_norm}_{clean_num}.xml", xml_bytes, 'application/xml')

            msg.send(fail_silently=False)

            return {
                'success': True,
                'recipient': recipient_email,
                'message': f'Comprobante enviado exitosamente a {recipient_email}'
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Error al despachar correo electrónico: {str(e)}'
            }

    @classmethod
    def send_document_email_async(cls, tenant_id: int, doc_type: str, doc_id: int, recipient_override: Optional[str] = None):
        """
        Lanza el envío de correo en un hilo secundario en segundo plano (no bloqueante).
        """
        thread = threading.Thread(
            target=cls.send_document_email,
            args=(tenant_id, doc_type, doc_id, recipient_override),
            daemon=True
        )
        thread.start()
