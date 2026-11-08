from django.urls import path
from modules.reportes.application.use_cases import GetDashboard
from modules.reportes.infrastructure.api.views import (
    InvoicePDFView, QuotePDFView,
    CreditNotePDFView, WithholdingPDFView,
    DispatchGuidePDFView, PurchaseSettlementPDFView,
    SalesExcelView, InventoryExcelView,
    ClientsExcelView, PayrollExcelView,
    ProfitMarginExcelView, ProfitMarginPDFView,
    TopProductsExcelView, TopProductsPDFView,
    CashClosureExcelView, CashClosurePDFView,
    CashClosureSummaryExcelView, CashClosureSummaryPDFView,
)
from rest_framework.views import APIView
from rest_framework.response import Response
from modules.parametros.infrastructure.repository_impl import DjangoParameterRepository
from modules.parametros.application.use_cases import GetAllParameters
from modules.reportes.infrastructure.repository_impl import DjangoReportRepository

class DashboardView(APIView):
    def get(self, request):
        if not request.tenant:
            return Response({'error': 'Company not found'}, status=404)
        repo = DjangoReportRepository()
        dashboard = GetDashboard(repo).execute(
            tenant_id=request.tenant.id,
            tenant_name=request.tenant.name,
            active_modules=request.tenant.modules,
        )
        return Response({
            'tenant': dashboard.tenant_name,
            'sales': {
                'total_sales': str(dashboard.sales.total_sales) if dashboard.sales else '0',
                'total_quotes': dashboard.sales.total_quotes if dashboard.sales else 0,
                'total_orders': dashboard.sales.total_orders if dashboard.sales else 0,
                'pending_orders': dashboard.sales.pending_orders if dashboard.sales else 0,
            },
            'inventory': {
                'total_products': dashboard.inventory.total_products if dashboard.inventory else 0,
                'low_stock_products': dashboard.inventory.low_stock_products if dashboard.inventory else 0,
                'inventory_value': str(dashboard.inventory.inventory_value) if dashboard.inventory else '0',
            },
            'hr': {
                'total_employees': dashboard.hr.total_employees if dashboard.hr else 0,
                'monthly_payroll': str(dashboard.hr.monthly_payroll) if dashboard.hr else '0',
                'attendances_today': dashboard.hr.attendances_today if dashboard.hr else 0,
            },
        })

class BIDashboardView(APIView):
    def get(self, request):
        if not request.tenant:
            return Response({'error': 'Company not found'}, status=404)
        repo = DjangoReportRepository()
        metrics = repo.get_bi_metrics(request.tenant.id)
        return Response(metrics)

urlpatterns = [
    path('dashboard/',                          DashboardView.as_view()),
    path('bi-dashboard/',                       BIDashboardView.as_view()),
    path('pdf/invoice/<int:invoice_id>/',        InvoicePDFView.as_view()),
    path('pdf/quotation/<int:quote_id>/',  QuotePDFView.as_view()),
    path('pdf/credit-note/<int:nc_id>/',         CreditNotePDFView.as_view()),
    path('pdf/withholding/<int:ret_id>/',        WithholdingPDFView.as_view()),
    path('pdf/dispatch-guide/<int:guide_id>/',   DispatchGuidePDFView.as_view()),
    path('pdf/purchase-settlement/<int:settlement_id>/', PurchaseSettlementPDFView.as_view()),
    path('excel/sales/',                        SalesExcelView.as_view()),
    path('excel/inventory/',                    InventoryExcelView.as_view()),
    path('excel/customers/',                      ClientsExcelView.as_view()),
    path('excel/nomina/',                        PayrollExcelView.as_view()),
    
    # Nuevos reportes POS
    path('excel/profit/',                        ProfitMarginExcelView.as_view()),
    path('pdf/profit/',                          ProfitMarginPDFView.as_view()),
    path('excel/top-products/',                  TopProductsExcelView.as_view()),
    path('pdf/top-products/',                    TopProductsPDFView.as_view()),
    
    # Reportes de Cierre de CashRegister
    path('excel/register-closing/<int:closure_id>/',  CashClosureExcelView.as_view()),
    path('pdf/register-closing/<int:closure_id>/',    CashClosurePDFView.as_view()),
    path('excel/register-closing-resumen/',           CashClosureSummaryExcelView.as_view()),
    path('pdf/register-closing-resumen/',             CashClosureSummaryPDFView.as_view()),
]

