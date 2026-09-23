from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction

from ..repository_impl import DjangoRestaurantRepository
from ...application.restaurant_service import RestaurantService

class BaseRestaurantView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._repo = DjangoRestaurantRepository()
        self._service = RestaurantService(self._repo)

class ZonasView(BaseRestaurantView):
    def get(self, request):
        if not hasattr(request, 'tenant') or not request.tenant:
            return Response({'error': 'Company not found'}, status=status.HTTP_404_NOT_FOUND)
            
        result = self._service.get_full_map(request.tenant.id)
        return Response(result)

    def post(self, request):
        if not hasattr(request, 'tenant') or not request.tenant:
            return Response({'error': 'Company not found'}, status=status.HTTP_404_NOT_FOUND)
            
        result = self._service.create_zone(request.tenant.id, request.data.get('nombre'))
        return Response(result)

class MesasView(BaseRestaurantView):
    def post(self, request):
        if not hasattr(request, 'tenant') or not request.tenant:
            return Response({'error': 'Company not found'}, status=status.HTTP_404_NOT_FOUND)
            
        result = self._service.create_table(
            request.tenant.id, 
            request.data.get('zona_id'), 
            request.data.get('nombre'), 
            request.data.get('asientos', 4)
        )
        return Response(result)

class PedidosView(BaseRestaurantView):
    def get(self, request):
        if not hasattr(request, 'tenant') or not request.tenant:
            return Response({'error': 'Company not found'}, status=status.HTTP_404_NOT_FOUND)
            
        mesa_id = request.query_params.get('mesa_id')
        result = self._service.get_open_orders_by_table(request.tenant.id, table_id=mesa_id)
        return Response(result)

    @transaction.atomic
    def post(self, request):
        if not hasattr(request, 'tenant') or not request.tenant:
            return Response({'error': 'Company not found'}, status=status.HTTP_404_NOT_FOUND)
            
        mesa_id = request.data.get('mesa_id')
        lineas_data = request.data.get('lineas', [])
        
        result = self._service.open_or_update_order(request.tenant.id, mesa_id, lineas_data)
        return Response(result)

class PedidoCerrarView(BaseRestaurantView):
    @transaction.atomic
    def post(self, request, pedido_id):
        if not hasattr(request, 'tenant') or not request.tenant:
            return Response({'error': 'Company not found'}, status=status.HTTP_404_NOT_FOUND)
            
        # In a real scenario, we might need mesa_id to release it
        # For MVP, we fetch the mesa_id from the repo inside service, but we don't have get_order_by_id yet.
        # Let's pass 0 for mesa_id and handle it in the service gracefully if possible, or add it to repo.
        # As a quick fix, let's assume we can get mesa_id from request.data or service refactor.
        mesa_id = request.data.get('mesa_id', 0)
        
        result = self._service.close_order(request.tenant.id, pedido_id, mesa_id)
        return Response(result)

class PantallaCocinaView(BaseRestaurantView):
    def get(self, request):
        if not hasattr(request, 'tenant') or not request.tenant:
            return Response({'error': 'Company not found'}, status=status.HTTP_404_NOT_FOUND)
            
        result = self._service.get_kitchen_dashboard(request.tenant.id)
        return Response(result)
        
    def post(self, request, linea_id):
        if not hasattr(request, 'tenant') or not request.tenant:
            return Response({'error': 'Company not found'}, status=status.HTTP_404_NOT_FOUND)
            
        try:
            result = self._service.update_kitchen_line(request.tenant.id, linea_id, request.data.get('estado'))
            return Response(result)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
