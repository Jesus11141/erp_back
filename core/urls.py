"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/tenant/', include('modules.tenants.infrastructure.api.urls')),
    path('api/auth/', include('modules.auth.infrastructure.api.urls')),
    path('api/facturacion/', include('modules.tax_documents.invoicing.infrastructure.ui.urls')),
    path('api/ventas/', include('modules.ventas.infrastructure.api.urls')),
    path('api/inventario/', include('modules.inventario.infrastructure.api.urls')),
    path('api/inventory/', include('modules.inventario.infrastructure.api.urls')), # Alias for english frontend
    path('api/rrhh/', include('modules.rrhh.infrastructure.api.urls')),
    path('api/reportes/', include('modules.reportes.infrastructure.api.urls')),
    path('api/planes/', include('modules.planes.infrastructure.api.urls')),
    path('api/pos/', include('modules.pos.infrastructure.api.urls')),
    path('api/parametros/', include('modules.parametros.infrastructure.api.urls')),
    path('api/superadmin/', include('modules.superadmin.infrastructure.api.urls')),
    path('api/clinica/', include('modules.clinica.infrastructure.api.urls')),
    path('api/contabilidad/', include('modules.contabilidad.infrastructure.api.urls')),
    path('api/restaurantes/', include('modules.restaurantes.infrastructure.api.urls')),
    path('api/technical-service/', include('modules.technical_service.infrastructure.api.urls')),
    path('api/ai/', include('modules.ai_assistant.infrastructure.api.urls')),
    path('api/auditoria/', include('modules.auditoria.infrastructure.urls')),
    path('api/accounting/', include('modules.accounting.infrastructure.api.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
