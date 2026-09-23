from django.urls import path
from .api.views import AuditLogView

urlpatterns = [
    path('logs/', AuditLogView.as_view(), name='audit_logs'),
]
