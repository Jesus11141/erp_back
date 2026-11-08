from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from django.db.models import Sum, F
from ..django_models import AccountModel, JournalEntryLineModel, JournalEntryModel
from ...application.financial_reports_exporter import (
    fetch_balance_sheet_data,
    fetch_pnl_data,
    generate_balance_sheet_pdf,
    generate_balance_sheet_excel,
    generate_pnl_pdf,
    generate_pnl_excel,
)

class GeneralLedgerView(APIView):
    def get(self, request):
        tenant_id = request.tenant.id
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        account_id = request.query_params.get('account_id')

        qs = JournalEntryLineModel.objects.filter(entry__tenant_id=tenant_id)
        if start_date:
            qs = qs.filter(entry__date__gte=start_date)
        if end_date:
            qs = qs.filter(entry__date__lte=end_date)
        if account_id:
            qs = qs.filter(account_id=account_id)

        # Aggregate totals per account
        aggregations = qs.values(
            'account__id', 'account__code', 'account__name', 'account__type'
        ).annotate(
            total_debit=Sum('debit'),
            total_credit=Sum('credit')
        ).order_by('account__code')

        results = []
        for agg in aggregations:
            debit = agg['total_debit'] or 0
            credit = agg['total_credit'] or 0
            # For Activos & Egresos -> Balance = Debit - Credit
            # For Pasivos, Patrimonio & Ingresos -> Balance = Credit - Debit
            # Note: in this DB, Activo is stored as 'is_active'
            acc_type = agg['account__type']
            if acc_type in ['is_active', 'egreso']:
                balance = debit - credit
            else:
                balance = credit - debit

            results.append({
                'account_id': agg['account__id'],
                'code': agg['account__code'],
                'name': agg['account__name'],
                'type': acc_type,
                'total_debit': debit,
                'total_credit': credit,
                'balance': balance
            })

        return Response(results)

class PnLView(APIView):
    # Estado de Resultados (Profit & Loss)
    def get(self, request):
        tenant_id = request.tenant.id
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        data = fetch_pnl_data(tenant_id, start_date=start_date, end_date=end_date)
        return Response(data)

class BalanceSheetView(APIView):
    # Balance General
    def get(self, request):
        tenant_id = request.tenant.id
        date_up_to = request.query_params.get('date') or request.query_params.get('date_up_to')
        data = fetch_balance_sheet_data(tenant_id, date_up_to=date_up_to)
        return Response(data)

class ExportBalanceSheetPDFView(APIView):
    """Descarga oficial del Balance General en PDF corporativo."""
    def get(self, request):
        tenant_id = request.tenant.id
        date_up_to = request.query_params.get('date') or request.query_params.get('date_up_to')
        data = fetch_balance_sheet_data(tenant_id, date_up_to=date_up_to)
        pdf_bytes = generate_balance_sheet_pdf(data, tenant_id, data['date_up_to'])

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        filename = f"balance_general_{data['date_up_to']}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

class ExportBalanceSheetExcelView(APIView):
    """Descarga oficial del Balance General en Excel corporativo."""
    def get(self, request):
        tenant_id = request.tenant.id
        date_up_to = request.query_params.get('date') or request.query_params.get('date_up_to')
        data = fetch_balance_sheet_data(tenant_id, date_up_to=date_up_to)
        excel_bytes = generate_balance_sheet_excel(data, tenant_id, data['date_up_to'])

        response = HttpResponse(
            excel_bytes,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = f"balance_general_{data['date_up_to']}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

class ExportPnLPDFView(APIView):
    """Descarga oficial del Estado de Resultados en PDF corporativo."""
    def get(self, request):
        tenant_id = request.tenant.id
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        data = fetch_pnl_data(tenant_id, start_date=start_date, end_date=end_date)
        pdf_bytes = generate_pnl_pdf(data, tenant_id, data['start_date'], data['end_date'])

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        filename = f"estado_resultados_{data['start_date']}_{data['end_date']}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

class ExportPnLExcelView(APIView):
    """Descarga oficial del Estado de Resultados en Excel corporativo."""
    def get(self, request):
        tenant_id = request.tenant.id
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        data = fetch_pnl_data(tenant_id, start_date=start_date, end_date=end_date)
        excel_bytes = generate_pnl_excel(data, tenant_id, data['start_date'], data['end_date'])

        response = HttpResponse(
            excel_bytes,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = f"estado_resultados_{data['start_date']}_{data['end_date']}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

class AccountLedgerView(APIView):
    def get(self, request, account_id):
        tenant_id = request.tenant.id
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        qs = JournalEntryLineModel.objects.filter(
            entry__tenant_id=tenant_id,
            account_id=account_id
        ).select_related('entry').order_by('entry__date', 'entry__id')

        if start_date:
            qs = qs.filter(entry__date__gte=start_date)
        if end_date:
            qs = qs.filter(entry__date__lte=end_date)

        results = []
        balance = 0
        
        # We need to know the account type to calculate running balance correctly
        account = AccountModel.objects.filter(id=account_id).first()
        if not account:
            return Response({'error': 'Account not found'}, status=404)
            
        for line in qs:
            # Running balance logic
            debit = float(line.debit)
            credit = float(line.credit)
            
            if account.type in ['is_active', 'egreso']:
                balance += (debit - credit)
            else:
                balance += (credit - debit)
                
            results.append({
                'id': line.id,
                'date': line.entry.date,
                'reference': line.entry.reference,
                'description': line.entry.description,
                'debit': debit,
                'credit': credit,
                'running_balance': balance
            })

        return Response({
            'account': {
                'id': account.id,
                'code': account.code,
                'name': account.name,
                'type': account.type
            },
            'lines': results
        })
