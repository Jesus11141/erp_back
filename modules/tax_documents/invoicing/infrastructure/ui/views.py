import os
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ...infrastructure.persistence.repository_impl import DjangoInvoiceRepository, DjangoCreditNoteRepository
from ...application.use_cases import (
    CreateInvoice, EmitInvoiceSRI, CheckInvoiceAuthorizationSRI, CancelInvoice, ListInvoices,
    CreateCreditNote, EmitCreditNoteSRI, CheckCreditNoteAuthorizationSRI
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
        'sri_status': f.sri_status,
        'sri_message': f.sri_message,
        'environment': f.environment,
    }


def api_success(data, status_code=status.HTTP_200_OK):
    return Response({
        "status": "success",
        "data": data if isinstance(data, list) else [data]
    }, status=status_code)


def api_business_error(message, field=None, code="BUSINESS_ERROR", status_code=status.HTTP_400_BAD_REQUEST):
    return Response({
        "status": "business_error",
        "data": [{
            "code": code,
            "field": field,
            "message": str(message)
        }]
    }, status=status_code)


def api_system_error(message, detail=None, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR):
    return Response({
        "status": "system_error",
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
            else:
                return Response({'error': 'Acción no válida'}, status=status.HTTP_400_BAD_REQUEST)
            return Response(_credit_note_dict(nc))
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

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
            elif status_sri == 'RECHAZADA':
                doc.status = 'not_authorized'

            repo.save(doc)
            return Response({'success': True})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

