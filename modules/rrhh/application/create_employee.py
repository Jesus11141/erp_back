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
            identification=data.get('identification', data.get('cedula', '')),
            email=data.get('email', ''),
            phone=data.get('phone', ''),
            position=data.get('position', ''),
            department=data.get('department', 'General'),
            hire_date=date.fromisoformat(data.get('hire_date', str(date.today()))),
            salary=Decimal(str(data.get('salary', '0'))),
            contract_type=data.get('contract_type', 'full_time'),
            bank_name=data.get('bank_name', data.get('banco', '')),
            bank_account_type=data.get('bank_account_type', data.get('tipo_cuenta_banco', 'ahorros')),
            bank_account_number=data.get('bank_account_number', data.get('numero_cuenta_banco', '')),
            cash_register_pin=data.get('cash_register_pin', data.get('pin_caja', '')),
            has_iess=bool(data.get('has_iess', False)),
            accumulates_13th=bool(data.get('accumulates_13th', True)),
            accumulates_14th=bool(data.get('accumulates_14th', True)),
        )
        return self.repo.save(employee)


