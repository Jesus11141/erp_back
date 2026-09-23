from django.urls import path
from .views import (
    ProductView, StockView, StockMovementView, KardexView,
    ProductDiscountTierView, DiscountTierDetailView, QuotationView,
    BranchView, BranchDetailView, StockTransferView, BranchStockView
)

urlpatterns = [
    path('products/', ProductView.as_view()),
    path('products/<int:producto_id>/stock/', StockView.as_view()),
    path('products/<int:producto_id>/movements/', StockMovementView.as_view()),
    path('products/<int:producto_id>/kardex/', KardexView.as_view()),
    path('products/<int:producto_id>/discount-tiers/', ProductDiscountTierView.as_view()),
    path('discount-tiers/<int:escala_id>/', DiscountTierDetailView.as_view()),
    path('quotation/', QuotationView.as_view()),
    path('branches/', BranchView.as_view()),
    path('branches/<int:sucursal_id>/', BranchDetailView.as_view()),
    path('transfers/', StockTransferView.as_view()),
    path('branches/<int:sucursal_id>/stock/', BranchStockView.as_view()),
]
