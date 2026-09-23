import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from modules.tenants.infrastructure.django_models import TenantModel
from modules.auth.infrastructure.django_models import UserModel, RoleModel

def run():
    print("Creating initial tenant and super admin...")
    # 1. Create a default tenant
    tenant, created = TenantModel.objects.get_or_create(
        name="Mi Empresa Principal",
        defaults={
            'subdomain': 'localhost',
            'is_active': True,
            'max_devices': 100,
        }
    )
    print(f"Tenant created/found: {tenant.name} (ID: {tenant.id})")


    # 2. Create the Administrador role
    admin_role, r_created = RoleModel.objects.get_or_create(
        tenant_id=tenant.id,
        name="Administrador",
        defaults={
            'permissions': ['*']
        }
    )
    print(f"Role created/found: {admin_role.name}")

    # 3. Create the superadmin user
    email = "hidalgo11141@gmail.com"
    username = f"{tenant.id}:{email}"
    
    user_qs = UserModel.objects.filter(email=email, tenant_id=tenant.id)
    if not user_qs.exists():
        user = UserModel.objects.create_user(
            username=username,
            email=email,
            tenant_id=tenant.id,
            name="Raul Hidalgo",
            role="superadmin"
        )
        user.set_password("123456")
        user.custom_role = admin_role
        user.save()
        print(f"Superadmin user created: {email} con clave 123456")
    else:
        user = user_qs.first()
        user.set_password("123456")
        user.role = "superadmin"
        user.custom_role = admin_role
        user.save()
        print(f"Superadmin user updated: {email} con clave 123456")

if __name__ == "__main__":
    run()
