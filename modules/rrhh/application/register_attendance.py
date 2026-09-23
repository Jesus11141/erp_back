from decimal import Decimal
from datetime import date
from ..domain.entities import Employee, Attendance, Payroll
from ..domain.repositories import EmployeeRepository, AttendanceRepository, PayrollRepository


class RegisterAttendance:
    def __init__(self, employee_repo: EmployeeRepository, attendance_repo: AttendanceRepository):
        self.employee_repo = employee_repo
        self.attendance_repo = attendance_repo

    def execute(self, tenant_id: int, employee_id: int, data: dict) -> Attendance:
        employee = self.employee_repo.find_by_id(employee_id, tenant_id)
        if not employee:
            raise ValueError("Employee not found")
        attendance = Attendance(
            id=0,
            tenant_id=tenant_id,
            employee_id=employee_id,
            employee_name=employee.name,
            date=date.fromisoformat(data.get('date', str(date.today()))),
            check_in=data.get('check_in', ''),
            check_out=data.get('check_out', ''),
            status=data.get('status', 'present'),
        )
        return self.attendance_repo.save(attendance)


