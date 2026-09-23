from typing import Optional, List
from ..domain.entities import Employee, Attendance, Payroll, Dependent, SalaryHistory, Loan
from ..domain.repositories import EmployeeRepository, AttendanceRepository, PayrollRepository, DependentRepository, SalaryHistoryRepository, LoanRepository
from .django_models import EmployeeModel, AttendanceModel, PayrollModel, DependentModel, SalaryHistoryModel, LoanModel

class DjangoEmployeeRepository(EmployeeRepository):
    def _to_entity(self, m) -> Employee:
        return Employee(
            id=m.id,
            tenant_id=m.tenant_id,
            name=m.name,
            email=m.email,
            phone=m.phone,
            position=m.position,
            department=m.department,
            hire_date=m.hire_date,
            salary=m.salary,
            contract_type=m.contract_type,
            cash_register_pin=m.pin_caja,
            active=m.active,
            has_iess=m.has_iess,
            accumulates_13th=m.accumulates_13th,
            accumulates_14th=m.accumulates_14th,
            active_dependents_count=self._calculate_active_dependents(m)
        )

    def _calculate_active_dependents(self, m: EmployeeModel) -> int:
        count = 0
        from datetime import date
        today = date.today()
        for dep in m.dependents.filter(active=True):
            if dep.relationship == 'hijo' and not dep.has_disability:
                age = today.year - dep.birth_date.year - ((today.month, today.day) < (dep.birth_date.month, dep.birth_date.day))
                if age < 18:
                    count += 1
            else:
                count += 1
        return count

    def save(self, e: Employee) -> Employee:
        data = {
            'tenant_id': e.tenant_id,
            'name': e.name,
            'email': e.email,
            'phone': e.phone,
            'position': e.position,
            'department': e.department,
            'salary': e.salary,
            'hire_date': e.hire_date,
            'contract_type': e.contract_type,
            'pin_caja': e.cash_register_pin,
            'active': e.active,
            'has_iess': e.has_iess,
            'accumulates_13th': e.accumulates_13th,
            'accumulates_14th': e.accumulates_14th
        }
        if e.id:
            old_employee = EmployeeModel.objects.get(id=e.id)
            if old_employee.salary != e.salary:
                # Automáticamente registrar historial de sueldo
                SalaryHistoryModel.objects.create(
                    tenant_id=e.tenant_id,
                    employee_id=e.id,
                    old_salary=old_employee.salary,
                    new_salary=e.salary
                )
            EmployeeModel.objects.filter(id=e.id).update(**data)
            m = EmployeeModel.objects.get(id=e.id)
        else:
            m = EmployeeModel.objects.create(**data)
            # Registrar historial inicial si lo requiere (opcional)
        return self._to_entity(m)

    def find_by_id(self, id: int, tenant_id: int) -> Optional[Employee]:
        try:
            m = EmployeeModel.objects.get(id=id, tenant_id=tenant_id)
            return self._to_entity(m)
        except EmployeeModel.DoesNotExist:
            return None

    def find_all_active(self, tenant_id: int, position: Optional[str] = None, department: Optional[str] = None) -> List[Employee]:
        query = EmployeeModel.objects.filter(tenant_id=tenant_id, active=True)
        if position:
            query = query.filter(position__iexact=position)
        if department:
            query = query.filter(department__iexact=department)
        
        return [self._to_entity(m) for m in query.all()]

    def list_by_tenant(self, tenant_id: int) -> List[Employee]:
        return [self._to_entity(m) for m in EmployeeModel.objects.filter(tenant_id=tenant_id, active=True)]

    def list_by_department(self, department: str, tenant_id: int) -> List[Employee]:
        return [self._to_entity(m) for m in EmployeeModel.objects.filter(tenant_id=tenant_id, department=department, active=True)]

class DjangoAttendanceRepository(AttendanceRepository):
    def _to_entity(self, m) -> Attendance:
        return Attendance(
            id=m.id,
            tenant_id=m.tenant_id,
            employee_id=m.employee_id,
            employee_name=m.employee_name,
            date=m.date,
            check_in=m.check_in,
            check_out=m.check_out,
            status=m.status
        )

    def save(self, a: Attendance) -> Attendance:
        m = AttendanceModel.objects.create(
            tenant_id=a.tenant_id,
            employee_id=a.employee_id,
            employee_name=a.employee_name,
            date=a.date,
            check_in=a.check_in,
            check_out=a.check_out,
            status=a.status
        )
        return self._to_entity(m)

    def list_by_employee(self, employee_id: int, tenant_id: int) -> List[Attendance]:
        return [self._to_entity(m) for m in AttendanceModel.objects.filter(employee_id=employee_id, tenant_id=tenant_id)]

    def list_by_date(self, date: str, tenant_id: int) -> List[Attendance]:
        return [self._to_entity(m) for m in AttendanceModel.objects.filter(date=date, tenant_id=tenant_id)]

class DjangoPayrollRepository(PayrollRepository):
    def _to_entity(self, m) -> Payroll:
        return Payroll(
            id=m.id,
            tenant_id=m.tenant_id,
            employee_id=m.employee_id,
            employee_name=m.employee_name,
            period_start=m.period_start,
            period_end=m.period_end,
            base_salary=m.base_salary,
            deductions=m.deductions,
            bonuses=m.bonuses,
            iess_personal=m.iess_personal,
            iess_employer=m.iess_employer,
            thirteenth_salary=m.thirteenth_salary,
            fourteenth_salary=m.fourteenth_salary,
            reserve_funds=m.reserve_funds,
            net_salary=m.net_salary,
            status=m.status
        )

    def save(self, n: Payroll) -> Payroll:
        data = {
            'status': n.status,
            'deductions': n.deductions,
            'bonuses': n.bonuses,
            'iess_personal': n.iess_personal,
            'iess_employer': n.iess_employer,
            'thirteenth_salary': n.thirteenth_salary,
            'fourteenth_salary': n.fourteenth_salary,
            'reserve_funds': n.reserve_funds,
            'net_salary': n.net_salary,
        }
        if n.id:
            PayrollModel.objects.filter(id=n.id).update(**data)
            m = PayrollModel.objects.get(id=n.id)
        else:
            m = PayrollModel.objects.create(
                tenant_id=n.tenant_id,
                employee_id=n.employee_id,
                employee_name=n.employee_name,
                period_start=n.period_start,
                period_end=n.period_end,
                base_salary=n.base_salary,
                **data
            )
        return self._to_entity(m)

    def find_by_id(self, id: int, tenant_id: int) -> Optional[Payroll]:
        try:
            m = PayrollModel.objects.get(id=id, tenant_id=tenant_id)
            return self._to_entity(m)
        except PayrollModel.DoesNotExist:
            return None

    def exists(self, tenant_id: int, employee_id: int, period_start: str, period_end: str) -> bool:
        return PayrollModel.objects.filter(
            tenant_id=tenant_id,
            employee_id=employee_id,
            period_start=period_start,
            period_end=period_end
        ).exists()

    def list_by_tenant(self, tenant_id: int) -> List[Payroll]:
        return [self._to_entity(m) for m in PayrollModel.objects.filter(tenant_id=tenant_id)]

    def list_by_employee(self, employee_id: int, tenant_id: int) -> List[Payroll]:
        return [self._to_entity(m) for m in PayrollModel.objects.filter(employee_id=employee_id, tenant_id=tenant_id)]

class DjangoDependentRepository(DependentRepository):
    def _to_entity(self, m: DependentModel) -> Dependent:
        return Dependent(
            id=m.id,
            tenant_id=m.tenant_id,
            employee_id=m.employee_id,
            full_name=m.full_name,
            birth_date=m.birth_date,
            relationship=m.relationship,
            identification=m.identification,
            has_disability=m.has_disability,
            active=m.active
        )

    def save(self, dependent: Dependent) -> Dependent:
        data = {
            'employee_id': dependent.employee_id,
            'full_name': dependent.full_name,
            'birth_date': dependent.birth_date,
            'relationship': dependent.relationship,
            'identification': dependent.identification,
            'has_disability': dependent.has_disability,
            'active': dependent.active
        }
        if dependent.id:
            DependentModel.objects.filter(id=dependent.id, tenant_id=dependent.tenant_id).update(**data)
            m = DependentModel.objects.get(id=dependent.id)
        else:
            m = DependentModel.objects.create(tenant_id=dependent.tenant_id, **data)
        return self._to_entity(m)

    def find_by_id(self, id: int, tenant_id: int) -> Optional[Dependent]:
        try:
            m = DependentModel.objects.get(id=id, tenant_id=tenant_id)
            return self._to_entity(m)
        except DependentModel.DoesNotExist:
            return None

    def list_by_employee(self, employee_id: int, tenant_id: int) -> List[Dependent]:
        return [self._to_entity(m) for m in DependentModel.objects.filter(employee_id=employee_id, tenant_id=tenant_id)]

    def delete(self, id: int, tenant_id: int) -> None:
        DependentModel.objects.filter(id=id, tenant_id=tenant_id).delete()

class DjangoSalaryHistoryRepository(SalaryHistoryRepository):
    def _to_entity(self, m: SalaryHistoryModel) -> SalaryHistory:
        return SalaryHistory(
            id=m.id,
            tenant_id=m.tenant_id,
            employee_id=m.employee_id,
            old_salary=m.old_salary,
            new_salary=m.new_salary,
            change_date=m.change_date.date(),
            reason=m.reason
        )
        
    def list_by_employee(self, employee_id: int, tenant_id: int) -> List[SalaryHistory]:
        return [self._to_entity(m) for m in SalaryHistoryModel.objects.filter(employee_id=employee_id, tenant_id=tenant_id).order_by('-change_date')]
        
    def save(self, history: SalaryHistory) -> SalaryHistory:
        m = SalaryHistoryModel.objects.create(
            tenant_id=history.tenant_id,
            employee_id=history.employee_id,
            old_salary=history.old_salary,
            new_salary=history.new_salary,
            reason=history.reason
        )
        return self._to_entity(m)

class DjangoLoanRepository(LoanRepository):
    def _to_entity(self, m: LoanModel) -> Loan:
        return Loan(
            id=m.id,
            tenant_id=m.tenant_id,
            employee_id=m.employee_id,
            type=m.type,
            total_amount=m.total_amount,
            monthly_installment=m.monthly_installment,
            start_date=m.start_date,
            active=m.active
        )
        
    def list_by_employee(self, employee_id: int, tenant_id: int) -> List[Loan]:
        return [self._to_entity(m) for m in LoanModel.objects.filter(employee_id=employee_id, tenant_id=tenant_id).order_by('-start_date')]
        
    def save(self, loan: Loan) -> Loan:
        data = {
            'employee_id': loan.employee_id,
            'type': loan.type,
            'total_amount': loan.total_amount,
            'monthly_installment': loan.monthly_installment,
            'start_date': loan.start_date,
            'active': loan.active
        }
        if loan.id:
            LoanModel.objects.filter(id=loan.id, tenant_id=loan.tenant_id).update(**data)
            m = LoanModel.objects.get(id=loan.id)
        else:
            m = LoanModel.objects.create(tenant_id=loan.tenant_id, **data)
        return self._to_entity(m)
        
    def find_by_id(self, id: int, tenant_id: int) -> Optional[Loan]:
        try:
            m = LoanModel.objects.get(id=id, tenant_id=tenant_id)
            return self._to_entity(m)
        except LoanModel.DoesNotExist:
            return None
            
    def delete(self, id: int, tenant_id: int) -> None:
        LoanModel.objects.filter(id=id, tenant_id=tenant_id).delete()
