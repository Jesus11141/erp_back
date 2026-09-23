from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from modules.tenants.infrastructure.django_models import PlanModel
from rest_framework.response import Response
from rest_framework import status
from ...infrastructure.repository_impl import DjangoSuperAdminRepository
from ...application.use_cases import (
    ListTenants, CreateTenant, UpdateTenant,
    ToggleTenant, ToggleModule, GetStatistics,
)

def _verify_superadmin(request):
    user = getattr(request, 'user', None)
    if not user:
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
    
    is_super = user.role == 'superadmin' or (user.permissions and '*' in user.permissions)
    if not is_super:
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
    return None

def _tenant_dict(t) -> dict:
    return {
        'id': t.id,
        'name': t.name,
        'subdomain': t.subdomain,
        'active': t.active,
        'plan': t.plan,
        'modules': t.modules,
        'primary_color': t.primary_color,
        'secondary_color': t.secondary_color,
        'logo_url': t.logo_url,
        'creation_date': t.creation_date,
        'total_users': t.total_users,
        'ruc': getattr(t, 'ruc', ''),
        'contact_email': getattr(t, 'contact_email', ''),
        'contact_phone': getattr(t, 'contact_phone', ''),
        'contract_start_date': getattr(t, 'contract_start_date', None),
        'expiration_date': getattr(t, 'expiration_date', None),
        'subscription_status': getattr(t, 'subscription_status', 'active'),
        'remaining_days': t.remaining_days,
        'is_expired': t.is_expired,
        'admin_email': getattr(t, 'admin_email', ''),
        'max_devices': getattr(t, 'max_devices', 1),
    }

class TenantsView(APIView):

    def get(self, request):
        if error := _verify_superadmin(request): return error
        repo = DjangoSuperAdminRepository()
        tenants = ListTenants(repo).execute()
        return Response([_tenant_dict(t) for t in tenants])

    def post(self, request):
        if error := _verify_superadmin(request): return error
        try:
            repo = DjangoSuperAdminRepository()
            tenant = CreateTenant(repo).execute(request.data)
            return Response(_tenant_dict(tenant), status=status.HTTP_201_CREATED)
        except (ValueError, Exception) as e:
            msg = str(e)
            if 'tenants_subdominio_key' in msg or 'subdominio' in msg or 'subdomain' in msg:
                msg = "The entered subdomain already exists. Please choose a different subdomain."
            return Response({'error': msg}, status=status.HTTP_400_BAD_REQUEST)

class TenantDetailView(APIView):

    def get(self, request, tenant_id: int):
        if error := _verify_superadmin(request): return error
        repo = DjangoSuperAdminRepository()
        tenant = repo.find_tenant(tenant_id)
        if not tenant:
            return Response({'error': 'Company not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(_tenant_dict(tenant))

    def put(self, request, tenant_id: int):
        if error := _verify_superadmin(request): return error
        try:
            repo = DjangoSuperAdminRepository()
            tenant = UpdateTenant(repo).execute(tenant_id, request.data)
            return Response(_tenant_dict(tenant))
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class TenantToggleView(APIView):

    def post(self, request, tenant_id: int):
        if error := _verify_superadmin(request): return error
        try:
            activate = request.data.get('activate', True)
            repo = DjangoSuperAdminRepository()
            tenant = ToggleTenant(repo).execute(tenant_id, activate)
            return Response(_tenant_dict(tenant))
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ModuleToggleView(APIView):

    def post(self, request, tenant_id: int, module: str):
        if error := _verify_superadmin(request): return error
        try:
            activate = request.data.get('activar', True)
            repo = DjangoSuperAdminRepository()
            tenant = ToggleModule(repo).execute(tenant_id, module, activate)
            return Response(_tenant_dict(tenant))
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class StatisticsView(APIView):

    def get(self, request):
        if error := _verify_superadmin(request): return error
        stats = GetStatistics(DjangoSuperAdminRepository()).execute()
        return Response(stats)


def _plan_dict(p: PlanModel) -> dict:
    return {
        'id': p.id,
        'key': p.key,
        'name': p.name,
        'price': str(p.price),
        'max_users': p.max_users,
        'max_devices': p.max_devices,
        'modules': p.modules,
    }

class PlanView(APIView):
    def get(self, request):
        if error := _verify_superadmin(request): return error
        planes = PlanModel.objects.all().order_by('price')
        return Response([_plan_dict(p) for p in planes])

    def post(self, request):
        if error := _verify_superadmin(request): return error
        data = request.data
        try:
            p = PlanModel.objects.create(
                key=data.get('key', data.get('name', '').lower().replace(' ', '_')),
                name=data.get('name'),
                price=data.get('price', 0),
                max_users=data.get('max_users', 1),
                max_devices=data.get('max_devices', 1),
                modules=data.get('modules', [])
            )
            return Response(_plan_dict(p), status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class PlanDetailView(APIView):
    def put(self, request, plan_id: int):
        if error := _verify_superadmin(request): return error
        try:
            p = PlanModel.objects.get(id=plan_id)
            data = request.data
            p.name = data.get('name', p.name)
            p.price = data.get('price', p.price)
            p.max_users = data.get('max_users', p.max_users)
            p.max_devices = data.get('max_devices', p.max_devices)
            p.modules = data.get('modules', p.modules)
            p.save()
            return Response(_plan_dict(p))
        except PlanModel.DoesNotExist:
            return Response({'error': 'Plan not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, plan_id: int):
        if error := _verify_superadmin(request): return error
        try:
            p = PlanModel.objects.get(id=plan_id)
            p.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except PlanModel.DoesNotExist:
            return Response({'error': 'Plan not found'}, status=status.HTTP_404_NOT_FOUND)

class SuperAdminTenantFeaturesView(APIView):
    def get(self, request, tenant_id: int):
        if error := _verify_superadmin(request): return error
        from modules.tenants.infrastructure.django_models import TenantFeatureToggleModel
        features = TenantFeatureToggleModel.objects.filter(tenant_id=tenant_id)
        return Response({f.feature_key: f.is_enabled for f in features})

    def post(self, request, tenant_id: int):
        if error := _verify_superadmin(request): return error
        feature_key = request.data.get('feature_key')
        is_enabled = request.data.get('is_enabled', False)
        from modules.tenants.infrastructure.django_models import TenantFeatureToggleModel
        feature, _ = TenantFeatureToggleModel.objects.update_or_create(
            tenant_id=tenant_id,
            feature_key=feature_key,
            defaults={'is_enabled': is_enabled}
        )
        return Response({feature.feature_key: feature.is_enabled})

