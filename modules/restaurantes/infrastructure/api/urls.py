from django.urls import path
from .views import ZonasView, MesasView, PedidosView, PedidoCerrarView, PantallaCocinaView, PlatosView, PlatoDetailView, PlatoRecipeView

urlpatterns = [
    path('zonas/', ZonasView.as_view(), name='restaurantes-zonas'),
    path('mesas/', MesasView.as_view(), name='restaurantes-mesas'),
    path('pedidos/', PedidosView.as_view(), name='restaurantes-pedidos'),
    path('pedidos/<str:pedido_id>/cerrar/', PedidoCerrarView.as_view(), name='restaurantes-pedidos-cerrar'),
    path('cocina/', PantallaCocinaView.as_view(), name='restaurantes-cocina'),
    path('cocina/<str:linea_id>/', PantallaCocinaView.as_view(), name='restaurantes-cocina-update'),
    path('platos/', PlatosView.as_view(), name='restaurantes-platos'),
    path('platos/<str:plato_id>/', PlatoDetailView.as_view(), name='restaurantes-plato-detail'),
    path('platos/<str:plato_id>/recipe/', PlatoRecipeView.as_view(), name='restaurantes-plato-recipe'),
]
