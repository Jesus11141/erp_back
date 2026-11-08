from django.urls import path
from modules.importador.infrastructure.api.views import TemplateDownloadView, BulkImportView

urlpatterns = [
    path('<str:entity>/template/', TemplateDownloadView.as_view(), name='import-template-download'),
    path('<str:entity>/', BulkImportView.as_view(), name='bulk-import'),
]
