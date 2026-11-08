from django.urls import path
from .views import (
    AccountsView, AccountDetailView, JournalEntriesView, 
    JournalEntryDetailView, CentrosCostosView, CentroCostoDetailView, 
    SeedAccountsView, ExportAccountsExcelView
)
from .report_views import (
    GeneralLedgerView, PnLView, BalanceSheetView, AccountLedgerView,
    ExportBalanceSheetPDFView, ExportBalanceSheetExcelView,
    ExportPnLPDFView, ExportPnLExcelView
)
from .bank_views import (
    BankAccountsView, BankAccountDetailView,
    CashManagementItemsView, CashManagementGenerateView, CashManagementApplyPaymentsView,
    BankReconciliationsView, BankReconciliationUploadView, BankReconciliationDetailView,
    BankReconciliationMatchToggleView, BankReconciliationFinalizeView,
    BankReconciliationExportPDFView, BankReconciliationExportExcelView
)
from .period_views import (
    AccountingPeriodsView, AccountingPeriodStatusUpdateView
)

urlpatterns = [
    path('cuentas/export/excel/', ExportAccountsExcelView.as_view()),
    path('cuentas/seed/', SeedAccountsView.as_view()),
    path('cuentas/', AccountsView.as_view()),
    path('cuentas/<int:account_id>/', AccountDetailView.as_view()),
    path('asientos/', JournalEntriesView.as_view()),
    path('asientos/<int:entry_id>/', JournalEntryDetailView.as_view()),
    path('centros-costos/', CentrosCostosView.as_view()),
    path('centros-costos/<int:cc_id>/', CentroCostoDetailView.as_view()),
    path('reportes/mayor/', GeneralLedgerView.as_view()),
    path('reportes/pnl/', PnLView.as_view()),
    path('reportes/pnl/export/pdf/', ExportPnLPDFView.as_view()),
    path('reportes/pnl/export/excel/', ExportPnLExcelView.as_view()),
    path('reportes/balance/', BalanceSheetView.as_view()),
    path('reportes/balance/export/pdf/', ExportBalanceSheetPDFView.as_view()),
    path('reportes/balance/export/excel/', ExportBalanceSheetExcelView.as_view()),
    path('reportes/mayor/auxiliar/<int:account_id>/', AccountLedgerView.as_view()),

    # Cuentas Bancarias de la Empresa (Cero datos quemados)
    path('bancos/', BankAccountsView.as_view()),
    path('bancos/<int:pk>/', BankAccountDetailView.as_view()),

    # Cash Management Bancario (Pichincha, Guayaquil, Produbanco)
    path('cash-management/items/', CashManagementItemsView.as_view()),
    path('cash-management/generate/', CashManagementGenerateView.as_view()),
    path('cash-management/apply-payments/', CashManagementApplyPaymentsView.as_view()),

    # Conciliación Bancaria Automática
    path('conciliaciones/', BankReconciliationsView.as_view()),
    path('conciliaciones/upload/', BankReconciliationUploadView.as_view()),
    path('conciliaciones/<int:pk>/', BankReconciliationDetailView.as_view()),
    path('conciliaciones/<int:pk>/match/', BankReconciliationMatchToggleView.as_view()),
    path('conciliaciones/<int:pk>/finalize/', BankReconciliationFinalizeView.as_view()),
    path('conciliaciones/<int:pk>/export/pdf/', BankReconciliationExportPDFView.as_view()),
    path('conciliaciones/<int:pk>/export/excel/', BankReconciliationExportExcelView.as_view()),

    # Control y Bloqueo de Períodos Contables / Meses Fiscales
    path('periodos/', AccountingPeriodsView.as_view()),
    path('periodos/status/', AccountingPeriodStatusUpdateView.as_view()),
]
