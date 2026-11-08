from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction

from ..repository_impl import DjangoRestaurantRepository
from ..cross_module_adapters import DjangoRestaurantInventoryService
from ...application.restaurant_service import RestaurantService
from ..django_models import PlatoModel

def check_restaurant_permission(request, perm: str) -> bool:
    user = getattr(request, 'user', None)
    if not user:
        return True
    if getattr(user, 'role', '') in ('admin', 'superadmin'):
        return True
    if hasattr(user, 'has_permission'):
        return (
            user.has_permission(perm) or 
            user.has_permission('restaurante.*') or 
            user.has_permission('*')
        )
    return True

class BaseRestaurantView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._repo = DjangoRestaurantRepository()
        self._service = RestaurantService(self._repo, DjangoRestaurantInventoryService())

class ZonasView(BaseRestaurantView):
    def get(self, request):
        if not getattr(request, 'tenant', None) or not request.tenant.has_module('restaurantes'):
            return Response({'error': 'Module not active'}, status=status.HTTP_403_FORBIDDEN)
        if not check_restaurant_permission(request, 'restaurante.mesas'):
            return Response({'error': 'No tienes permisos para ver las mesas.'}, status=status.HTTP_403_FORBIDDEN)
            
        result = self._service.get_full_map(request.tenant.id)
        return Response(result)

    def post(self, request):
        if not getattr(request, 'tenant', None) or not request.tenant.has_module('restaurantes'):
            return Response({'error': 'Module not active'}, status=status.HTTP_403_FORBIDDEN)
        if not check_restaurant_permission(request, 'restaurante.config'):
            return Response({'error': 'No tienes permisos para configurar zonas.'}, status=status.HTTP_403_FORBIDDEN)
            
        result = self._service.create_zone(request.tenant.id, request.data.get('nombre'))
        return Response(result)

class MesasView(BaseRestaurantView):
    def post(self, request):
        if not getattr(request, 'tenant', None) or not request.tenant.has_module('restaurantes'):
            return Response({'error': 'Module not active'}, status=status.HTTP_403_FORBIDDEN)
        if not check_restaurant_permission(request, 'restaurante.config'):
            return Response({'error': 'No tienes permisos para configurar mesas.'}, status=status.HTTP_403_FORBIDDEN)
            
        result = self._service.create_table(
            request.tenant.id, 
            request.data.get('zona_id'), 
            request.data.get('nombre'), 
            request.data.get('asientos', 4)
        )
        return Response(result)

class PedidosView(BaseRestaurantView):
    def get(self, request):
        if not getattr(request, 'tenant', None) or not request.tenant.has_module('restaurantes'):
            return Response({'error': 'Module not active'}, status=status.HTTP_403_FORBIDDEN)
        if not check_restaurant_permission(request, 'restaurante.mesas'):
            return Response({'error': 'No tienes permisos para ver pedidos.'}, status=status.HTTP_403_FORBIDDEN)
            
        mesa_id = request.query_params.get('mesa_id')
        result = self._service.get_open_orders_by_table(request.tenant.id, table_id=mesa_id)
        return Response(result)

    @transaction.atomic
    def post(self, request):
        if not getattr(request, 'tenant', None) or not request.tenant.has_module('restaurantes'):
            return Response({'error': 'Module not active'}, status=status.HTTP_403_FORBIDDEN)
        if not check_restaurant_permission(request, 'restaurante.pedidos'):
            return Response({'error': 'No tienes permisos para registrar o actualizar pedidos.'}, status=status.HTTP_403_FORBIDDEN)
            
        mesa_id = request.data.get('mesa_id')
        lineas_data = request.data.get('lineas', [])
        
        result = self._service.open_or_update_order(request.tenant.id, mesa_id, lineas_data)
        return Response(result)

class PedidoCerrarView(BaseRestaurantView):
    @transaction.atomic
    def post(self, request, pedido_id):
        if not getattr(request, 'tenant', None) or not request.tenant.has_module('restaurantes'):
            return Response({'error': 'Module not active'}, status=status.HTTP_403_FORBIDDEN)
        if not check_restaurant_permission(request, 'restaurante.cobrar'):
            return Response({'error': 'No tienes permisos para cobrar pedidos o cerrar mesas.'}, status=status.HTTP_403_FORBIDDEN)
            
        mesa_id = request.data.get('mesa_id', 0)
        cliente_obj = request.data.get('cliente', {})
        billing_data = {
            'facturar': request.data.get('facturar', True),
            'factura_id': request.data.get('factura_id'),
            'factura_numero': request.data.get('factura_numero'),
            'clave_acceso': request.data.get('clave_acceso'),
            'cliente': cliente_obj,
            'cliente_nombre': request.data.get('cliente_nombre') or cliente_obj.get('nombre'),
            'cliente_identificacion': request.data.get('cliente_identificacion') or cliente_obj.get('identificacion'),
            'metodo_pago': request.data.get('metodo_pago', '01'),
            'emitir_sri': request.data.get('emitir_sri', False),
        }
        
        user_id = getattr(getattr(request, 'user', None), 'id', 0) or 0
        result = self._service.close_order(request.tenant.id, pedido_id, mesa_id, billing_data=billing_data, user_id=user_id)
        return Response(result)

class PantallaCocinaView(BaseRestaurantView):
    def get(self, request):
        if not getattr(request, 'tenant', None) or not request.tenant.has_module('restaurantes'):
            return Response({'error': 'Module not active'}, status=status.HTTP_403_FORBIDDEN)
        if not check_restaurant_permission(request, 'restaurante.cocina'):
            return Response({'error': 'No tienes permisos para ver la pantalla de cocina.'}, status=status.HTTP_403_FORBIDDEN)
            
        result = self._service.get_kitchen_dashboard(request.tenant.id)
        return Response(result)
        
    def post(self, request, linea_id):
        if not getattr(request, 'tenant', None) or not request.tenant.has_module('restaurantes'):
            return Response({'error': 'Module not active'}, status=status.HTTP_403_FORBIDDEN)
        if not check_restaurant_permission(request, 'restaurante.cocina'):
            return Response({'error': 'No tienes permisos para actualizar estados de cocina.'}, status=status.HTTP_403_FORBIDDEN)
            
        try:
            result = self._service.update_kitchen_line(request.tenant.id, linea_id, request.data.get('estado'))
            return Response(result)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class PlatosView(BaseRestaurantView):
    def get(self, request):
        if not getattr(request, 'tenant', None) or not request.tenant.has_module('restaurantes'):
            return Response({'error': 'Module not active'}, status=status.HTTP_403_FORBIDDEN)
        
        platos = PlatoModel.objects.filter(tenant_id=request.tenant.id, disponible=True).order_by('categoria', 'nombre')
        recipe_counts = self._service.get_recipe_counts(request.tenant.id)
        data = [{
            'id': str(p.id),
            'nombre': p.nombre,
            'categoria': p.categoria,
            'precio': float(p.precio),
            'disponible': p.disponible,
            'ingredients_count': recipe_counts.get(str(p.id), 0)
        } for p in platos]
        return Response(data)

    def post(self, request):
        if not getattr(request, 'tenant', None) or not request.tenant.has_module('restaurantes'):
            return Response({'error': 'Module not active'}, status=status.HTTP_403_FORBIDDEN)
        if not check_restaurant_permission(request, 'restaurante.config'):
            return Response({'error': 'No tienes permisos para crear platos.'}, status=status.HTTP_403_FORBIDDEN)
        
        nombre = request.data.get('nombre')
        categoria = request.data.get('categoria', 'General')
        precio = request.data.get('precio', 0.0)
        
        if not nombre:
            return Response({'error': 'Nombre es requerido'}, status=status.HTTP_400_BAD_REQUEST)
            
        plato = PlatoModel.objects.create(
            tenant_id=request.tenant.id,
            nombre=nombre,
            categoria=categoria,
            precio=precio
        )
        return Response({
            'id': str(plato.id),
            'nombre': plato.nombre,
            'categoria': plato.categoria,
            'precio': float(plato.precio),
            'disponible': plato.disponible
        }, status=status.HTTP_201_CREATED)

class PlatoDetailView(BaseRestaurantView):
    def delete(self, request, plato_id):
        if not getattr(request, 'tenant', None) or not request.tenant.has_module('restaurantes'):
            return Response({'error': 'Module not active'}, status=status.HTTP_403_FORBIDDEN)
        if not check_restaurant_permission(request, 'restaurante.config'):
            return Response({'error': 'No tienes permisos para eliminar platos.'}, status=status.HTTP_403_FORBIDDEN)
            
        self._service.delete_dish_recipe_holder(request.tenant.id, plato_id)
        PlatoModel.objects.filter(tenant_id=request.tenant.id, id=plato_id).delete()
        return Response({'success': True})

class PlatoRecipeView(BaseRestaurantView):
    """Recipe (escandallo) of a dish: inventory products consumed per unit sold."""

    def _guard(self, request):
        if not getattr(request, 'tenant', None) or not request.tenant.has_module('restaurantes'):
            return Response({'error': 'Module not active'}, status=status.HTTP_403_FORBIDDEN)
        if not check_restaurant_permission(request, 'restaurante.config'):
            return Response({'error': 'No tienes permisos para gestionar recetas.'}, status=status.HTTP_403_FORBIDDEN)
        return None

    def get(self, request, plato_id):
        if denied := self._guard(request): return denied
        try:
            return Response(self._service.get_dish_recipe(request.tenant.id, plato_id))
        except LookupError as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)

    @transaction.atomic
    def put(self, request, plato_id):
        if denied := self._guard(request): return denied
        try:
            result = self._service.set_dish_recipe(
                request.tenant.id, plato_id, request.data.get('ingredients', [])
            )
            return Response(result)
        except LookupError as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
