from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, F
from ..django_models import AccountModel, JournalEntryLineModel, JournalEntryModel

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

        qs = JournalEntryLineModel.objects.filter(entry__tenant_id=tenant_id)
        if start_date:
            qs = qs.filter(entry__date__gte=start_date)
        if end_date:
            qs = qs.filter(entry__date__lte=end_date)

        # Solo Ingresos y Egresos
        qs = qs.filter(account__type__in=['ingreso', 'egreso'])

        aggregations = qs.values(
            'account__id', 'account__name', 'account__type'
        ).annotate(
            total_debit=Sum('debit'),
            total_credit=Sum('credit')
        )

        ingresos = []
        egresos = []
        total_ingresos = 0
        total_egresos = 0

        for agg in aggregations:
            debit = agg['total_debit'] or 0
            credit = agg['total_credit'] or 0
            acc_type = agg['account__type']
            
            if acc_type == 'ingreso':
                bal = credit - debit
                total_ingresos += bal
                ingresos.append({'id': agg['account__id'], 'name': agg['account__name'], 'balance': bal})
            elif acc_type == 'egreso':
                bal = debit - credit
                total_egresos += bal
                egresos.append({'id': agg['account__id'], 'name': agg['account__name'], 'balance': bal})

        utilidad_neta = total_ingresos - total_egresos

        return Response({
            'ingresos': ingresos,
            'total_ingresos': total_ingresos,
            'egresos': egresos,
            'total_egresos': total_egresos,
            'utilidad_neta': utilidad_neta
        })

class BalanceSheetView(APIView):
    # Balance General
    def get(self, request):
        tenant_id = request.tenant.id
        date_up_to = request.query_params.get('date') # Balance up to a specific date
        
        qs = JournalEntryLineModel.objects.filter(entry__tenant_id=tenant_id)
        if date_up_to:
            qs = qs.filter(entry__date__lte=date_up_to)

        # Solo Activos, Pasivos, Patrimonio
        # type 'is_active' = Activo
        qs_balance = qs.filter(account__type__in=['is_active', 'pasivo', 'patrimonio'])

        aggregations = qs_balance.values(
            'account__id', 'account__name', 'account__type'
        ).annotate(
            total_debit=Sum('debit'),
            total_credit=Sum('credit')
        )

        activos = []
        pasivos = []
        patrimonio = []
        total_activos = 0
        total_pasivos = 0
        total_patrimonio = 0

        for agg in aggregations:
            debit = agg['total_debit'] or 0
            credit = agg['total_credit'] or 0
            acc_type = agg['account__type']
            
            if acc_type == 'is_active':
                bal = debit - credit
                total_activos += bal
                activos.append({'id': agg['account__id'], 'name': agg['account__name'], 'balance': bal})
            elif acc_type == 'pasivo':
                bal = credit - debit
                total_pasivos += bal
                pasivos.append({'id': agg['account__id'], 'name': agg['account__name'], 'balance': bal})
            elif acc_type == 'patrimonio':
                bal = credit - debit
                total_patrimonio += bal
                patrimonio.append({'id': agg['account__id'], 'name': agg['account__name'], 'balance': bal})

        # Calculate Net Income from P&L up to that date, which rolls into Equity (Patrimonio)
        qs_pnl = qs.filter(account__type__in=['ingreso', 'egreso']).aggregate(
            debit=Sum('debit'), credit=Sum('credit')
        )
        # Note: we need to group by type manually to get exact income vs expense, or just net
        # Net = Total Ingresos (Credit - Debit) - Total Egresos (Debit - Credit)
        # Net = (Credit(I) - Debit(I)) - (Debit(E) - Credit(E))
        # Net = Credit(I) - Debit(I) - Debit(E) + Credit(E)
        # Net = Total Credit (I+E) - Total Debit (I+E)
        net_income = (qs_pnl['credit'] or 0) - (qs_pnl['debit'] or 0)
        
        if net_income != 0:
            patrimonio.append({
                'id': 'utilidad_ejercicio',
                'name': 'Utilidad del Ejercicio',
                'balance': net_income
            })
            total_patrimonio += net_income

        return Response({
            'activos': activos,
            'total_activos': total_activos,
            'pasivos': pasivos,
            'total_pasivos': total_pasivos,
            'patrimonio': patrimonio,
            'total_patrimonio': total_patrimonio,
            'ecuacion_balance': total_activos == (total_pasivos + total_patrimonio)
        })

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
