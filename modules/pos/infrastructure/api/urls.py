from django.urls import path
from .views import (
    CashRegisterView, CashRegisterActionView, POSSaleView, CashRegisterClosureView,
    PhysicalCashRegisterView, PhysicalCashRegisterDetailView, CashRegisterMovementView,
    PendingOrdersView, POSQuotationsView, VerifyPinView
)

urlpatterns = [
    path('verify-pin/', VerifyPinView.as_view()),
    path('pending-orders/', PendingOrdersView.as_view()),
    path('pos-quotations/', POSQuotationsView.as_view()),
    path('cash-registers/', CashRegisterView.as_view()),
    path('physical-cash-registers/', PhysicalCashRegisterView.as_view()),
    path('physical-cash-registers/<int:physical_reg_id>/', PhysicalCashRegisterDetailView.as_view()),
    path('cash-registers/<int:register_id>/sales/', POSSaleView.as_view()),
    path('cash-registers/<int:register_id>/movements/', CashRegisterMovementView.as_view()),
    path('cash-registers/<int:register_id>/<str:action>/', CashRegisterActionView.as_view()),
    path('closures/', CashRegisterClosureView.as_view()),
]
