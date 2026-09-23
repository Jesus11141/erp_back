from django.urls import path
from .views import CustomersView, QuotationsView, QuotationDetailView, QuotationActionView, OrdersView, PaymentMethodsView, PaymentMethodDetailView, AccountReceivablesView, ReceivablePaymentView, QuotationPdfView, QuotationConfigView

urlpatterns = [
    path('customers/', CustomersView.as_view()),
    path('quotations/', QuotationsView.as_view()),
    path('quotations/<int:quotation_id>/', QuotationDetailView.as_view()),
    path('quotations/<int:quotation_id>/config/', QuotationConfigView.as_view()),
    path('quotations/<int:quotation_id>/pdf/', QuotationPdfView.as_view()),
    path('quotations/<int:quotation_id>/<str:action>/', QuotationActionView.as_view()),
    path('orders/', OrdersView.as_view(), name='orders-list'),
    path('payment-methods/', PaymentMethodsView.as_view(), name='payment-methods-list'),
    path('payment-methods/<int:pk>/', PaymentMethodDetailView.as_view(), name='payment-method-detail'),
    path('receivables/', AccountReceivablesView.as_view()),
    path('receivables/<int:account_id>/pay/', ReceivablePaymentView.as_view()),
]
