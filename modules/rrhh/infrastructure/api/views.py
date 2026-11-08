from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ...infrastructure.repository_impl import DjangoEmployeeRepository, DjangoAttendanceRepository, DjangoPayrollRepository
from ...application.use_cases import CreateEmployee, RegisterAttendance, GeneratePayroll, ApprovePayroll
from modules.shared.role_permissions import admin_only

def verify_module(request):
    if not request.tenant or not request.tenant.has_module('rrhh'):
        return Response({'error': 'Module not available'}, status=status.HTTP_403_FORBIDDEN)

def _employee_dict(e, tenant_id):
    from ..django_models import JobPositionModel
    pos = JobPositionModel.objects.filter(tenant_id=tenant_id, name=e.position).first()
    return {
        'id': e.id,
        'name': e.name,
        'identification': getattr(e, 'identification', '') or '',
        'cedula': getattr(e, 'identification', '') or '',
        'email': e.email,
        'phone': e.phone,
        'position': e.position,
        'department': e.department,
        'salary': str(e.salary),
        'contract_type': e.contract_type,
        'tenure_years': e.tenure_years,
        'pin_caja': getattr(e, 'cash_register_pin', ''),
        'active': e.active,
        'has_iess': getattr(e, 'has_iess', False),
        'accumulates_13th': getattr(e, 'accumulates_13th', True),
        'accumulates_14th': getattr(e, 'accumulates_14th', True),
        'bank_name': getattr(e, 'bank_name', '') or '',
        'bank_account_type': getattr(e, 'bank_account_type', 'ahorros') or 'ahorros',
        'bank_account_number': getattr(e, 'bank_account_number', '') or '',
        'active_dependents_count': getattr(e, 'active_dependents_count', 0)
    }

class EmployeesView(APIView):
    def get(self, request):
        if not request.tenant or not (request.tenant.has_module('rrhh') or request.tenant.has_module('pos')):
            return Response({'error': 'Module not available'}, status=status.HTTP_403_FORBIDDEN)
        employees = DjangoEmployeeRepository().list_by_tenant(request.tenant.id)
        return Response([_employee_dict(e, request.tenant.id) for e in employees])

    def post(self, request):
        if not request.tenant or not (request.tenant.has_module('rrhh') or request.tenant.has_module('pos')):
            return Response({'error': 'Module not available'}, status=status.HTTP_403_FORBIDDEN)
        if e := admin_only(request): return e
        try:
            employee = CreateEmployee(DjangoEmployeeRepository()).execute(request.tenant.id, request.data)
            return Response(_employee_dict(employee, request.tenant.id), status=status.HTTP_201_CREATED)
        except (ValueError, KeyError) as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class EmployeeDetailView(APIView):
    def put(self, request, employee_id):
        if not request.tenant or not (request.tenant.has_module('rrhh') or request.tenant.has_module('pos')):
            return Response({'error': 'Module not available'}, status=status.HTTP_403_FORBIDDEN)
        if e := admin_only(request): return e
        
        repo = DjangoEmployeeRepository()
        employee = repo.find_by_id(employee_id, request.tenant.id)
        if not employee:
            return Response({'error': 'Employee not found'}, status=status.HTTP_404_NOT_FOUND)
            
        name = request.data.get('nombre', request.data.get('name'))
        email = request.data.get('email')
        phone = request.data.get('telefono', request.data.get('phone', ''))
        position = request.data.get('puesto', request.data.get('position'))
        department = request.data.get('departamento', request.data.get('department', 'General'))
        hire_date = request.data.get('fecha_ingreso', request.data.get('hire_date'))
        salary = request.data.get('salario', request.data.get('salary'))
        contract_type = request.data.get('tipo_contrato', request.data.get('contract_type', 'full_time'))
        cash_register_pin = request.data.get('cash_register_pin', request.data.get('pin_caja'))
        active = request.data.get('activo', request.data.get('active'))
        
        if not name or not position or salary is None:
            return Response({'error': 'Name, position and salary are required fields'}, status=status.HTTP_400_BAD_REQUEST)
            
        employee.name = name
        employee.email = email
        employee.phone = phone
        employee.position = position
        employee.department = department
        if hire_date:
            from datetime import date
            try:
                if isinstance(hire_date, str):
                    employee.hire_date = date.fromisoformat(hire_date[:10])
                else:
                    employee.hire_date = hire_date
            except (ValueError, TypeError):
                pass
        if salary is not None:
            from decimal import Decimal
            try:
                employee.salary = Decimal(str(salary))
            except Exception:
                pass
        employee.contract_type = contract_type
        employee.cash_register_pin = cash_register_pin
        if active is not None:
            employee.active = bool(active)
            
        identification = request.data.get('cedula', request.data.get('identification'))
        if identification is not None:
            employee.identification = str(identification).strip()
            
        if 'has_iess' in request.data:
            employee.has_iess = bool(request.data['has_iess'])
        if 'accumulates_13th' in request.data:
            employee.accumulates_13th = bool(request.data['accumulates_13th'])
        if 'accumulates_14th' in request.data:
            employee.accumulates_14th = bool(request.data['accumulates_14th'])
            
        bank_name = request.data.get('bank_name', request.data.get('banco'))
        if bank_name is not None:
            employee.bank_name = str(bank_name).strip()
            
        bank_acc_type = request.data.get('bank_account_type', request.data.get('tipo_cuenta_banco'))
        if bank_acc_type is not None:
            employee.bank_account_type = str(bank_acc_type).strip()
            
        bank_acc_num = request.data.get('bank_account_number', request.data.get('numero_cuenta_banco'))
        if bank_acc_num is not None:
            employee.bank_account_number = str(bank_acc_num).strip()
            
        repo.save(employee)
        return Response(_employee_dict(employee, request.tenant.id))

    def delete(self, request, employee_id):
        if not request.tenant or not (request.tenant.has_module('rrhh') or request.tenant.has_module('pos')):
            return Response({'error': 'Module not available'}, status=status.HTTP_403_FORBIDDEN)
        if e := admin_only(request): return e
        
        from modules.rrhh.infrastructure.django_models import EmployeeModel
        EmployeeModel.objects.filter(id=employee_id, tenant_id=request.tenant.id).update(active=False)
        return Response({'success': True})

class DependentsView(APIView):
    def get(self, request, employee_id):
        if e := verify_module(request): return e
        from ...infrastructure.repository_impl import DjangoDependentRepository
        deps = DjangoDependentRepository().list_by_employee(employee_id, request.tenant.id)
        return Response([{
            'id': d.id,
            'full_name': d.full_name,
            'birth_date': str(d.birth_date),
            'relationship': d.relationship,
            'identification': d.identification,
            'has_disability': d.has_disability,
            'active': d.active,
            'age': d.age,
            'is_valid_carga': d.is_valid_carga
        } for d in deps])

    def post(self, request, employee_id):
        if e := verify_module(request): return e
        if e := admin_only(request): return e
        from ...infrastructure.repository_impl import DjangoDependentRepository
        from ...domain.entities import Dependent
        from datetime import date
        try:
            birth = date.fromisoformat(request.data.get('birth_date')[:10])
            dep = Dependent(
                id=0,
                tenant_id=request.tenant.id,
                employee_id=employee_id,
                full_name=request.data.get('full_name'),
                birth_date=birth,
                relationship=request.data.get('relationship'),
                identification=request.data.get('identification', ''),
                has_disability=request.data.get('has_disability', False),
                active=request.data.get('active', True)
            )
            saved = DjangoDependentRepository().save(dep)
            return Response({'id': saved.id}, status=status.HTTP_201_CREATED)
        except Exception as err:
            return Response({'error': str(err)}, status=status.HTTP_400_BAD_REQUEST)

class DependentDetailView(APIView):
    def put(self, request, employee_id, dep_id):
        if e := verify_module(request): return e
        if e := admin_only(request): return e
        from ...infrastructure.repository_impl import DjangoDependentRepository
        repo = DjangoDependentRepository()
        dep = repo.find_by_id(dep_id, request.tenant.id)
        if not dep or dep.employee_id != employee_id:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        
        dep.full_name = request.data.get('full_name', dep.full_name)
        dep.relationship = request.data.get('relationship', dep.relationship)
        dep.identification = request.data.get('identification', dep.identification)
        dep.has_disability = request.data.get('has_disability', dep.has_disability)
        dep.active = request.data.get('active', dep.active)
        bd = request.data.get('birth_date')
        if bd:
            from datetime import date
            try: dep.birth_date = date.fromisoformat(bd[:10])
            except: pass
        
        repo.save(dep)
        return Response({'message': 'Updated'})

    def delete(self, request, employee_id, dep_id):
        if e := verify_module(request): return e
        if e := admin_only(request): return e
        from ...infrastructure.repository_impl import DjangoDependentRepository
        DjangoDependentRepository().delete(dep_id, request.tenant.id)
        return Response({'message': 'Deleted'})

class SalaryHistoryView(APIView):
    def get(self, request, employee_id):
        if e := verify_module(request): return e
        from ...infrastructure.repository_impl import DjangoSalaryHistoryRepository
        history = DjangoSalaryHistoryRepository().list_by_employee(employee_id, request.tenant.id)
        return Response([{
            'id': h.id,
            'old_salary': str(h.old_salary),
            'new_salary': str(h.new_salary),
            'change_date': str(h.change_date),
            'reason': h.reason
        } for h in history])

class LoansView(APIView):
    def get(self, request, employee_id):
        if e := verify_module(request): return e
        from ...infrastructure.repository_impl import DjangoLoanRepository
        loans = DjangoLoanRepository().list_by_employee(employee_id, request.tenant.id)
        return Response([{
            'id': l.id,
            'type': l.type,
            'total_amount': str(l.total_amount),
            'monthly_installment': str(l.monthly_installment),
            'start_date': str(l.start_date),
            'active': l.active
        } for l in loans])

    def post(self, request, employee_id):
        if e := verify_module(request): return e
        if e := admin_only(request): return e
        from ...infrastructure.repository_impl import DjangoLoanRepository
        from ...domain.entities import Loan
        from datetime import date
        from decimal import Decimal
        try:
            start = date.fromisoformat(request.data.get('start_date')[:10])
            loan = Loan(
                id=0,
                tenant_id=request.tenant.id,
                employee_id=employee_id,
                type=request.data.get('type'),
                total_amount=Decimal(str(request.data.get('total_amount'))),
                monthly_installment=Decimal(str(request.data.get('monthly_installment'))),
                start_date=start,
                active=request.data.get('active', True)
            )
            saved = DjangoLoanRepository().save(loan)
            return Response({'id': saved.id}, status=status.HTTP_201_CREATED)
        except Exception as err:
            return Response({'error': str(err)}, status=status.HTTP_400_BAD_REQUEST)

class LoanDetailView(APIView):
    def put(self, request, employee_id, loan_id):
        if e := verify_module(request): return e
        if e := admin_only(request): return e
        from ...infrastructure.repository_impl import DjangoLoanRepository
        repo = DjangoLoanRepository()
        loan = repo.find_by_id(loan_id, request.tenant.id)
        if not loan or loan.employee_id != employee_id:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        
        loan.active = request.data.get('active', loan.active)
        repo.save(loan)
        return Response({'message': 'Updated'})

    def delete(self, request, employee_id, loan_id):
        if e := verify_module(request): return e
        if e := admin_only(request): return e
        from ...infrastructure.repository_impl import DjangoLoanRepository
        DjangoLoanRepository().delete(loan_id, request.tenant.id)
        return Response({'message': 'Deleted'})

class AttendancesView(APIView):
    def get(self, request):
        if e := verify_module(request): return e
        date_query = request.query_params.get('fecha', request.query_params.get('date', ''))
        attendances = DjangoAttendanceRepository().list_by_date(date_query, request.tenant.id) if date_query else []
        return Response([{
            'id': a.id,
            'employee_name': a.employee_name,
            'date': a.date,
            'check_in': a.check_in,
            'check_out': a.check_out,
            'status': a.status
        } for a in attendances])

    def post(self, request):
        if e := verify_module(request): return e
        try:
            employee_id = request.data.get('employee_id', request.data.get('empleado_id'))
            attendance = RegisterAttendance(
                DjangoEmployeeRepository(), DjangoAttendanceRepository()
            ).execute(request.tenant.id, employee_id, request.data)
            return Response({'id': attendance.id, 'status': attendance.status}, status=status.HTTP_201_CREATED)
        except (ValueError, KeyError) as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

def _payroll_dict(n):
    return {
        'id': n.id,
        'employee_name': n.employee_name,
        'employee_id': n.employee_id,
        'period_start': n.period_start,
        'period_end': n.period_end,
        'base_salary': str(n.base_salary),
        'deductions': str(n.deductions),
        'bonuses': str(n.bonuses),
        'iess_personal': str(n.iess_personal),
        'iess_employer': str(n.iess_employer),
        'thirteenth_salary': str(n.thirteenth_salary),
        'fourteenth_salary': str(n.fourteenth_salary),
        'reserve_funds': str(n.reserve_funds),
        'net_salary': str(n.net_salary),
        'total_net': str(n.total_net),
        'status': n.status,
        'employee_identification': getattr(n, 'employee_identification', '') or '',
    }

class PayrollsView(APIView):
    def get(self, request):
        if e := verify_module(request): return e
        payrolls = DjangoPayrollRepository().list_by_tenant(request.tenant.id)
        return Response([_payroll_dict(n) for n in payrolls])

    def post(self, request):
        if e := verify_module(request): return e
        try:
            from modules.parametros.infrastructure.repository_impl import DjangoParameterRepository
            from ...infrastructure.repository_impl import DjangoLoanRepository
            from decimal import Decimal
            employee_id = request.data.get('employee_id', request.data.get('empleado_id'))
            
            # Deduct active loans
            loans = DjangoLoanRepository().list_by_employee(employee_id, request.tenant.id)
            loan_deductions = sum(l.monthly_installment for l in loans if l.active)
            current_deductions = Decimal(str(request.data.get('deductions', 0)))
            request.data['deductions'] = float(current_deductions + loan_deductions)

            payroll = GeneratePayroll(
                DjangoEmployeeRepository(), DjangoPayrollRepository(), DjangoParameterRepository()
            ).execute(request.tenant.id, employee_id, request.data)
            return Response(_payroll_dict(payroll), status=status.HTTP_201_CREATED)
        except (ValueError, KeyError) as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class PayrollActionView(APIView):
    def post(self, request, payroll_id, action):
        if e := verify_module(request): return e
        try:
            if action == 'aprobar' or action == 'approve':
                payroll = ApprovePayroll(DjangoPayrollRepository()).execute(payroll_id, request.tenant.id)
                return Response({'status': payroll.status})
            return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class MassPayrollsView(APIView):
    def post(self, request):
        if e := verify_module(request): return e
        try:
            from modules.parametros.infrastructure.repository_impl import DjangoParameterRepository
            from ...application.use_cases import GenerateMassPayroll
            count = GenerateMassPayroll(
                DjangoEmployeeRepository(), DjangoPayrollRepository(), DjangoParameterRepository()
            ).execute(request.tenant.id, request.data)
            return Response({'generated': count}, status=status.HTTP_201_CREATED)
        except (ValueError, KeyError) as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class JobPositionView(APIView):
    def get(self, request):
        if not request.tenant or not (request.tenant.has_module('rrhh') or request.tenant.has_module('pos')):
            return Response({'error': 'Module not available'}, status=status.HTTP_403_FORBIDDEN)
        from ...infrastructure.django_models import JobPositionModel
        positions = JobPositionModel.objects.filter(tenant_id=request.tenant.id)
        return Response([{'id': p.id, 'name': p.name, 'active': p.active} for p in positions])

    def post(self, request):
        if not request.tenant or not (request.tenant.has_module('rrhh') or request.tenant.has_module('pos')):
            return Response({'error': 'Module not available'}, status=status.HTTP_403_FORBIDDEN)
        if not getattr(request.user, 'has_permission', lambda x: False)('rrhh.*') and request.user.role not in ('admin', 'superadmin'):
            return Response({'error': 'No tienes permiso para crear puestos'}, status=status.HTTP_403_FORBIDDEN)
        from ...infrastructure.django_models import JobPositionModel
        name = request.data.get('name', '').strip()
        if not name:
            return Response({'error': 'Job position name is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        pos = JobPositionModel.objects.create(
            tenant_id=request.tenant.id,
            name=request.data.get('name'),
            active=request.data.get('active', True)
        )
        return Response({'id': pos.id, 'name': pos.name, 'active': pos.active}, status=status.HTTP_201_CREATED)

class JobPositionDetailView(APIView):
    def put(self, request, position_id):
        if not request.tenant or not (request.tenant.has_module('rrhh') or request.tenant.has_module('pos')):
            return Response({'error': 'Module not available'}, status=status.HTTP_403_FORBIDDEN)
        if not getattr(request.user, 'has_permission', lambda x: False)('rrhh.*') and request.user.role not in ('admin', 'superadmin'):
            return Response({'error': 'No tienes permiso para editar puestos'}, status=status.HTTP_403_FORBIDDEN)
        from ...infrastructure.django_models import JobPositionModel
        pos = JobPositionModel.objects.filter(id=position_id, tenant_id=request.tenant.id).first()
        if not pos:
            return Response({'error': 'Job position not found'}, status=status.HTTP_404_NOT_FOUND)
        
        pos.name = request.data.get('name', pos.name)
        pos.active = request.data.get('active', pos.active)
        pos.save()
        return Response({'message': 'Job position updated'})

    def delete(self, request, position_id):
        if not request.tenant or not (request.tenant.has_module('rrhh') or request.tenant.has_module('pos')):
            return Response({'error': 'Module not available'}, status=status.HTTP_403_FORBIDDEN)
        if not getattr(request.user, 'has_permission', lambda x: False)('rrhh.*') and request.user.role not in ('admin', 'superadmin'):
            return Response({'error': 'No tienes permiso para eliminar puestos'}, status=status.HTTP_403_FORBIDDEN)
        from ...infrastructure.django_models import JobPositionModel
        pos = JobPositionModel.objects.filter(id=position_id, tenant_id=request.tenant.id).first()
        if not pos:
            return Response({'error': 'Job position not found'}, status=status.HTTP_404_NOT_FOUND)
        try:
            pos.delete()
            return Response({'message': 'Job position deleted'})
        except Exception:
            return Response({'error': 'Cannot delete because it is in use'}, status=status.HTTP_400_BAD_REQUEST)


class IESSFlatFileView(APIView):
    def get(self, request):
        if e := verify_module(request): return e
        from django.http import HttpResponse
        from ...application.payroll_exporter import PayrollExporter
        
        period_start = request.query_params.get('period_start')
        period_end = request.query_params.get('period_end')
        format_type = request.query_params.get('format', 'txt').lower()
        
        if not period_start or not period_end:
            return Response({'error': 'Parámetros period_start y period_end requeridos'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            if format_type == 'csv':
                file_data = PayrollExporter.generate_iess_csv(request.tenant.id, period_start, period_end)
            else:
                file_data = PayrollExporter.generate_iess_flat_file(request.tenant.id, period_start, period_end)
                
            response = HttpResponse(file_data['content'], content_type=file_data['mimetype'])
            response['Content-Disposition'] = f'attachment; filename="{file_data["filename"]}"'
            return response
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PayrollPDFView(APIView):
    def get(self, request, payroll_id):
        if e := verify_module(request): return e
        from django.http import HttpResponse
        from ...application.payroll_exporter import PayrollExporter
        
        try:
            buffer = PayrollExporter.generate_payroll_pdf(payroll_id, request.tenant.id)
            response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="rol_pago_{payroll_id}.pdf"'
            return response
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

