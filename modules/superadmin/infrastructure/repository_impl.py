from decimal import Decimal
from datetime import date, datetime
from typing import Optional, List
from ..domain.entities import TenantSummary, GlobalStatistics
from ..domain.repositories import SuperAdminRepository
from modules.tenants.infrastructure.django_models import TenantModel, TenantModuloModel
from modules.planes.domain.entities import PLANS

def _parse_date(val):
    if not val:
        return None
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        try:
            return date.fromisoformat(val.strip()[:10])
        except (ValueError, TypeError):
            return None
    return None

class DjangoSuperAdminRepository(SuperAdminRepository):

    def _to_entity(self, m: TenantModel) -> TenantSummary:
        from modules.auth.infrastructure.django_models import UserModel
        modules = list(m.modulos.filter(is_active=True).values_list('module', flat=True))
        user_count = UserModel.objects.filter(tenant_id=m.id).count()
        admin_u = UserModel.objects.filter(tenant_id=m.id).order_by('id').first()
        admin_email = admin_u.email if admin_u else getattr(m, 'contact_email', '')
        summary = TenantSummary(
            id=m.id,
            name=m.name,
            subdomain=m.subdomain,
            active=m.is_active,
            plan=getattr(m, 'plan', 'basic'),
            modules=modules,
            primary_color=m.primary_color,
            secondary_color=m.secondary_color,
            logo_url=m.logo_url,
            creation_date=m.created,
            total_users=user_count,
            ruc=getattr(m, 'ruc', ''),
            contact_email=getattr(m, 'contact_email', ''),
            contact_phone=getattr(m, 'contact_phone', ''),
            contract_start_date=_parse_date(getattr(m, 'contract_start_date', None)),
            expiration_date=_parse_date(getattr(m, 'expiration_date', None)),
            subscription_status=getattr(m, 'subscription_state', 'active'),
            max_devices=m.max_devices,
        )
        setattr(summary, 'admin_email', admin_email)
        return summary

    def list_tenants(self) -> List[TenantSummary]:
        return [self._to_entity(m) for m in TenantModel.objects.all().order_by('-created')]

    def find_tenant(self, tenant_id: int) -> Optional[TenantSummary]:
        try:
            return self._to_entity(TenantModel.objects.get(id=tenant_id))
        except TenantModel.DoesNotExist:
            return None

    def create_tenant(self, data: dict) -> TenantSummary:
        from modules.auth.infrastructure.django_models import UserModel
        subdomain = data.get('subdomain', '').strip().lower()
        if not subdomain:
            raise ValueError("Subdomain is mandatory")
        if TenantModel.objects.filter(subdominio=subdomain).exists():
            raise ValueError(f"The subdomain '{subdomain}' already belongs to another registered company. Please enter a different one (e.g. {subdomain}2).")

        m = TenantModel.objects.create(
            nombre=data['name'],
            subdominio=subdomain,
            ruc=data.get('ruc', ''),
            email_contacto=data.get('contact_email', ''),
            telefono_contacto=data.get('contact_phone', ''),
            fecha_inicio_contrato=_parse_date(data.get('contract_start_date')),
            fecha_vencimiento=_parse_date(data.get('expiration_date')),
            estado_suscripcion=data.get('subscription_status', 'active'),
            color_primario=data.get('primary_color', '#1976D2'),
            color_secundario=data.get('secondary_color', '#424242'),
            logo_url=data.get('logo_url', ''),
            activo=data.get('subscription_status', 'active') in ['active', 'demo'],
            max_devices=data.get('max_devices', 1),
        )
        for module in data.get('modules', []):
            TenantModuloModel.objects.create(tenant=m, modulo=module, activo=True)

        from modules.parametros.infrastructure.django_models import ParametroModel
        from modules.parametros.domain.entities import CATALOGO
        for mod, params in CATALOGO.items():
            for key, info in params.items():
                val_default = info.get('default', '')
                if mod == 'general':
                    if key == 'empresa_nombre': val_default = data.get('name', '')
                    elif key == 'empresa_rfc': val_default = data.get('ruc', '')
                    elif key == 'empresa_email': val_default = data.get('contact_email', '')
                    elif key == 'empresa_telefono': val_default = data.get('contact_phone', '')
                    elif key == 'empresa_representante': val_default = data.get('admin_name', '')
                ParametroModel.objects.get_or_create(
                    tenant_id=m.id, modulo=mod, clave=key,
                    defaults={'valor': val_default}
                )

        admin_email = data.get('admin_email', '').strip()
        admin_password = data.get('admin_password', '').strip()
        if admin_email and admin_password:
            admin_name = data.get('admin_name', 'Administrator').strip()
            username = f"{m.id}:{admin_email}"
            u, _ = UserModel.objects.get_or_create(
                username=username,
                defaults={
                    'email': admin_email,
                    'nombre': admin_name,
                    'rol': 'admin',
                    'tenant_id': m.id,
                    'activo': True,
                }
            )
            u.set_password(admin_password)
            u.save()

        return self._to_entity(m)

    def update_tenant(self, tenant_id: int, data: dict) -> TenantSummary:
        m = TenantModel.objects.get(id=tenant_id)
        field_mapping = {
            'name': 'nombre',
            'primary_color': 'color_primario',
            'secondary_color': 'color_secundario',
            'logo_url': 'logo_url',
            'ruc': 'ruc',
            'contact_email': 'email_contacto',
            'contact_phone': 'telefono_contacto',
            'contract_start_date': 'fecha_inicio_contrato',
            'expiration_date': 'fecha_vencimiento',
            'subscription_status': 'estado_suscripcion',
            'max_devices': 'max_devices'
        }
        for eng_key, es_field in field_mapping.items():
            if eng_key in data:
                val = data[eng_key]
                if eng_key in ['contract_start_date', 'expiration_date']:
                    val = _parse_date(val)
                setattr(m, es_field, val)
        if 'subscription_status' in data:
            m.activo = (data['subscription_status'] in ['active', 'demo'])
        m.save()

        from modules.auth.infrastructure.django_models import UserModel
        admin_u = None
        if data.get('admin_email'):
            admin_u = UserModel.objects.filter(tenant_id=m.id, email=data['admin_email'].strip()).first()
        if not admin_u:
            admin_u = UserModel.objects.filter(tenant_id=m.id).order_by('id').first()

        if admin_u:
            if data.get('admin_email') and data['admin_email'].strip():
                new_email = data['admin_email'].strip()
                admin_u.email = new_email
                admin_u.username = f"{m.id}:{new_email}"
            if data.get('admin_password') and data['admin_password'].strip():
                admin_u.set_password(data['admin_password'].strip())
            admin_u.save()

        return self._to_entity(m)

    def activate_tenant(self, tenant_id: int) -> TenantSummary:
        TenantModel.objects.filter(id=tenant_id).update(activo=True, estado_suscripcion='active')
        return self._to_entity(TenantModel.objects.get(id=tenant_id))

    def deactivate_tenant(self, tenant_id: int) -> TenantSummary:
        TenantModel.objects.filter(id=tenant_id).update(activo=False, estado_suscripcion='suspended')
        return self._to_entity(TenantModel.objects.get(id=tenant_id))

    def activate_module(self, tenant_id: int, module: str) -> TenantSummary:
        m = TenantModel.objects.get(id=tenant_id)
        TenantModuloModel.objects.update_or_create(
            tenant=m, module=module, defaults={'is_active': True}
        )
        return self._to_entity(m)

    def deactivate_module(self, tenant_id: int, module: str) -> TenantSummary:
        m = TenantModel.objects.get(id=tenant_id)
        TenantModuloModel.objects.filter(tenant=m, module=module).update(is_active=False)
        return self._to_entity(m)

    def get_statistics(self) -> GlobalStatistics:
        from django.db.models import Count
        from django.utils import timezone
        total = TenantModel.objects.count()
        activos = TenantModel.objects.filter(is_active=True).count()
        este_mes = TenantModel.objects.filter(
            created__month=timezone.now().month,
            created__year=timezone.now().year,
        ).count()
        modulo_top = (
            TenantModuloModel.objects
            .filter(is_active=True)
            .values('module')
            .annotate(total=Count('module'))
            .order_by('-total')
            .first()
        )
        return GlobalStatistics(
            total_tenants=total,
            active_tenants=activos,
            expired_tenants=0,
            monthly_revenue=Decimal('0'),
            most_used_module=modulo_top['module'] if modulo_top else 'none',
            new_this_month=este_mes,
        )
