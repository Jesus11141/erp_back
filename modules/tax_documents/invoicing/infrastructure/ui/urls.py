from django.urls import path
from .views import InvoicesView, InvoiceActionsView, InvoiceXMLView, CertificadoView, CreditNotesView, CreditNoteActionsView, SRIWebhookView

urlpatterns = [
    path('', InvoicesView.as_view()),
    path('certificado/', CertificadoView.as_view()),
    path('<int:invoice_id>/xml/', InvoiceXMLView.as_view()),
    path('<int:invoice_id>/<str:accion>/', InvoiceActionsView.as_view()),
    path('webhook/sri/', SRIWebhookView.as_view()),
    path('notas-credito/', CreditNotesView.as_view()),
    path('notas-credito/<int:nc_id>/<str:accion>/', CreditNoteActionsView.as_view()),
]
