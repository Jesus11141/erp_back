import os
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser
from ...infrastructure.repository_impl import DjangoTenantRepository
from ...application.use_cases import ActivateModule, DeactivateModule

class TenantConfigView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        if not request.tenant:
            return Response({'error': 'Tenant not found'}, status=status.HTTP_404_NOT_FOUND)
        t = request.tenant
        return Response({
            'name': t.name,
            'logo_url': t.logo_url,
            'primary_color': t.primary_color,
            'secondary_color': t.secondary_color,
            'modules': t.modules,
            'subscription_state': getattr(t, 'subscription_state', 'activa'),
        })

import time

class TenantLogoView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request):
        if not request.tenant:
            return Response({'error': 'Tenant not found'}, status=status.HTTP_404_NOT_FOUND)
        file = request.FILES.get('logo')
        if not file:
            return Response({'error': 'No file sent'}, status=status.HTTP_400_BAD_REQUEST)
        ext = os.path.splitext(file.name)[1].lower()
        if ext not in ['.jpg', '.jpeg', '.png', '.svg', '.webp']:
            return Response({'error': 'Invalid format. Use JPG, PNG, SVG or WEBP'}, status=status.HTTP_400_BAD_REQUEST)
        folder = os.path.join(settings.MEDIA_ROOT, 'logos')
        os.makedirs(folder, exist_ok=True)
        name = f'logo_{request.tenant.id}_{int(time.time())}{ext}'
        path = os.path.join(folder, name)
        with open(path, 'wb') as f:
            for chunk in file.chunks():
                f.write(chunk)
        try:
            os.chmod(path, 0o644)
        except Exception:
            pass
        logo_url = f'{settings.MEDIA_URL}logos/{name}'
        from ...infrastructure.django_models import TenantModel
        TenantModel.objects.filter(id=request.tenant.id).update(logo_url=logo_url)
        from modules.parametros.infrastructure.django_models import ParameterModel
        ParameterModel.objects.update_or_create(
            tenant_id=request.tenant.id,
            module='general',
            key='logo_url',
            defaults={'value': logo_url}
        )
        return Response({'logo_url': logo_url})


class ModuleView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.repo = DjangoTenantRepository()

    def post(self, request, module):
        caso = ActivateModule(self.repo)
        tenant = caso.execute(request.tenant.subdomain, module)
        return Response({'modules': tenant.modules})

    def delete(self, request, module):
        caso = DeactivateModule(self.repo)
        tenant = caso.execute(request.tenant.subdomain, module)
        return Response({'modules': tenant.modules})

class TenantFeaturesView(APIView):
    def get(self, request):
        if not request.tenant:
            return Response({'error': 'Tenant not found'}, status=status.HTTP_404_NOT_FOUND)
        from ...infrastructure.django_models import TenantFeatureToggleModel
        features = TenantFeatureToggleModel.objects.filter(tenant_id=request.tenant.id)
        result = {f.feature_key: f.is_enabled for f in features}
        return Response(result)

