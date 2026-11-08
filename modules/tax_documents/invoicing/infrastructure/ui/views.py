import os
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ...infrastructure.persistence.repository_impl import (
    DjangoInvoiceRepository, DjangoCreditNoteRepository, DjangoWithholdingRepository,
    DjangoDispatchGuideRepository, DjangoPurchaseSettlementRepository
)
from ...application.use_cases import (
    CreateInvoice, EmitInvoiceSRI, CheckInvoiceAuthorizationSRI, CancelInvoice, ListInvoices,
    CreateCreditNote, EmitCreditNoteSRI, CheckCreditNoteAuthorizationSRI,
    CreateWithholding, EmitWithholdingSRI, CheckWithholdingAuthorizationSRI,
    CreateDispatchGuide, EmitDispatchGuideSRI, CheckDispatchGuideAuthorizationSRI,
    CreatePurchaseSettlement, EmitPurchaseSettlementSRI, CheckPurchaseSettlementAuthorizationSRI
)
from modules.parametros.application.use_cases import GetParameter
from modules.parametros.infrastructure.repository_impl import DjangoParameterRepository
from ...application.exceptions import BusinessError

def verificar_modulo(request):
    if not request.tenant or not request.tenant.has_module('facturacion'):
        return Response({'error': 'Módulo no disponible'}, status=status.HTTP_403_FORBIDDEN)
    return None


def _param(tenant_id, modulo, clave, default=''):
    return GetParameter(DjangoParameterRepository()).execute(tenant_id, modulo, clave, default)


def _get_emisor(tenant_id):
    """Construye el dict emisor desde parámetros"""
    return {
        'ruc':                  _param(tenant_id, 'facturacion', 'ruc_emisor', ''),
        'sri_password':         _param(tenant_id, 'facturacion', 'sri_password', ''),
        'razon_social':         _param(tenant_id, 'general', 'empresa_nombre', ''),
        'nombre_comercial':     _param(tenant_id, 'general', 'empresa_nombre', ''),
        'direccion':            _param(tenant_id, 'general', 'empresa_direccion', ''),
        'establecimiento':      _param(tenant_id, 'facturacion', 'establecimiento', ''),
        'punto_emision':        _param(tenant_id, 'facturacion', 'punto_emision', ''),
        'environment':          _param(tenant_id, 'facturacion', 'ambiente_sri', '1'),
        'obligado_contabilidad':_param(tenant_id, 'facturacion', 'obligado_contabilidad', 'NO'),
        'contribuyente_especial':_param(tenant_id, 'facturacion', 'contribuyente_especial', ''),
    }


def _invoice_dict(f):
    return {
        'id': f.id,
        'number': f.number,
        'client': f.client,
        'client_identification': f.client_identification,
        'date': f.date,
        'created_at': f.created_at.strftime('%Y-%m-%d %H:%M:%S') if getattr(f, 'created_at', None) else str(f.date) + ' 00:00:00',
        'subtotal': str(f.subtotal),
        'vat': str(f.tax),
        'total': str(f.total),
        'status': f.status,
        'payment_method': f.payment_method,
        'notes': f.notes,
        'access_key': f.access_key,
        'authorization_number': f.authorization_number,
        'authorization_date': f.authorization_date,
        'client_address': getattr(f, 'client_address', ''),
        'sri_status': f.sri_status,
        'sri_message': f.sri_message,
        'environment': f.environment,
        'items': [{
            'description': i.description,
            'quantity': str(i.quantity),
            'unit_price': str(i.unit_price),
            'discount': str(getattr(i, 'discount', 0)),
            'total': str(i.subtotal)
        } for i in (getattr(f, 'items', None) or [])]
    }


def api_success(data, status_code=status.HTTP_200_OK):
    return Response({
        "status": "success",
        "data": data if isinstance(data, list) else [data]
    }, status=status_code)


def api_business_error(message, field=None, code="BUSINESS_ERROR", status_code=status.HTTP_400_BAD_REQUEST):
    return Response({
        "status": "business_error",
        "error": str(message),
        "data": [{
            "code": code,
            "field": field,
            "message": str(message)
        }]
    }, status=status_code)


def api_system_error(message, detail=None, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR):
    return Response({
        "status": "system_error",
        "error": f"{message}: {detail}" if detail else str(message),
        "message": str(message),
        "data": [{"detail": detail}] if detail else []
    }, status=status_code)

class InvoicesView(APIView):
    def get(self, request):
        if e := verificar_modulo(request): return e
        
        if request.GET.get('pending_ids') == 'true':
            from ..persistence.django_models import InvoiceModel
            ids = list(InvoiceModel.objects.filter(
                tenant_id=request.tenant.id,
                status__in=['draft', 'not_authorized']
            ).exclude(client_identification='9999999999999').values_list('id', flat=True))
            return Response({'ids': ids})

        repo = DjangoInvoiceRepository()
        
        page = int(request.GET.get('page', 1))
        limit = int(request.GET.get('limit', 10))
        
        result = ListInvoices(repo).execute(request.tenant.id, page, limit)
        return Response({
            'total': result['total'],
            'page': result['page'],
            'limit': result['limit'],
            'data': [_invoice_dict(f) for f in result['items']]
        })

    def post(self, request):
        if e := verificar_modulo(request): return e
        try:
            repo = DjangoInvoiceRepository()
            emisor = _get_emisor(request.tenant.id)
            iva = _param(request.tenant.id, 'ventas', 'iva', '15')
            factura = CreateInvoice(repo).execute(
                tenant_id=request.tenant.id,
                data=request.data,
                issuer=emisor,
                vat=iva,
            )
            return api_success(_invoice_dict(factura), status_code=status.HTTP_201_CREATED)
        except BusinessError as e:
            return api_business_error(e.message, field=e.field, code=e.code)
        except ValueError as e:
            return api_business_error(str(e), code='VALIDATION_ERROR')
        except KeyError as e:
            return api_business_error(f"Falta el campo obligatorio: {str(e)}", field=str(e), code='MISSING_FIELD')
        except Exception as e:
            return api_system_error("Ocurrió un error inesperado al crear la factura.", detail=str(e))


class InvoiceActionsView(APIView):
    def post(self, request, invoice_id, accion):
        if e := verificar_modulo(request): return e
        repo = DjangoInvoiceRepository()
        try:
            if accion == 'emitir':
                emisor = _get_emisor(request.tenant.id)
                cert_path = _param(request.tenant.id, 'facturacion', 'signature_file', '')
                cert_pass = _param(request.tenant.id, 'facturacion', 'signature_password', '')
                if not cert_path:
                    return Response(
                        {'error': 'Certificado P12 no configurado. Ve a Parametrización → Facturación'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                factura = EmitInvoiceSRI(repo).execute(
                    invoice_id, request.tenant.id, emisor, cert_path, cert_pass
                )
            elif accion == 'autorizar':
                factura = CheckInvoiceAuthorizationSRI(repo).execute(invoice_id, request.tenant.id)
                if factura.status == 'authorized':
                    try:
                        from modules.tax_documents.invoicing.application.email_notification_service import EmailNotificationService
                        smtp_cfg = EmailNotificationService.get_smtp_config(request.tenant.id)
                        if smtp_cfg.get('enviar_automatico', True):
                            EmailNotificationService.send_document_email_async(request.tenant.id, 'invoice', invoice_id)
                    except Exception as ex:
                        print(f"[InvoiceActionsView] Error enviando correo automático: {ex}")
            elif accion == 'enviar-correo':
                from modules.tax_documents.invoicing.application.email_notification_service import EmailNotificationService
                email_dest = request.data.get('email')
                res = EmailNotificationService.send_document_email(
                    request.tenant.id, 'invoice', invoice_id, recipient_override=email_dest
                )
                if not res.get('success'):
                    return Response({'error': res.get('error')}, status=status.HTTP_400_BAD_REQUEST)
                return Response({'ok': True, 'mensaje': res.get('message'), 'recipient': res.get('recipient')})
            elif accion == 'cancelar':
                from modules.inventario.infrastructure.repository_impl import DjangoProductRepository, DjangoStockMovementRepository
                factura = CancelInvoice(
                    repo,
                    DjangoProductRepository(),
                    DjangoStockMovementRepository(),
                ).execute(invoice_id, request.tenant.id)
            else:
                return Response({'error': 'Acción no válida'}, status=status.HTTP_400_BAD_REQUEST)
            return Response(_invoice_dict(factura))
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f"Error al procesar acción {accion}: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)


class InvoiceXMLView(APIView):
    """Descarga el XML firmado de una factura"""
    def get(self, request, invoice_id):
        if e := verificar_modulo(request): return e
        repo = DjangoInvoiceRepository()
        factura = repo.find_by_id(invoice_id, request.tenant.id)
        if not factura or not factura.signed_xml:
            return Response({'error': 'XML no disponible'}, status=status.HTTP_404_NOT_FOUND)
        import os
        content = factura.signed_xml
        if content.endswith('.xml') and not content.startswith('<'):
            base_path = os.environ.get('LOCAL_STORAGE_PATH', '/home/erp/facturador/storage')
            xml_path = os.path.join(base_path, content.replace('\\', '/'))
            try:
                with open(xml_path, 'rb') as f:
                    content = f.read()
            except FileNotFoundError:
                return Response({'error': 'Archivo XML no encontrado en el servidor'}, status=status.HTTP_404_NOT_FOUND)

        from django.http import HttpResponse
        resp = HttpResponse(content, content_type='application/xml')
        resp['Content-Disposition'] = f'attachment; filename="{factura.access_key}.xml"'
        return resp


class CertificadoView(APIView):
    """Sube el certificado P12 del emisor"""
    from rest_framework.parsers import MultiPartParser
    parser_classes = [MultiPartParser]

    def post(self, request):
        if e := verificar_modulo(request): return e
        archivo = request.FILES.get('certificado')
        password = request.data.get('password', '')
        if not archivo:
            return Response({'error': 'No se envió certificado'}, status=status.HTTP_400_BAD_REQUEST)
        if not archivo.name.endswith('.p12'):
            return Response({'error': 'El archivo debe ser .p12'}, status=status.HTTP_400_BAD_REQUEST)

        carpeta = os.path.join(settings.MEDIA_ROOT, 'certificados')
        os.makedirs(carpeta, exist_ok=True)
        ruta = os.path.join(carpeta, f'cert_{request.tenant.id}.p12')
        with open(ruta, 'wb') as f:
            for chunk in archivo.chunks():
                f.write(chunk)

        repo_params = DjangoParameterRepository()
        from modules.parametros.application.use_cases import GuardarParametro
        from modules.shared.crypto import cifrar
        GuardarParametro(repo_params).execute(request.tenant.id, 'facturacion', 'signature_file', ruta)
        GuardarParametro(repo_params).execute(request.tenant.id, 'facturacion', 'signature_password', cifrar(password))

        return Response({'ok': True, 'mensaje': 'Certificado guardado correctamente'})


def _credit_note_dict(nc):
    return {
        'id': nc.id,
        'number': nc.number,
        'origin_invoice_number': nc.origin_invoice_number,
        'origin_invoice_key': nc.origin_invoice_key,
        'client': nc.client,
        'client_identification': nc.client_identification,
        'date': nc.date,
        'subtotal': str(nc.subtotal),
        'vat': str(nc.tax),
        'total': str(nc.total),
        'status': nc.status,
        'reason': nc.reason,
        'access_key': nc.access_key,
        'authorization_number': nc.authorization_number,
        'authorization_date': nc.authorization_date,
        'sri_status': nc.sri_status,
        'sri_message': nc.sri_message,
        'environment': nc.environment,
    }


class CreditNotesView(APIView):
    def get(self, request):
        if e := verificar_modulo(request): return e
        repo = DjangoCreditNoteRepository()
        notas = repo.list_by_tenant(request.tenant.id)
        return Response([_credit_note_dict(n) for n in notas])

    def post(self, request):
        if e := verificar_modulo(request): return e
        try:
            nc_repo = DjangoCreditNoteRepository()
            factura_repo = DjangoInvoiceRepository()
            emisor = _get_emisor(request.tenant.id)
            nc = CreateCreditNote(nc_repo, factura_repo).execute(
                tenant_id=request.tenant.id,
                data=request.data,
                issuer=emisor,
            )
            return Response(_credit_note_dict(nc), status=status.HTTP_201_CREATED)
        except (KeyError, ValueError) as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CreditNoteActionsView(APIView):
    def post(self, request, nc_id, accion):
        if e := verificar_modulo(request): return e
        repo = DjangoCreditNoteRepository()
        try:
            if accion == 'emitir':
                emisor = _get_emisor(request.tenant.id)
                cert_path = _param(request.tenant.id, 'facturacion', 'signature_file', '')
                cert_pass = _param(request.tenant.id, 'facturacion', 'signature_password', '')
                if not cert_path:
                    return Response(
                        {'error': 'Certificado P12 no configurado. Ve a Parametrización → Facturación'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Import SRI client tools if not present
                # Import SRI client tools if not present
                nc = EmitCreditNoteSRI(repo).execute(
                    nc_id, request.tenant.id, emisor, cert_path, cert_pass
                )
            elif accion == 'autorizar':
                pass
                from modules.inventario.infrastructure.repository_impl import DjangoProductRepository, DjangoStockMovementRepository
                nc = CheckCreditNoteAuthorizationSRI(
                    repo,
                    DjangoProductRepository(),
                    DjangoStockMovementRepository()
                ).execute(nc_id, request.tenant.id)
                if nc.status == 'authorized':
                    try:
                        from modules.tax_documents.invoicing.application.email_notification_service import EmailNotificationService
                        smtp_cfg = EmailNotificationService.get_smtp_config(request.tenant.id)
                        if smtp_cfg.get('enviar_automatico', True):
                            EmailNotificationService.send_document_email_async(request.tenant.id, 'credit_note', nc_id)
                    except Exception as ex:
                        print(f"[CreditNoteActionsView] Error enviando correo automático: {ex}")
            elif accion == 'enviar-correo':
                from modules.tax_documents.invoicing.application.email_notification_service import EmailNotificationService
                email_dest = request.data.get('email')
                res = EmailNotificationService.send_document_email(
                    request.tenant.id, 'credit_note', nc_id, recipient_override=email_dest
                )
                if not res.get('success'):
                    return Response({'error': res.get('error')}, status=status.HTTP_400_BAD_REQUEST)
                return Response({'ok': True, 'mensaje': res.get('message'), 'recipient': res.get('recipient')})
            else:
                return Response({'error': 'Acción no válida'}, status=status.HTTP_400_BAD_REQUEST)
            return Response(_credit_note_dict(nc))
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

def _withholding_dict(w):
    return {
        'id': w.id,
        'number': w.number,
        'supplier': w.supplier,
        'supplier_identification': w.supplier_identification,
        'supplier_id_type': w.supplier_id_type,
        'origin_invoice_number': w.origin_invoice_number,
        'fiscal_period': w.fiscal_period,
        'date': w.date.strftime('%Y-%m-%d') if hasattr(w.date, 'strftime') else str(w.date),
        'status': w.status,
        'total_withheld': str(w.total_withheld),
        'access_key': w.access_key,
        'authorization_number': w.authorization_number,
        'authorization_date': w.authorization_date,
        'sri_status': w.sri_status,
        'sri_message': w.sri_message,
        'environment': w.environment,
        'items': [
            {
                'type_code': i.type_code,
                'withholding_code': i.withholding_code,
                'tax_base': str(i.tax_base),
                'percentage': str(i.percentage),
                'withheld_value': str(i.withheld_value),
            } for i in w.items
        ]
    }


class WithholdingsView(APIView):
    def get(self, request):
        if e := verificar_modulo(request): return e
        repo = DjangoWithholdingRepository()
        retenciones = repo.list_by_tenant(request.tenant.id)
        return Response([_withholding_dict(r) for r in retenciones])

    def post(self, request):
        if e := verificar_modulo(request): return e
        try:
            repo = DjangoWithholdingRepository()
            emisor = _get_emisor(request.tenant.id)
            ret = CreateWithholding(repo).execute(
                tenant_id=request.tenant.id,
                data=request.data,
                issuer=emisor,
            )
            return Response(_withholding_dict(ret), status=status.HTTP_201_CREATED)
        except (KeyError, ValueError, BusinessError) as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class WithholdingActionsView(APIView):
    def post(self, request, ret_id, accion):
        if e := verificar_modulo(request): return e
        repo = DjangoWithholdingRepository()
        try:
            if accion == 'emitir':
                emisor = _get_emisor(request.tenant.id)
                cert_path = _param(request.tenant.id, 'facturacion', 'signature_file', '')
                cert_pass = _param(request.tenant.id, 'facturacion', 'signature_password', '')
                if not cert_path:
                    return Response(
                        {'error': 'Certificado P12 no configurado. Ve a Parametrización → Facturación'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                ret = EmitWithholdingSRI(repo).execute(
                    ret_id, request.tenant.id, emisor, cert_path, cert_pass
                )
            elif accion == 'autorizar':
                ret = CheckWithholdingAuthorizationSRI(repo).execute(ret_id, request.tenant.id)
                if ret.status == 'authorized':
                    try:
                        from modules.tax_documents.invoicing.application.email_notification_service import EmailNotificationService
                        smtp_cfg = EmailNotificationService.get_smtp_config(request.tenant.id)
                        if smtp_cfg.get('enviar_automatico', True):
                            EmailNotificationService.send_document_email_async(request.tenant.id, 'withholding', ret_id)
                    except Exception as ex:
                        print(f"[WithholdingActionsView] Error enviando correo automático: {ex}")
            elif accion == 'enviar-correo':
                from modules.tax_documents.invoicing.application.email_notification_service import EmailNotificationService
                email_dest = request.data.get('email')
                res = EmailNotificationService.send_document_email(
                    request.tenant.id, 'withholding', ret_id, recipient_override=email_dest
                )
                if not res.get('success'):
                    return Response({'error': res.get('error')}, status=status.HTTP_400_BAD_REQUEST)
                return Response({'ok': True, 'mensaje': res.get('message'), 'recipient': res.get('recipient')})
            else:
                return Response({'error': 'Acción no válida'}, status=status.HTTP_400_BAD_REQUEST)
            return Response(_withholding_dict(ret))
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class WithholdingXMLView(APIView):
    def get(self, request, ret_id):
        if e := verificar_modulo(request): return e
        from django.http import HttpResponse
        repo = DjangoWithholdingRepository()
        ret = repo.find_by_id(ret_id, request.tenant.id)
        if not ret:
            return Response({'error': 'Retención no encontrada'}, status=status.HTTP_404_NOT_FOUND)

        if ret.signed_xml:
            erp_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
            base_path = os.path.join(erp_dir, 'facturador', 'storage')
            xml_path = os.path.normpath(os.path.join(base_path, ret.signed_xml.replace('\\', '/')))
            if os.path.exists(xml_path):
                with open(xml_path, 'r', encoding='utf-8') as f:
                    xml_content = f.read()
                resp = HttpResponse(xml_content, content_type='application/xml; charset=utf-8')
                resp['Content-Disposition'] = f'attachment; filename="retencion-{ret.number}.xml"'
                return resp

        from ..infrastructure.external_clients.sri_xml_retencion import generate_xml_retencion
        emisor = _get_emisor(request.tenant.id)
        xml_content = generate_xml_retencion(ret, emisor)
        resp = HttpResponse(xml_content, content_type='application/xml; charset=utf-8')
        resp['Content-Disposition'] = f'attachment; filename="retencion-{ret.number}.xml"'
        return resp


def _dispatch_guide_dict(g):
    return {
        'id': g.id,
        'number': g.number,
        'date_emission': g.date_emission.strftime('%Y-%m-%d') if hasattr(g.date_emission, 'strftime') else str(g.date_emission),
        'start_date': g.start_date.strftime('%Y-%m-%d') if hasattr(g.start_date, 'strftime') else str(g.start_date),
        'end_date': g.end_date.strftime('%Y-%m-%d') if hasattr(g.end_date, 'strftime') else str(g.end_date),
        'starting_address': g.starting_address,
        'carrier_ruc': g.carrier_ruc,
        'carrier_name': g.carrier_name,
        'carrier_id_type': g.carrier_id_type,
        'vehicle_plate': g.vehicle_plate,
        'recipient_id': g.recipient_id,
        'recipient_id_type': g.recipient_id_type,
        'recipient_name': g.recipient_name,
        'recipient_address': g.recipient_address,
        'transfer_reason': g.transfer_reason,
        'route': g.route,
        'origin_doc_type': g.origin_doc_type,
        'origin_doc_number': g.origin_doc_number,
        'origin_doc_auth': g.origin_doc_auth,
        'origin_doc_date': g.origin_doc_date.strftime('%Y-%m-%d') if g.origin_doc_date and hasattr(g.origin_doc_date, 'strftime') else (str(g.origin_doc_date) if g.origin_doc_date else ''),
        'status': g.status,
        'environment': g.environment,
        'access_key': g.access_key,
        'authorization_number': g.authorization_number,
        'authorization_date': g.authorization_date,
        'sri_status': g.sri_status,
        'sri_message': g.sri_message,
        'items': [
            {
                'description': i.description,
                'quantity': str(i.quantity),
                'internal_code': i.internal_code,
            } for i in g.items
        ]
    }


class DispatchGuidesView(APIView):
    def get(self, request):
        if e := verificar_modulo(request): return e
        repo = DjangoDispatchGuideRepository()
        guides = repo.list_by_tenant(request.tenant.id)
        return Response([_dispatch_guide_dict(g) for g in guides])

    def post(self, request):
        if e := verificar_modulo(request): return e
        try:
            repo = DjangoDispatchGuideRepository()
            emisor = _get_emisor(request.tenant.id)
            guide = CreateDispatchGuide(repo).execute(
                tenant_id=request.tenant.id,
                data=request.data,
                issuer=emisor,
            )
            return Response(_dispatch_guide_dict(guide), status=status.HTTP_201_CREATED)
        except (KeyError, ValueError, BusinessError) as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f"Error interno: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DispatchGuideActionsView(APIView):
    def post(self, request, guide_id, accion):
        if e := verificar_modulo(request): return e
        repo = DjangoDispatchGuideRepository()
        try:
            if accion == 'emitir':
                emisor = _get_emisor(request.tenant.id)
                cert_path = _param(request.tenant.id, 'facturacion', 'signature_file', '')
                cert_pass = _param(request.tenant.id, 'facturacion', 'signature_password', '')
                if not cert_path:
                    return Response(
                        {'error': 'Certificado P12 no configurado. Ve a Parametrización → Facturación'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                guide = EmitDispatchGuideSRI(repo).execute(
                    guide_id, request.tenant.id, emisor, cert_path, cert_pass
                )
            elif accion == 'autorizar':
                guide = CheckDispatchGuideAuthorizationSRI(repo).execute(guide_id, request.tenant.id)
                if guide.status == 'AUTORIZADA':
                    from ...application.email_notification_service import EmailNotificationService
                    auto_envio = _param(request.tenant.id, 'correo', 'enviar_automatico', 'true') == 'true'
                    if auto_envio:
                        EmailNotificationService.send_document_email_async(
                            tenant_id=request.tenant.id,
                            doc_type='dispatch_guide',
                            doc_id=guide.id
                        )
            elif accion == 'enviar-correo':
                from ...application.email_notification_service import EmailNotificationService
                override_email = request.data.get('email') if isinstance(request.data, dict) else None
                res = EmailNotificationService.send_document_email(
                    tenant_id=request.tenant.id,
                    doc_type='dispatch_guide',
                    doc_id=guide_id,
                    recipient_override=override_email
                )
                if not res.get('success'):
                    return Response({'error': res.get('error', 'Error al enviar correo')}, status=status.HTTP_400_BAD_REQUEST)
                return Response({'ok': True, 'mensaje': res.get('message', 'Correo enviado exitosamente')})
            else:
                return Response({'error': 'Acción no válida'}, status=status.HTTP_400_BAD_REQUEST)
            return Response(_dispatch_guide_dict(guide))
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DispatchGuideXMLView(APIView):
    def get(self, request, guide_id):
        if e := verificar_modulo(request): return e
        from django.http import HttpResponse
        repo = DjangoDispatchGuideRepository()
        guide = repo.find_by_id(guide_id, request.tenant.id)
        if not guide:
            return Response({'error': 'Guía de remisión no encontrada'}, status=status.HTTP_404_NOT_FOUND)

        if guide.signed_xml:
            erp_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
            base_path = os.path.join(erp_dir, 'facturador', 'storage')
            xml_path = os.path.normpath(os.path.join(base_path, guide.signed_xml.replace('\\', '/')))
            if os.path.exists(xml_path):
                with open(xml_path, 'r', encoding='utf-8') as f:
                    xml_content = f.read()
                resp = HttpResponse(xml_content, content_type='application/xml; charset=utf-8')
                resp['Content-Disposition'] = f'attachment; filename="guia-{guide.number}.xml"'
                return resp

        from ..infrastructure.external_clients.sri_xml_guia_remision import generate_xml_guia_remision
        emisor = _get_emisor(request.tenant.id)
        xml_content = generate_xml_guia_remision(guide, emisor)
        resp = HttpResponse(xml_content, content_type='application/xml; charset=utf-8')
        resp['Content-Disposition'] = f'attachment; filename="guia-{guide.number}.xml"'
        return resp


def _purchase_settlement_dict(s):
    return {
        'id': s.id,
        'number': s.number,
        'supplier': s.supplier,
        'supplier_identification': s.supplier_identification,
        'supplier_id_type': s.supplier_id_type,
        'supplier_address': s.supplier_address,
        'supplier_email': s.supplier_email,
        'date': s.date.strftime('%Y-%m-%d') if hasattr(s.date, 'strftime') else str(s.date),
        'payment_method': s.payment_method,
        'status': s.status,
        'notes': s.notes,
        'environment': s.environment,
        'subtotal_0': str(s.subtotal_0),
        'subtotal_iva': str(s.subtotal_iva),
        'total_discount': str(s.total_discount),
        'vat': str(s.vat),
        'total': str(s.total),
        'access_key': s.access_key,
        'authorization_number': s.authorization_number,
        'authorization_date': s.authorization_date,
        'sri_status': s.sri_status,
        'sri_message': s.sri_message,
        'items': [
            {
                'description': i.description,
                'quantity': str(i.quantity),
                'unit_price': str(i.unit_price),
                'discount': str(i.discount),
                'vat_rate': str(i.vat_rate),
                'product_code': i.product_code,
                'subtotal': str(i.subtotal),
            } for i in s.items
        ]
    }


class PurchaseSettlementsView(APIView):
    def get(self, request):
        if e := verificar_modulo(request): return e
        repo = DjangoPurchaseSettlementRepository()
        settlements = repo.list_by_tenant(request.tenant.id)
        return Response([_purchase_settlement_dict(s) for s in settlements])

    def post(self, request):
        if e := verificar_modulo(request): return e
        try:
            repo = DjangoPurchaseSettlementRepository()
            emisor = _get_emisor(request.tenant.id)
            settlement = CreatePurchaseSettlement(repo).execute(
                tenant_id=request.tenant.id,
                data=request.data,
                issuer=emisor,
            )
            return Response(_purchase_settlement_dict(settlement), status=status.HTTP_201_CREATED)
        except (KeyError, ValueError, BusinessError) as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f"Error interno: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PurchaseSettlementActionsView(APIView):
    def post(self, request, settlement_id, accion):
        if e := verificar_modulo(request): return e
        repo = DjangoPurchaseSettlementRepository()
        try:
            if accion == 'emitir':
                emisor = _get_emisor(request.tenant.id)
                cert_path = _param(request.tenant.id, 'facturacion', 'signature_file', '')
                cert_pass = _param(request.tenant.id, 'facturacion', 'signature_password', '')
                if not cert_path:
                    return Response(
                        {'error': 'Certificado P12 no configurado. Ve a Parametrización → Facturación'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                settlement = EmitPurchaseSettlementSRI(repo).execute(
                    settlement_id, request.tenant.id, emisor, cert_path, cert_pass
                )
            elif accion == 'autorizar':
                settlement = CheckPurchaseSettlementAuthorizationSRI(repo).execute(settlement_id, request.tenant.id)
                if settlement.status == 'AUTORIZADA':
                    from ...application.email_notification_service import EmailNotificationService
                    auto_envio = _param(request.tenant.id, 'correo', 'enviar_automatico', 'true') == 'true'
                    if auto_envio:
                        EmailNotificationService.send_document_email_async(
                            tenant_id=request.tenant.id,
                            doc_type='purchase_settlement',
                            doc_id=settlement.id
                        )
            elif accion == 'enviar-correo':
                from ...application.email_notification_service import EmailNotificationService
                override_email = request.data.get('email') if isinstance(request.data, dict) else None
                res = EmailNotificationService.send_document_email(
                    tenant_id=request.tenant.id,
                    doc_type='purchase_settlement',
                    doc_id=settlement_id,
                    recipient_override=override_email
                )
                if not res.get('success'):
                    return Response({'error': res.get('error', 'Error al enviar correo')}, status=status.HTTP_400_BAD_REQUEST)
                return Response({'ok': True, 'mensaje': res.get('message', 'Correo enviado exitosamente')})
            else:
                return Response({'error': 'Acción no válida'}, status=status.HTTP_400_BAD_REQUEST)
            return Response(_purchase_settlement_dict(settlement))
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PurchaseSettlementXMLView(APIView):
    def get(self, request, settlement_id):
        if e := verificar_modulo(request): return e
        from django.http import HttpResponse
        repo = DjangoPurchaseSettlementRepository()
        settlement = repo.find_by_id(settlement_id, request.tenant.id)
        if not settlement:
            return Response({'error': 'Liquidación de compra no encontrada'}, status=status.HTTP_404_NOT_FOUND)

        if settlement.signed_xml:
            erp_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
            base_path = os.path.join(erp_dir, 'facturador', 'storage')
            xml_path = os.path.normpath(os.path.join(base_path, settlement.signed_xml.replace('\\', '/')))
            if os.path.exists(xml_path):
                with open(xml_path, 'r', encoding='utf-8') as f:
                    xml_content = f.read()
                resp = HttpResponse(xml_content, content_type='application/xml; charset=utf-8')
                resp['Content-Disposition'] = f'attachment; filename="liquidacion-{settlement.number}.xml"'
                return resp

        from ..infrastructure.external_clients.sri_xml_liquidacion_compra import generate_xml_liquidacion_compra
        emisor = _get_emisor(request.tenant.id)
        xml_content = generate_xml_liquidacion_compra(settlement, emisor)
        resp = HttpResponse(xml_content, content_type='application/xml; charset=utf-8')
        resp['Content-Disposition'] = f'attachment; filename="liquidacion-{settlement.number}.xml"'
        return resp


from rest_framework.permissions import AllowAny

class SRIWebhookView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        tenant_id = request.data.get('tenant_id')
        invoice_id = request.data.get('invoice_id')
        status_sri = request.data.get('status')
        message = request.data.get('message', '')
        authorized_file = request.data.get('authorized_file', '')

        doc_type = request.data.get('doc_type', 'invoice')

        if not tenant_id or not invoice_id:
            return Response({'error': 'Missing tenant_id or invoice_id'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            if doc_type == 'credit_note':
                from modules.tax_documents.invoicing.infrastructure.persistence.repository_impl import DjangoCreditNoteRepository
                repo = DjangoCreditNoteRepository()
            elif doc_type == 'withholding':
                repo = DjangoWithholdingRepository()
            elif doc_type == 'dispatch_guide':
                repo = DjangoDispatchGuideRepository()
            elif doc_type == 'purchase_settlement':
                repo = DjangoPurchaseSettlementRepository()
            else:
                repo = DjangoInvoiceRepository()

            doc = repo.find_by_id(int(invoice_id), int(tenant_id))
            if not doc:
                return Response({'error': f'{doc_type} not found'}, status=status.HTTP_404_NOT_FOUND)

            doc.sri_status = status_sri
            doc.sri_message = message
            
            if status_sri == 'AUTORIZADA':
                doc.status = 'authorized'
                if authorized_file:
                    doc.signed_xml = authorized_file
                # Disparar envío automático de correo al autorizar
                try:
                    from modules.tax_documents.invoicing.application.email_notification_service import EmailNotificationService
                    smtp_cfg = EmailNotificationService.get_smtp_config(int(tenant_id))
                    if smtp_cfg.get('enviar_automatico', True):
                        EmailNotificationService.send_document_email_async(int(tenant_id), doc_type, int(invoice_id))
                except Exception as ex:
                    print(f"[SRIWebhookView] Error disparando email automático: {ex}")
            elif status_sri == 'RECHAZADA':
                doc.status = 'not_authorized'

            repo.save(doc)
            return Response({'success': True})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TestSMTPView(APIView):
    """Prueba la conexión y credenciales SMTP enviando un correo de verificación."""
    def post(self, request):
        if e := verificar_modulo(request): return e
        test_email = request.data.get('email', '').strip()
        if not test_email or '@' not in test_email:
            return Response({'error': 'Debe ingresar un correo electrónico de destino válido.'}, status=status.HTTP_400_BAD_REQUEST)

        from modules.tax_documents.invoicing.application.email_notification_service import EmailNotificationService
        result = EmailNotificationService.test_smtp_connection(request.tenant.id, test_email)
        http_status = status.HTTP_200_OK if result.get('success') else status.HTTP_400_BAD_REQUEST
        return Response(result, status=http_status)



