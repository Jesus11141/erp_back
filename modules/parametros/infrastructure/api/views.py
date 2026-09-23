from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import os
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from cryptography.hazmat.primitives.serialization import pkcs12
from ...infrastructure.repository_impl import DjangoParameterRepository
from ...application.use_cases import GetAllParameters, SaveMultipleParameters
from ...domain.entities import CATALOG

def _verify_module(request, module: str):
    if not request.tenant or not request.tenant.has_module(module):
        return Response({'error': 'Module not available'}, status=status.HTTP_403_FORBIDDEN)
    return None

class ParametersView(APIView):
    """Gets all tenant parameters grouped by module."""

    def get(self, request):
        if not request.tenant:
            return Response({'error': 'Company not found'}, status=status.HTTP_404_NOT_FOUND)
        repo = DjangoParameterRepository()
        result = GetAllParameters(repo).execute(request.tenant.id)
        return Response(result)

class ModuleParametersView(APIView):
    """Gets and saves parameters for a specific module."""

    def get(self, request, module: str):
        if not request.tenant:
            return Response({'error': 'Company not found'}, status=status.HTTP_404_NOT_FOUND)
        if module not in CATALOG:
            return Response({'error': f"Module '{module}' does not exist"}, status=status.HTTP_404_NOT_FOUND)
        repo = DjangoParameterRepository()
        result = GetAllParameters(repo).execute(request.tenant.id)
        return Response(result.get(module, {}))

    def post(self, request, module: str):
        if not request.tenant:
            return Response({'error': 'Company not found'}, status=status.HTTP_404_NOT_FOUND)
        if module not in CATALOG:
            return Response({'error': f"Module '{module}' does not exist"}, status=status.HTTP_404_NOT_FOUND)
        try:
            repo = DjangoParameterRepository()
            saved = SaveMultipleParameters(repo).execute(
                tenant_id=request.tenant.id,
                module=module,
                parameters=request.data,
            )
            
            # Hook to update the actual InvoiceSequentialModel if ultima_factura is sent
            if module == 'facturacion' and 'ultima_factura' in request.data:
                try:
                    nuevo_secuencial = int(request.data['ultima_factura'])
                    from modules.tax_documents.invoicing.infrastructure.persistence.django_models import InvoiceSequentialModel
                    estab = request.data.get('establecimiento', '001')
                    pto_emi = request.data.get('punto_emision', '001')
                    
                    seq, created = InvoiceSequentialModel.objects.get_or_create(
                        tenant_id=request.tenant.id,
                        estab=estab,
                        pto_emi=pto_emi,
                        defaults={'ultimo': nuevo_secuencial}
                    )
                    if not created:
                        seq.ultimo = nuevo_secuencial
                        seq.save()
                except Exception as e:
                    print(f"Error actualizando InvoiceSequentialModel desde parametros: {e}")

            return Response({'saved': len(saved), 'module': module})
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class CatalogView(APIView):
    """Returns the complete catalog of available parameters."""

    def get(self, request):
        return Response({
            module: {
                key: {
                    'label': info['label'],
                    'type': info['type'],
                    'default': info['default'],
                    'options': info.get('options'),
                }
                for key, info in keys.items()
            }
            for module, keys in CATALOG.items()
        })

class SignatureUploadView(APIView):
    """Handles the upload of the electronic signature (.p12) file."""

    def post(self, request):
        if not request.tenant:
            return Response({'error': 'Company not found'}, status=status.HTTP_404_NOT_FOUND)

        file = request.FILES.get('signature')
        if not file:
            return Response({'error': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure signatures directory exists
        path = f'firmas/tenant_{request.tenant.id}_{file.name}'
        
        # Save or overwrite the file
        if default_storage.exists(path):
            default_storage.delete(path)
        
        saved_path = default_storage.save(path, ContentFile(file.read()))

        # Save the path to the parameters database
        repo = DjangoParameterRepository()
        SaveMultipleParameters(repo).execute(
            tenant_id=request.tenant.id,
            module='facturacion',
            parameters={'signature_file': saved_path}
        )

        return Response({'path': saved_path})

class ValidateSignatureView(APIView):
    """Validates the electronic signature (.p12) password."""

    def post(self, request):
        if not request.tenant:
            return Response({'error': 'Company not found'}, status=status.HTTP_404_NOT_FOUND)

        password = request.data.get('password', '')
        file = request.FILES.get('signature')
        
        p12_data = None
        if file:
            p12_data = file.read()
        else:
            repo = DjangoParameterRepository()
            param = repo.get(request.tenant.id, 'facturacion', 'signature_file')
            if not param or not param.value:
                return Response({'status': 'business_error', 'message': 'No signature found to test the password.'}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                file_path = default_storage.path(param.value)
                if not os.path.exists(file_path):
                    return Response({'status': 'business_error', 'message': 'Signature file not found on the server.'}, status=status.HTTP_400_BAD_REQUEST)
                with open(file_path, 'rb') as f:
                    p12_data = f.read()
            except NotImplementedError:
                # Si el storage no soporta path() local (ej. S3), se debe usar open()
                with default_storage.open(param.value, 'rb') as f:
                    p12_data = f.read()

        try:
            pkcs12.load_key_and_certificates(p12_data, password.encode('utf-8'))
            return Response({'status': 'success', 'message': 'Correct password. Signature is valid.'})
        except ValueError:
            return Response({'status': 'business_error', 'message': 'Incorrect password or invalid signature file.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'status': 'system_error', 'message': f'Error reading signature: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
