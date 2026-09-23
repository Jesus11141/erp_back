from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from modules.technical_service.application.use_cases import TechnicalServiceUseCases
from modules.technical_service.infrastructure.repository_impl import DjangoWorkOrderRepository
from modules.pos.infrastructure.repository_impl import DjangoCashRegisterRepository
from modules.parametros.infrastructure.repository_impl import DjangoParameterRepository
from modules.pos.infrastructure.cross_module_adapters import DjangoPOSInventoryService

# Initialize use cases
order_repo = DjangoWorkOrderRepository()
register_repo = DjangoCashRegisterRepository()
param_repo = DjangoParameterRepository()
inventory_service = DjangoPOSInventoryService()

use_cases = TechnicalServiceUseCases(
    order_repo=order_repo,
    register_repo=register_repo,
    param_repo=param_repo,
    inventory_service=inventory_service
)

class WorkOrderListView(APIView):
    def get(self, request):
        if not request.tenant:
            return Response({'error': 'Tenant not found'}, status=status.HTTP_404_NOT_FOUND)
        tenant_id = request.tenant.id
        orders = use_cases.list_work_orders.execute(tenant_id)
        
        data = []
        for o in orders:
            data.append({
                'id': o.id,
                'customer_id': o.customer_id,
                'customer_name': o.customer_name,
                'device_type': o.device_type,
                'device_model': o.device_model,
                'device_identifier': o.device_identifier,
                'physical_conditions': o.physical_conditions,
                'reported_fault': o.reported_fault,
                'advance_payment': float(o.advance_payment),
                'subtotal': float(o.subtotal),
                'vat_amount': float(o.vat_amount),
                'total': float(o.total),
                'balance_due': float(o.balance_due),
                'status': o.status,
                'created_at': o.created_at,
                'items': [{
                    'id': i.id,
                    'product_id': i.product_id,
                    'description': i.description,
                    'quantity': float(i.quantity),
                    'unit_price': float(i.unit_price),
                    'discount': float(i.discount),
                    'subtotal': float(i.subtotal)
                } for i in o.items]
            })
            
        return Response(data)

    def post(self, request):
        if not request.tenant:
            return Response({'error': 'Tenant not found'}, status=status.HTTP_404_NOT_FOUND)
        tenant_id = request.tenant.id
        user_id = request.user.id if hasattr(request, 'user') and request.user else None
        data = request.data
        
        try:
            order = use_cases.create_work_order.execute(tenant_id, user_id, data)
            return Response({'id': order.id, 'status': order.status}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class WorkOrderStatusView(APIView):
    def patch(self, request, pk):
        if not request.tenant:
            return Response({'error': 'Tenant not found'}, status=status.HTTP_404_NOT_FOUND)
        tenant_id = request.tenant.id
        new_status = request.data.get('status')
        
        if not new_status:
            return Response({'error': 'status is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            order = use_cases.update_status.execute(tenant_id, pk, new_status)
            if not order:
                return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
            return Response({'id': order.id, 'status': order.status})
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class WorkOrderPayView(APIView):
    def post(self, request, pk):
        if not request.tenant:
            return Response({'error': 'Tenant not found'}, status=status.HTTP_404_NOT_FOUND)
        tenant_id = request.tenant.id
        user_id = request.user.id if hasattr(request, 'user') and request.user else None
        
        from decimal import Decimal
        try:
            amount = Decimal(str(request.data.get('amount', 0)))
            result = use_cases.pay_work_order.execute(tenant_id, user_id, pk, amount)
            return Response(result, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
