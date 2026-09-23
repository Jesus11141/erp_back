from decimal import Decimal
from datetime import date
from typing import Protocol
from django.db import transaction
from ..domain.entities import Employee, Attendance, Payroll
from ..domain.repositories import EmployeeRepository, AttendanceRepository, PayrollRepository


class PayrollAccountingService(Protocol):
    """Interface (Puerto) para desacoplar Recursos Humanos de Contabilidad"""
    def register_payroll_entry(self, tenant_id: int, payroll: Payroll) -> None:
        pass


class ApprovePayroll:
    def __init__(self, repo: PayrollRepository, accounting_service: PayrollAccountingService = None):
        self.repo = repo
        self.accounting_service = accounting_service

    def execute(self, payroll_id: int, tenant_id: int) -> Payroll:
        with transaction.atomic():
            payroll = self.repo.find_by_id(payroll_id, tenant_id)
            if not payroll:
                raise ValueError("Payroll not found")
            
            payroll.approve()
            saved = self.repo.save(payroll)

            # Se delega a la abstracción (Inversión de dependencias)
            if self.accounting_service:
                self.accounting_service.register_payroll_entry(tenant_id, saved)

            return saved
