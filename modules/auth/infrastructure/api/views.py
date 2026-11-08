from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from ...infrastructure.repository_impl import DjangoUserRepository
from ...application.use_cases import LoginUser, CreateUser, ListUsers
from ..permissions import RequiresPermission

def _token_response(user):
    from modules.auth.infrastructure.django_models import UserModel
    django_user = UserModel.objects.get(id=user.id)
    refresh = RefreshToken.for_user(django_user)
    refresh['tenant_id'] = user.tenant_id
    refresh['role'] = user.role
    refresh['name'] = user.name
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'role': user.role,
            'permissions': user.custom_permissions,
        }
    }

class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        from datetime import date
        email = request.data.get('email', '').strip()
        password = request.data.get('password', '').strip()

        if not email or not password:
            return Response({'error': 'Email and password required'}, status=status.HTTP_400_BAD_REQUEST)

        from modules.auth.infrastructure.django_models import UserModel
        from modules.tenants.infrastructure.django_models import TenantModel

        target_tenant = getattr(request, 'tenant', None)
        subdomain_req = request.data.get('subdominio') or request.data.get('tenant')

        if subdomain_req:
            t = TenantModel.objects.filter(subdomain=subdomain_req).first()
            if t:
                target_tenant = t

        # En acceso por IP, localhost o si el correo pertenece a otra empresa, ubicar el tenant por el email del usuario
        current_sub = getattr(target_tenant, 'subdomain', '')
        is_ip = current_sub.replace('.', '').isdigit()
        is_local_or_ip = not target_tenant or current_sub in ['localhost', '127', '127.0.0.1'] or is_ip
        
        user_in_current_tenant = target_tenant and UserModel.objects.filter(email=email, tenant_id=target_tenant.id).exists()
        
        if is_local_or_ip or not user_in_current_tenant:
            candidate = UserModel.objects.filter(email=email).order_by('-id').first()
            if candidate:
                t = TenantModel.objects.filter(id=candidate.tenant_id).first()
                if t:
                    target_tenant = t

        if not target_tenant:
            return Response({'error': 'Company not found for user'}, status=status.HTTP_404_NOT_FOUND)

        # Resolver target_tenant a TenantModel si venía como entidad del dominio
        if not isinstance(target_tenant, TenantModel):
            target_tenant = TenantModel.objects.filter(id=target_tenant.id).first()

        if not target_tenant:
            return Response({'error': 'Company not found for user'}, status=status.HTTP_404_NOT_FOUND)

        # Verificar suspensión o vencimiento de la empresa cliente
        if target_tenant.expiration_date and target_tenant.expiration_date < date.today():
            return Response({'error': f'The subscription for {target_tenant.name} expired on {target_tenant.expiration_date}. Contact support.'}, status=status.HTTP_403_FORBIDDEN)
        if target_tenant.subscription_state in ['suspendida', 'vencida'] or not target_tenant.is_active:
            return Response({'error': f'The subscription for {target_tenant.name} is suspended.'}, status=status.HTTP_403_FORBIDDEN)

        repo = DjangoUserRepository()
        try:
            user = LoginUser(repo).execute(
                email=email,
                password=password,
                tenant_id=target_tenant.id,
            )
        except (PermissionError, KeyError) as e:
            return Response({'error': 'Incorrect email or password'}, status=status.HTTP_401_UNAUTHORIZED)

        # Device limit verification (PER USER)
        device_id = request.data.get('device_id')
        if not device_id:
            return Response({'error': 'Device ID is required. Please refresh the page or update your app.'}, status=status.HTTP_400_BAD_REQUEST)
            
        from modules.tenants.infrastructure.django_models import DeviceRegistrationModel
        from django.utils import timezone
        
        device_record = DeviceRegistrationModel.objects.filter(user_id=user.id, device_uuid=device_id).first()
        if not device_record:
            # Contar los dispositivos activos de TODA la empresa (tenant)
            current_devices_count = DeviceRegistrationModel.objects.filter(user__tenant_id=target_tenant.id).count()
            
            # Validar contra el límite del Tenant (ej. 20) en lugar del límite de 1 por usuario
            if current_devices_count >= target_tenant.max_devices:
                # Estilo Netflix: Si se superó el límite, eliminamos la sesión más antigua para dejar entrar la nueva
                oldest_device = DeviceRegistrationModel.objects.filter(user__tenant_id=target_tenant.id).order_by('last_login').first()
                if oldest_device:
                    oldest_device.delete()
            
            device_name = request.data.get('device_name', 'Unknown Device')
            device_record = DeviceRegistrationModel.objects.create(
                user_id=user.id,
                device_uuid=device_id,
                device_name=device_name
            )
        else:
            device_record.last_login = timezone.now()
            device_record.save()

        return Response(_token_response(user))

class UsersView(APIView):
    def get_permissions(self):
        return [RequiresPermission('admin.*')]

    def get(self, request):
        repo = DjangoUserRepository()
        users = ListUsers(repo).execute(request.tenant.id)
        from modules.auth.infrastructure.django_models import UserModel
        db_users = UserModel.objects.filter(tenant_id=request.tenant.id)
        role_map = {u.id: {'custom_role_id': u.custom_role_id, 'permissions': u.permissions} for u in db_users}
        return Response([{'id': u.id, 'name': u.name, 'email': u.email, 'role': u.role, 'is_active': u.is_active, 'custom_role_id': role_map.get(u.id, {}).get('custom_role_id'), 'permissions': role_map.get(u.id, {}).get('permissions', [])} for u in users])

    def post(self, request):
        repo = DjangoUserRepository()
        try:
            # Enforce max_users limit
            from modules.tenants.infrastructure.django_models import TenantModel
            from modules.auth.infrastructure.django_models import UserModel
            tenant = TenantModel.objects.get(id=request.tenant.id)
            current_users = UserModel.objects.filter(tenant_id=request.tenant.id).count()
            limit = getattr(tenant, 'max_users', 999)
            if current_users >= limit:
                return Response({'error': f'Límite de usuarios ({limit}) alcanzado para este plan.'}, status=status.HTTP_403_FORBIDDEN)

            user = CreateUser(repo).execute(
                tenant_id=request.tenant.id,
                name=request.data['name'],
                email=request.data['email'],
                password=request.data['password'],
                role=request.data['role'],
            )
            custom_role_id = request.data.get('custom_role_id')
            permissions = request.data.get('permissions', [])
            
            update_kwargs = {}
            if custom_role_id:
                update_kwargs['custom_role_id'] = custom_role_id
            if permissions is not None:
                update_kwargs['permissions'] = permissions
                
            if update_kwargs:
                UserModel.objects.filter(id=user.id).update(**update_kwargs)
                
            return Response({'id': user.id, 'name': user.name, 'is_active': user.is_active, 'custom_role_id': custom_role_id, 'permissions': permissions}, status=status.HTTP_201_CREATED)
        except (ValueError, KeyError) as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class UserDetailView(APIView):
    def get_permissions(self):
        return [RequiresPermission('admin.*')]

    def put(self, request, user_id):
        repo = DjangoUserRepository()
        user = repo.find_by_id(user_id)
        if not user or user.tenant_id != request.tenant.id:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
        name = request.data.get('name')
        email = request.data.get('email')
        role = request.data.get('role')
        is_active = request.data.get('is_active')
        password = request.data.get('password')
        custom_role_id = request.data.get('custom_role_id')
        permissions = request.data.get('permissions')

        if name:
            user.name = name
        if email:
            email = email.strip().lower()
            if email != user.email:
                existing = repo.find_by_email(email, request.tenant.id)
                if existing:
                    return Response({'error': 'Another user with this email already exists'}, status=status.HTTP_400_BAD_REQUEST)
                user.email = email
        if role:
            user.role = role
        if is_active is not None:
            user.is_active = bool(is_active)
        
        repo.save(user, password)
        
        custom_role_id = request.data.get('custom_role_id')
        from modules.auth.infrastructure.django_models import UserModel
        db_user = UserModel.objects.get(id=user.id)
        update_fields = []
        if custom_role_id is not None:
            db_user.custom_role_id = custom_role_id
            update_fields.append('custom_role_id')
        if permissions is not None:
            db_user.permissions = permissions
            update_fields.append('permissions')
            
        if update_fields:
            db_user.save(update_fields=update_fields)
            
        return Response({'id': user.id, 'name': user.name, 'email': user.email, 'role': user.role, 'is_active': user.is_active, 'custom_role_id': db_user.custom_role_id, 'permissions': db_user.permissions})

    def delete(self, request, user_id):
        repo = DjangoUserRepository()
        user = repo.find_by_id(user_id)
        if not user or user.tenant_id != request.tenant.id:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
        user.is_active = False
        repo.save(user)
        return Response({'success': True})

class MeView(APIView):
    def get(self, request):
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        u = request.user
        from modules.auth.infrastructure.django_models import UserModel
        db_u = UserModel.objects.filter(id=u.id).first()
        if not db_u:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
        permissions = list(db_u.permissions) if db_u.permissions else []
        if db_u.custom_role and db_u.custom_role.permissions:
            permissions.extend(db_u.custom_role.permissions)
            permissions = list(set(permissions))
            
        return Response({
            'id': u.id, 
            'name': u.name, 
            'email': u.email, 
            'role': u.role, 
            'permissions': permissions,
            'is_admin': u.role in ('admin', 'superadmin') or '*' in permissions or 'admin.*' in permissions
        })
