from django.urls import path
from .views import (
    TenantsView, TenantDetailView, TenantToggleView, ModuleToggleView,
    StatisticsView, PlanView, PlanDetailView, SuperAdminTenantFeaturesView
)

urlpatterns = [
    path('tenants/', TenantsView.as_view(), name='sa-tenants'),
    path('tenants/<int:tenant_id>/', TenantDetailView.as_view(), name='sa-tenant-detail'),
    path('tenants/<int:tenant_id>/toggle/', TenantToggleView.as_view(), name='sa-tenant-toggle'),
    path('tenants/<int:tenant_id>/modules/<str:module>/', ModuleToggleView.as_view(), name='sa-module-toggle'),
    path('statistics/', StatisticsView.as_view(), name='sa-statistics'),
    path('plans/', PlanView.as_view(), name='sa-plans'),
    path('plans/<int:plan_id>/', PlanDetailView.as_view(), name='sa-plan-detail'),
    path('tenants/<int:tenant_id>/features/', SuperAdminTenantFeaturesView.as_view(), name='sa-tenant-features'),
]
