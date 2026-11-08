from django.urls import path
from .views import (
    InvoicesView, InvoiceActionsView, InvoiceXMLView, CertificadoView,
    CreditNotesView, CreditNoteActionsView, SRIWebhookView,
    WithholdingsView, WithholdingActionsView, WithholdingXMLView,
    DispatchGuidesView, DispatchGuideActionsView, DispatchGuideXMLView,
    PurchaseSettlementsView, PurchaseSettlementActionsView, PurchaseSettlementXMLView,
    TestSMTPView
)

urlpatterns = [
    path('', InvoicesView.as_view()),
    path('certificado/', CertificadoView.as_view()),
    path('test-smtp/', TestSMTPView.as_view()),
    path('<int:invoice_id>/xml/', InvoiceXMLView.as_view()),
    path('<int:invoice_id>/<str:accion>/', InvoiceActionsView.as_view()),
    path('webhook/sri/', SRIWebhookView.as_view()),
    path('notas-credito/', CreditNotesView.as_view()),
    path('notas-credito/<int:nc_id>/<str:accion>/', CreditNoteActionsView.as_view()),
    path('retenciones/', WithholdingsView.as_view()),
    path('retenciones/<int:ret_id>/xml/', WithholdingXMLView.as_view()),
    path('retenciones/<int:ret_id>/<str:accion>/', WithholdingActionsView.as_view()),
    path('guias-remision/', DispatchGuidesView.as_view()),
    path('guias-remision/<int:guide_id>/xml/', DispatchGuideXMLView.as_view()),
    path('guias-remision/<int:guide_id>/<str:accion>/', DispatchGuideActionsView.as_view()),
    path('liquidaciones-compra/', PurchaseSettlementsView.as_view()),
    path('liquidaciones-compra/<int:settlement_id>/xml/', PurchaseSettlementXMLView.as_view()),
    path('liquidaciones-compra/<int:settlement_id>/<str:accion>/', PurchaseSettlementActionsView.as_view()),
]
