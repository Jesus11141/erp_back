from datetime import date
from django.http import JsonResponse
from ..infrastructure.repository_impl import DjangoTenantRepository
from ..application.use_cases import GetTenantConfig

class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.repo = DjangoTenantRepository()
        self.use_case = GetTenantConfig(self.repo)

    def __call__(self, request):
        tenant_from_token = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            try:
                from rest_framework_simplejwt.tokens import AccessToken
                raw_token = auth_header.split(' ')[1]
                token_data = AccessToken(raw_token)
                tenant_id = token_data.get('tenant_id')
                if tenant_id and tenant_id > 0:
                    from .django_models import TenantModel
                    db_t = TenantModel.objects.filter(id=tenant_id).first()
                    if db_t:
                        tenant_from_token = self.repo._to_entity(db_t)
            except Exception:
                pass

        if tenant_from_token:
            request.tenant = tenant_from_token
        else:
            host = request.get_host().split(':')[0]
            # 1. Buscar por host completo (IP pública o dominio completo)
            tenant = self.repo.find_by_subdomain(host)
            if not tenant:
                # 2. Buscar por primer segmento del subdominio
                subdomain = host.split('.')[0]
                tenant = self.repo.find_by_subdomain(subdomain)
            if not tenant:
                # 3. Fallback garantizado al Tenant Maestro (ID 1)
                from .django_models import TenantModel
                db_t = TenantModel.objects.filter(id=1).first()
                if db_t:
                    tenant = self.repo._to_entity(db_t)

            request.tenant = tenant

        path = request.path_info
        if request.tenant and not path.startswith('/api/superadmin/') and not path.startswith('/admin/'):
            from .django_models import TenantModel
            db_tenant = TenantModel.objects.filter(id=request.tenant.id).first()
            if db_tenant:
                is_expired = bool(db_tenant.expiration_date and db_tenant.expiration_date < date.today())
                is_suspended = db_tenant.subscription_state in ['suspendida', 'vencida'] or not db_tenant.is_active or is_expired

                if is_suspended:
                    msg = 'Subscription expired on ' + str(db_tenant.expiration_date) + '. Please contact support to renew your plan.' if is_expired else 'Subscription suspended by administrator.'
                    return JsonResponse({
                        'error': msg,
                        'subscription_state': 'vencida' if is_expired else db_tenant.subscription_state
                    }, status=403)

        return self.get_response(request)
