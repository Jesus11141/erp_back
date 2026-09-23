from decimal import Decimal
from datetime import date
from ..domain.entities import Employee, Attendance, Payroll
from ..domain.repositories import EmployeeRepository, AttendanceRepository, PayrollRepository


class GenerateMassPayroll:
    def __init__(self, employee_repo: EmployeeRepository, payroll_repo: PayrollRepository, param_repo=None):
        self.employee_repo = employee_repo
        self.payroll_repo = payroll_repo
        self.param_repo = param_repo
        self.generate_individual = GeneratePayroll(employee_repo, payroll_repo, param_repo)

    def execute(self, tenant_id: int, data: dict) -> int:
        period_start = data.get('period_start')
        period_end = data.get('period_end')
        position_filter = data.get('position')
        dept_filter = data.get('department')

        employees = self.employee_repo.find_all_active(
            tenant_id=tenant_id, 
            position=position_filter, 
            department=dept_filter
        )
        
        counter = 0

        for emp in employees:
            exists = self.payroll_repo.exists(
                tenant_id=tenant_id,
                employee_id=emp.id,
                period_start=period_start,
                period_end=period_end
            )
            
            if not exists:
                self.generate_individual.execute(
                    tenant_id=tenant_id,
                    employee_id=emp.id,
                    data={
                        'period_start': period_start,
                        'period_end': period_end,
                        'bonuses': Decimal('0.00'),
                        'deductions': Decimal('0.00')
                    }
                )
                counter += 1

        return counter

