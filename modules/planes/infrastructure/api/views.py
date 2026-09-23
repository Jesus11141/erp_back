from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ...application.use_cases import ListPlans, AssignPlan
from modules.tenants.infrastructure.repository_impl import DjangoTenantRepository
from modules.tenants.application.use_cases import ActivateModule

class PlansView(APIView):
    def get(self, request):
        plans = ListPlans().execute()
        return Response([{
            'key': p.key, 'name': p.name, 'price': str(p.price),
            'modules': p.modules, 'max_users': p.max_users,
        } for p in plans])

class AssignPlanView(APIView):
    def post(self, request):
        if not request.tenant:
            return Response({'error': 'Company not found'}, status=status.HTTP_404_NOT_FOUND)
        try:
            plan_key = request.data.get('plan')
            if 'plan' not in request.data and 'plan_clave' in request.data:
                plan_key = request.data['plan_clave']
            months = int(request.data.get('months', request.data.get('meses', 1)))

            result = AssignPlan().execute(
                tenant_id=request.tenant.id,
                plan_key=plan_key,
                months=months,
            )
            activate_uc = ActivateModule(DjangoTenantRepository())
            for module in result['activated_modules']:
                activate_uc.execute(request.tenant.subdominio, module)
            return Response(result)
        except (ValueError, KeyError) as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
