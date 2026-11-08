from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from datetime import date

from ..repository_impl import DjangoAccountingRepository
from ...application.accounting_service import AccountingService
from ...domain.value_objects import AccountData, AccountType, AccountCode


class AccountsView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._repo    = DjangoAccountingRepository()
        self._service = AccountingService(self._repo)

    def get(self, request):
        if not request.tenant or not request.tenant.has_module('contabilidad'):
            return Response({'error': 'Module not active or company not found'}, status=status.HTTP_403_FORBIDDEN)
        
        accounts = self._repo.list_accounts(request.tenant.id)
        if not accounts:
            self._inject_default_chart_of_accounts(request.tenant.id)
            accounts = self._repo.list_accounts(request.tenant.id)

        return Response([{
            'id':        acc.id,
            'code':      acc.code,
            'name':      acc.name,
            'type':      acc.type,
            'parent_id': acc.parent_id,
        } for acc in accounts])

    def _inject_default_chart_of_accounts(self, tenant_id: int):
        defaults = [
            (AccountCode('1.0.00.00'), 'Activos', AccountType.ASSET, None),
            (AccountCode('1.1.00.00'), 'Activos Corrientes', AccountType.ASSET, '1.0.00.00'),
            (AccountCode('1.1.01.01'), 'Caja y Bancos', AccountType.ASSET, '1.1.00.00'),
            (AccountCode('1.1.02.01'), 'Cuentas por Cobrar', AccountType.ASSET, '1.1.00.00'),
            (AccountCode('1.1.03.01'), 'Inventario', AccountType.ASSET, '1.1.00.00'),
            (AccountCode('2.0.00.00'), 'Pasivos', AccountType.LIABILITY, None),
            (AccountCode('2.1.00.00'), 'Pasivos Corrientes', AccountType.LIABILITY, '2.0.00.00'),
            (AccountCode('2.1.01.01'), 'Cuentas por Pagar', AccountType.LIABILITY, '2.1.00.00'),
            (AccountCode('2.1.03.01'), 'IVA por Pagar', AccountType.LIABILITY, '2.1.00.00'),
            (AccountCode('3.0.00.00'), 'Patrimonio', AccountType.EQUITY, None),
            (AccountCode('3.1.01.01'), 'Capital Social', AccountType.EQUITY, '3.0.00.00'),
            (AccountCode('4.0.00.00'), 'Ingresos', AccountType.REVENUE, None),
            (AccountCode('4.1.01.01'), 'Ingresos por Ventas', AccountType.REVENUE, '4.0.00.00'),
            (AccountCode('5.0.00.00'), 'Egresos', AccountType.EXPENSE, None),
            (AccountCode('5.1.01.01'), 'Costo de Ventas', AccountType.EXPENSE, '5.0.00.00'),
            (AccountCode('5.2.01.01'), 'Gastos Operativos', AccountType.EXPENSE, '5.0.00.00'),
        ]
        
        # Two-pass insertion to handle parents
        for code, name, acc_type, parent_code_str in defaults:
            parent_id = None
            if parent_code_str:
                # Find the parent in db
                from ..repository_impl import DjangoAccountingRepository
                from .django_models import AccountModel
                parent = AccountModel.objects.filter(tenant_id=tenant_id, code=parent_code_str).first()
                if parent:
                    parent_id = parent.id
                    
            self._service.get_or_create_account(AccountData(
                tenant_id=tenant_id,
                code=code,
                name=name,
                type=acc_type,
                parent_id=parent_id
            ))


    def post(self, request):
        if not request.tenant or not request.tenant.has_module('contabilidad'):
            return Response({'error': 'Module not active or company not found'}, status=status.HTTP_403_FORBIDDEN)

        code     = request.data.get('code', '').strip()
        name     = request.data.get('name', '').strip()
        type_str = request.data.get('type', 'is_active').strip().lower()

        if not code or not name:
            return Response(
                {'error': 'Fields "code" and "name" are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            account_type = AccountType(type_str)
        except ValueError:
            valid = [t.value for t in AccountType]
            return Response(
                {'error': f"Invalid type '{type_str}'. Valid values: {valid}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        account = self._service.get_or_create_account(AccountData(
            tenant_id=request.tenant.id,
            code=AccountCode(code),
            name=name,
            type=account_type,
        ))
        return Response({
            'id':        account.id,
            'code':      account.code,
            'name':      account.name,
            'type':      account.type,
            'parent_id': account.parent_id,
        }, status=status.HTTP_201_CREATED)


class AccountDetailView(APIView):
    def put(self, request, account_id):
        if not request.tenant or not request.tenant.has_module('contabilidad'):
            return Response({'error': 'Module not active or company not found'}, status=status.HTTP_403_FORBIDDEN)
            
        from modules.contabilidad.infrastructure.django_models import AccountModel
        acc = AccountModel.objects.filter(id=account_id, tenant_id=request.tenant.id).first()
        if not acc:
            return Response({'error': 'Account not found'}, status=status.HTTP_404_NOT_FOUND)
            
        name = request.data.get('name')
        if name:
            acc.name = name.strip()
            
        type_str = request.data.get('type')
        if type_str:
            acc.type = type_str.strip().lower()
            
        acc.save()
        return Response({'status': 'success', 'message': 'Account updated'})

    def delete(self, request, account_id):
        if not request.tenant or not request.tenant.has_module('contabilidad'):
            return Response({'error': 'Module not active or company not found'}, status=status.HTTP_403_FORBIDDEN)
            
        from modules.contabilidad.infrastructure.django_models import AccountModel, JournalEntryLineModel
        acc = AccountModel.objects.filter(id=account_id, tenant_id=request.tenant.id).first()
        if not acc:
            return Response({'error': 'Account not found'}, status=status.HTTP_404_NOT_FOUND)
            
        if JournalEntryLineModel.objects.filter(account_id=account_id).exists():
            return Response({'error': 'No se puede eliminar la cuenta porque ya tiene asientos contables asociados.'}, status=status.HTTP_400_BAD_REQUEST)
            
        acc.delete()
        return Response({'status': 'success', 'message': 'Account deleted'})

class JournalEntriesView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._repo    = DjangoAccountingRepository()
        self._service = AccountingService(self._repo)

    def get(self, request):
        if not request.tenant or not request.tenant.has_module('contabilidad'):
            return Response({'error': 'Module not active or company not found'}, status=status.HTTP_403_FORBIDDEN)
        
        entries = self._repo.get_journal_entries(request.tenant.id)
        return Response([{
            'id':          entry.id,
            'date':        entry.date,
            'description': entry.description,
            'type':        entry.type,
            'reference':   entry.reference,
            'lines': [{
                'id': line.id,
                'account_id': line.account_id,
                'account_code': line.account_code,
                'account_name': line.account_name,
                'debit': line.debit,
                'credit': line.credit,
            } for line in entry.lines] if entry.lines else [],
        } for entry in entries])

    def post(self, request):
        if not request.tenant or not request.tenant.has_module('contabilidad'):
            return Response({'error': 'Module not active or company not found'}, status=status.HTTP_403_FORBIDDEN)
        try:
            date_str   = request.data.get('date')
            entry_date = date.fromisoformat(date_str[:10]) if date_str else date.today()
            description = request.data.get('description', 'Manual Entry').strip()
            reference   = request.data.get('reference', '').strip()
            lines       = request.data.get('lines', [])

            if not lines:
                return Response(
                    {'error': 'A journal entry requires at least 2 lines'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            entry = self._service.create_journal_entry(
                tenant_id=request.tenant.id,
                description=description,
                lines=lines,
                entry_date=entry_date,
                reference=reference,
            )
            return Response(
                {'id': entry.id, 'description': entry.description},
                status=status.HTTP_201_CREATED,
            )
        except (ValueError, Exception) as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class JournalEntryDetailView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._repo = DjangoAccountingRepository()

    def get(self, request, entry_id):
        if not request.tenant or not request.tenant.has_module('contabilidad'):
            return Response({'error': 'Module not active or company not found'}, status=status.HTTP_403_FORBIDDEN)
        
        entry = self._repo.get_journal_entry_by_id(request.tenant.id, entry_id)
        if not entry:
            return Response({'error': 'Journal entry not found'}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'id':          entry.id,
            'date':        entry.date,
            'description': entry.description,
            'type':        entry.type,
            'reference':   entry.reference,
            'lines': [{
                'id':           line.id,
                'account_id':   line.account_id,
                'account_code': line.account_code,
                'account_name': line.account_name,
                'debit':        str(line.debit),
                'credit':       str(line.credit),
            } for line in entry.lines],
        })

from ..django_models import CentroCostoModel

class CentrosCostosView(APIView):
    def get(self, request):
        if not request.tenant or not request.tenant.has_module('contabilidad'):
            return Response({'error': 'Module not active or company not found'}, status=status.HTTP_403_FORBIDDEN)
        
        ccs = CentroCostoModel.objects.filter(tenant_id=request.tenant.id).order_by('code')
        return Response([{
            'id': cc.id,
            'code': cc.code,
            'name': cc.name,
            'description': cc.description,
            'is_active': cc.is_active,
            'created_at': cc.created_at.isoformat()
        } for cc in ccs])

    def post(self, request):
        if not request.tenant or not request.tenant.has_module('contabilidad'):
            return Response({'error': 'Module not active or company not found'}, status=status.HTTP_403_FORBIDDEN)
        
        code = request.data.get('code', '').strip()
        name = request.data.get('name', '').strip()
        description = request.data.get('description', '').strip()
        
        if not code or not name:
            return Response({'error': 'Code and name are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if CentroCostoModel.objects.filter(tenant_id=request.tenant.id, code=code).exists():
            return Response({'error': f'Code {code} already exists'}, status=status.HTTP_400_BAD_REQUEST)
            
        cc = CentroCostoModel.objects.create(
            tenant_id=request.tenant.id,
            code=code,
            name=name,
            description=description,
            is_active=True
        )
        return Response({
            'id': cc.id,
            'code': cc.code,
            'name': cc.name,
            'description': cc.description,
            'is_active': cc.is_active,
            'created_at': cc.created_at.isoformat()
        }, status=status.HTTP_201_CREATED)


class CentroCostoDetailView(APIView):
    def put(self, request, cc_id):
        if not request.tenant or not request.tenant.has_module('contabilidad'):
            return Response({'error': 'Module not active or company not found'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            cc = CentroCostoModel.objects.get(tenant_id=request.tenant.id, id=cc_id)
        except CentroCostoModel.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
            
        code = request.data.get('code', cc.code).strip()
        if code != cc.code and CentroCostoModel.objects.filter(tenant_id=request.tenant.id, code=code).exists():
            return Response({'error': f'Code {code} already exists'}, status=status.HTTP_400_BAD_REQUEST)
            
        cc.code = code
        cc.name = request.data.get('name', cc.name).strip()
        cc.description = request.data.get('description', cc.description).strip()
        cc.is_active = request.data.get('is_active', cc.is_active)
        cc.save()
        
        return Response({
            'id': cc.id,
            'code': cc.code,
            'name': cc.name,
            'description': cc.description,
            'is_active': cc.is_active,
            'created_at': cc.created_at.isoformat()
        })


from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

@method_decorator(csrf_exempt, name='dispatch')
class SeedAccountsView(APIView):
    def post(self, request):
        if not request.tenant or not request.tenant.has_module('contabilidad'):
            return Response({'error': 'Module not active or company not found'}, status=status.HTTP_403_FORBIDDEN)
            
        from modules.contabilidad.infrastructure.django_models import AccountModel
        
        standard_accounts = [
            ('1.0.00.00', 'Activos', 'activo'),
            ('1.1.01.01', 'Caja y Bancos', 'activo'),
            ('1.1.02.01', 'Cuentas por Cobrar Clientes', 'activo'),
            ('1.1.03.01', 'IVA Pagado en Compras', 'activo'),
            ('1.1.04.01', 'Inventario de Mercaderías', 'activo'),
            
            ('2.0.00.00', 'Pasivos', 'pasivo'),
            ('2.1.01.01', 'Proveedores por Pagar', 'pasivo'),
            ('2.1.02.01', 'Sueldos por Pagar', 'pasivo'),
            ('2.1.03.01', 'IVA por Pagar', 'pasivo'),
            
            ('3.0.00.00', 'Patrimonio', 'patrimonio'),
            ('3.1.01.01', 'Capital Social', 'patrimonio'),
            
            ('4.0.00.00', 'Ingresos', 'ingreso'),
            ('4.1.01.01', 'Ingresos por Ventas', 'ingreso'),
            ('4.1.02.01', 'Ingresos por Servicios', 'ingreso'),
            
            ('5.0.00.00', 'Egresos y Gastos', 'egreso'),
            ('5.1.01.01', 'Gastos Generales', 'egreso'),
            ('5.1.02.01', 'Suministros y Útiles de Oficina', 'egreso'),
            ('5.1.03.01', 'Servicios Básicos (Luz, Agua, Teléfono)', 'egreso'),
            ('5.1.04.01', 'Honorarios Profesionales', 'egreso'),
            ('5.1.05.01', 'Arriendos Pagados', 'egreso'),
            ('5.1.06.01', 'Gastos de Alimentación', 'egreso'),
            ('5.1.07.01', 'Mantenimiento y Reparaciones', 'egreso'),
            
            ('6.0.00.00', 'Costos', 'costo'),
            ('6.1.01.01', 'Costo de Ventas', 'costo')
        ]
        
        for code, name, t in standard_accounts:
            AccountModel.objects.get_or_create(
                tenant_id=request.tenant.id,
                code=code,
                defaults={'name': name, 'type': t}
            )
            
        return Response({'status': 'success', 'message': 'Plan de Cuentas generado'})


class ExportAccountsExcelView(APIView):
    def get(self, request):
        if not request.tenant or not request.tenant.has_module('contabilidad'):
            return Response({'error': 'Module not active or company not found'}, status=status.HTTP_403_FORBIDDEN)
            
        from modules.contabilidad.infrastructure.django_models import AccountModel
        from modules.reportes.infrastructure.excel_generator import generate_chart_of_accounts_excel
        from modules.parametros.infrastructure.repository_impl import DjangoParameterRepository
        from modules.parametros.application.use_cases import GetAllParameters

        cuentas = list(AccountModel.objects.filter(tenant_id=request.tenant.id).order_by('code').values('code', 'name', 'type'))
        
        repo = DjangoParameterRepository()
        params = GetAllParameters(repo).execute(request.tenant.id)
        
        tenant_dict = {
            'name': getattr(request.tenant, 'name', 'ERP'),
            'primary_color': getattr(request.tenant, 'primary_color', '#1976D2'),
            'secondary_color': getattr(request.tenant, 'secondary_color', '#1565C0'),
            'logo_url': getattr(request.tenant, 'logo_url', None),
        }
        
        excel_bytes = generate_chart_of_accounts_excel(cuentas, params, tenant_dict)
        response = HttpResponse(excel_bytes, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="Plan_de_Cuentas.xlsx"'
        return response
