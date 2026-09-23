from ..domain.repositories import SuperAdminRepository
from ..domain.entities import TenantSummary, AVAILABLE_MODULES, AVAILABLE_PLANS
from modules.planes.domain.entities import PLANS


class CreateTenant:
    def __init__(self, repo: SuperAdminRepository):
        self.repo = repo

    def execute(self, data: dict) -> TenantSummary:
        if not data.get('name'):
            raise ValueError("Name is required")
        if not data.get('subdomain'):
            raise ValueError("Subdomain is required")
        subdomain = data['subdomain'].lower().replace(' ', '-')
        data['subdomain'] = subdomain
        # Añadir max_devices a los datos si viene del request
        if 'max_devices' in data:
            data['max_devices'] = int(data['max_devices'])

        # Si se envían módulos explícitamente desde la interfaz, los usamos.
        if 'modules' in data and isinstance(data['modules'], list) and len(data['modules']) > 0:
            pass # Mantenemos data['modules']
        else:
            plan_key = data.get('plan', 'basic')
            from modules.tenants.infrastructure.django_models import PlanModel
            try:
                plan_db = PlanModel.objects.get(key=plan_key)
                data['modules'] = plan_db.modules
                if 'max_devices' not in data:
                    data['max_devices'] = plan_db.max_devices
            except PlanModel.DoesNotExist:
                # Fallback to empty if plan does not exist
                data['modules'] = []
            
        tenant_summary = self.repo.create_tenant(data)
        
        # Sincronización automática con el Facturador en Go
        try:
            import requests
            import os
            
            ruc = data.get('ruc', '9999999999999')
            if len(ruc) < 13:
                ruc = ruc.ljust(13, '0')
                
            payload = {
                "company_name": data.get('name', 'Empresa Desconocida'),
                "address": "Dirección no especificada",
                "gov_id_number": ruc,
                "company_email": data.get('contact_email', 'admin@example.com'),
                "currency": "USD",
                "obligado_contabilidad": False,
                "type_taxpayer": {
                    "name": "REGIMEN GENERAL",
                    "code": "01",
                    "additional_info": ""
                },
                "branch_offices": []
            }
            
            facturador_url = os.environ.get('FACTURADOR_API_URL', 'http://127.0.0.1:8080')
            response = requests.post(f"{facturador_url}/api/companies/sync", json=payload, timeout=5)
            if not response.ok:
                print(f"Warning: Sincronización con Facturador falló ({response.status_code}): {response.text}")
        except Exception as e:
            print(f"Warning: Error de red al sincronizar con Go Facturador: {e}")

        return tenant_summary
