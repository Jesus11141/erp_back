from django.urls import path
from .views import TenantConfigView, TenantLogoView, ModuleView, TenantFeaturesView

urlpatterns = [
    path('config/', TenantConfigView.as_view()),
    path('logo/', TenantLogoView.as_view()),
    path('modules/<str:module>/', ModuleView.as_view()),
    path('features/', TenantFeaturesView.as_view()),
]
