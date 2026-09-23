from decimal import Decimal
from datetime import date
from ..domain.entities import Employee, Attendance, Payroll
from ..domain.repositories import EmployeeRepository, AttendanceRepository, PayrollRepository


class CreateEmployee:
    def __init__(self, repo: EmployeeRepository):
        self.repo = repo

    def execute(self, tenant_id: int, data: dict) -> Employee:
        employee = Employee(
            id=0,
            tenant_id=tenant_id,
            name=data.get('name', ''),
            email=data.get('email', ''),
            phone=data.get('phone', ''),
            position=data.get('position', ''),
            department=data.get('department', 'General'),
            hire_date=date.fromisoformat(data.get('hire_date', str(date.today()))),
            salary=Decimal(str(data.get('salary', '0'))),
            contract_type=data.get('contract_type', 'full_time'),
            cash_register_pin=data.get('cash_register_pin', data.get('pin_caja', '')),
        )
        return self.repo.save(employee)


