from django.urls import path
from .views import AccountsView, AccountDetailView, JournalEntriesView, JournalEntryDetailView, CentrosCostosView, CentroCostoDetailView, SeedAccountsView
from .report_views import GeneralLedgerView, PnLView, BalanceSheetView, AccountLedgerView

urlpatterns = [
    path('cuentas/seed/', SeedAccountsView.as_view()),
    path('cuentas/', AccountsView.as_view()),
    path('cuentas/<int:account_id>/', AccountDetailView.as_view()),
    path('asientos/', JournalEntriesView.as_view()),
    path('asientos/<int:entry_id>/', JournalEntryDetailView.as_view()),
    path('centros-costos/', CentrosCostosView.as_view()),
    path('centros-costos/<int:cc_id>/', CentroCostoDetailView.as_view()),
    path('reportes/mayor/', GeneralLedgerView.as_view()),
    path('reportes/pnl/', PnLView.as_view()),
    path('reportes/balance/', BalanceSheetView.as_view()),
    path('reportes/mayor/auxiliar/<int:account_id>/', AccountLedgerView.as_view()),
]
