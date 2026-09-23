from django.urls import path
from .views import setup_sri_credentials, run_sri_emitted_extraction, get_outbox_documents, run_sri_extraction, get_inbox_documents, get_sri_status, run_sri_invoice_extraction, clear_sri_inbox, process_sri_invoice

urlpatterns = [
    path('sri-credentials/', setup_sri_credentials, name='setup_sri_credentials'),
    path('sri-extract/', run_sri_extraction, name='run_sri_extraction'),
    path('sri-extract-invoices/', run_sri_invoice_extraction, name='run_sri_invoice_extraction'),
    path('sri-inbox/', get_inbox_documents, name='get_inbox_documents'),
    path('sri-inbox/clear/', clear_sri_inbox, name='clear_sri_inbox'),
    path('sri-inbox/<int:inbox_id>/process/', process_sri_invoice, name='process_sri_invoice'),
    path('sri-status/', get_sri_status, name='get_sri_status'),
    path('sri-extract-emitted/', run_sri_emitted_extraction, name='run_sri_emitted_extraction'),
    path('sri-outbox/', get_outbox_documents, name='get_outbox_documents'),
]
