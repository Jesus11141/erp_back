"""
Controladores REST API para Importación Masiva Excel y Descarga de Plantillas.
"""

from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from modules.importador.application.excel_import_service import ExcelImportService


def _verify_tenant(request):
    if not hasattr(request, 'tenant') or not request.tenant:
        return Response({'error': 'No se identificó la empresa (Tenant requerido)'}, status=status.HTTP_400_BAD_REQUEST)
    return None


class TemplateDownloadView(APIView):
    permission_classes = [AllowAny]
    """
    Descarga la plantilla oficial en Excel (.xlsx) con estilos y datos de ejemplo
    para una entidad determinada: productos, clientes, proveedores, plan-cuentas.
    """
    def get(self, request, entity: str):
        try:
            content, filename = ExcelImportService.generate_template(entity)
            response = HttpResponse(
                content,
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f'Error al generar plantilla: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BulkImportView(APIView):
    permission_classes = [AllowAny]
    """
    Recibe un archivo Excel (.xlsx / .xls) o .csv para procesar la importación masiva.
    """
    def post(self, request, entity: str):
        err = _verify_tenant(request)
        if err:
            return err

        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response({'error': 'No se envió ningún archivo para importar. Debe enviar el campo "file".'}, status=status.HTTP_400_BAD_REQUEST)

        mode = request.POST.get('mode', 'upsert').strip().lower()
        if mode not in ['upsert', 'create_only']:
            mode = 'upsert'

        tenant_id = request.tenant.id
        user_id = getattr(request.user, 'id', 0) if hasattr(request, 'user') else 0
        entity_norm = entity.lower().strip()

        try:
            if entity_norm in ['productos', 'inventario', 'items']:
                result = ExcelImportService.import_products(
                    tenant_id=tenant_id,
                    file_obj=uploaded_file,
                    filename=uploaded_file.name,
                    mode=mode,
                    user_id=user_id
                )
            elif entity_norm in ['clientes', 'customers']:
                result = ExcelImportService.import_clients(
                    tenant_id=tenant_id,
                    file_obj=uploaded_file,
                    filename=uploaded_file.name,
                    mode=mode
                )
            elif entity_norm in ['proveedores', 'suppliers']:
                result = ExcelImportService.import_suppliers(
                    tenant_id=tenant_id,
                    file_obj=uploaded_file,
                    filename=uploaded_file.name,
                    mode=mode
                )
            elif entity_norm in ['plan-cuentas', 'cuentas', 'plancuentas', 'accounts']:
                result = ExcelImportService.import_accounts(
                    tenant_id=tenant_id,
                    file_obj=uploaded_file,
                    filename=uploaded_file.name,
                    mode=mode
                )
            else:
                return Response({'error': f"Entidad '{entity}' no soportada para importación masiva."}, status=status.HTTP_400_BAD_REQUEST)

            http_status = status.HTTP_200_OK if result.get('success') else status.HTTP_400_BAD_REQUEST
            return Response(result, status=http_status)

        except Exception as e:
            return Response({'error': f'Error procesando el archivo de importación: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
