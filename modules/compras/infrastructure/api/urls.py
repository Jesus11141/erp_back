from django.urls import path
from .views import (
    SuppliersView, SupplierDetailView,
    PurchaseOrdersView, PurchaseOrderDetailView, PurchaseOrderStatusView,
    PurchaseInvoicesView, PurchaseInvoiceDetailView, PurchaseInvoiceReceiveStockView,
    AccountsPayableView, AccountPayablePaymentView
)

urlpatterns = [
    # Proveedores
    path('proveedores/', SuppliersView.as_view()),
    path('proveedores/<int:supplier_id>/', SupplierDetailView.as_view()),

    # Órdenes de Compra
    path('ordenes/', PurchaseOrdersView.as_view()),
    path('ordenes/<int:order_id>/', PurchaseOrderDetailView.as_view()),
    path('ordenes/<int:order_id>/estado/', PurchaseOrderStatusView.as_view()),

    # Facturas de Compra
    path('facturas/', PurchaseInvoicesView.as_view()),
    path('facturas/<int:invoice_id>/', PurchaseInvoiceDetailView.as_view()),
    path('facturas/<int:invoice_id>/recepcionar/', PurchaseInvoiceReceiveStockView.as_view()),

    # Cuentas por Pagar (CXP)
    path('cuentas-pagar/', AccountsPayableView.as_view()),
    path('cuentas-pagar/<int:account_payable_id>/abonos/', AccountPayablePaymentView.as_view()),
]
