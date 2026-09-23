from django.urls import path
from .views import WorkOrderListView, WorkOrderStatusView, WorkOrderPayView

urlpatterns = [
    path('orders/', WorkOrderListView.as_view(), name='work-orders-list'),
    path('orders/<int:pk>/status/', WorkOrderStatusView.as_view(), name='work-orders-status'),
    path('orders/<int:pk>/pay/', WorkOrderPayView.as_view(), name='work-orders-pay'),
]
