from decimal import Decimal
from datetime import date
from ..domain.entities import Employee, Attendance, Payroll
from ..domain.repositories import EmployeeRepository, AttendanceRepository, PayrollRepository


class GeneratePayroll:
    def __init__(self, employee_repo: EmployeeRepository, payroll_repo: PayrollRepository, param_repo=None):
        self.employee_repo = employee_repo
        self.payroll_repo = payroll_repo
        self.param_repo = param_repo

    def execute(self, tenant_id: int, employee_id: int, data: dict) -> Payroll:
        employee = self.employee_repo.find_by_id(employee_id, tenant_id)
        if not employee:
            raise ValueError("Employee not found")

        sbu = Decimal('460.00')
        m_d3 = True
        m_d4 = True
        m_fr = True
        if self.param_repo:
            param_sbu = self.param_repo.get(tenant_id, 'rrhh', 'sbu_ecuador')
            if param_sbu:
                try: sbu = Decimal(param_sbu.value)
                except (ValueError, TypeError): pass

            p_d3 = self.param_repo.get(tenant_id, 'rrhh', 'monthly_thirteenth_salary')
            if p_d3: m_d3 = p_d3.value.lower() == 'true'
            p_d4 = self.param_repo.get(tenant_id, 'rrhh', 'monthly_fourteenth_salary')
            if p_d4: m_d4 = p_d4.value.lower() == 'true'
            p_fr = self.param_repo.get(tenant_id, 'rrhh', 'monthly_reserve_funds')
            if p_fr: m_fr = p_fr.value.lower() == 'true'

        payroll = Payroll(
            id=0,
            tenant_id=tenant_id,
            employee_id=employee_id,
            employee_name=employee.name,
            period_start=date.fromisoformat(data.get('period_start')),
            period_end=date.fromisoformat(data.get('period_end')),
            base_salary=employee.salary,
            deductions=Decimal(str(data.get('deductions', 0))),
            bonuses=Decimal(str(data.get('bonuses', 0))),
            status='draft',
        )

        tenure_days = (payroll.period_end - employee.hire_date).days
        
        payroll.calculate_ecuador(
            tenure_days=tenure_days,
            sbu=sbu,
            monthly_thirteenth=m_d3,
            monthly_fourteenth=m_d4,
            monthly_reserve_funds=m_fr
        )

        return self.payroll_repo.save(payroll)


