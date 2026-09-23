from abc import ABC, abstractmethod
from typing import Optional, List
from .entities import Employee, Attendance, Payroll, Dependent, Loan, SalaryHistory

class EmployeeRepository(ABC):
    @abstractmethod
    def save(self, employee: Employee) -> Employee:
        pass

    @abstractmethod
    def find_all_active(self, tenant_id: int, position: Optional[str] = None, department: Optional[str] = None) -> List[Employee]:
        pass
    
    @abstractmethod
    def find_by_id(self, id: int, tenant_id: int) -> Optional[Employee]: pass
    
    @abstractmethod
    def list_by_tenant(self, tenant_id: int) -> List[Employee]: pass
    
    @abstractmethod
    def list_by_department(self, department: str, tenant_id: int) -> List[Employee]: pass

class AttendanceRepository(ABC):
    @abstractmethod
    def save(self, attendance: Attendance) -> Attendance: pass
    
    @abstractmethod
    def list_by_employee(self, employee_id: int, tenant_id: int) -> List[Attendance]: pass
    
    @abstractmethod
    def list_by_date(self, date: str, tenant_id: int) -> List[Attendance]: pass

class PayrollRepository(ABC):
    @abstractmethod
    def save(self, payroll: Payroll) -> Payroll:
        pass

    @abstractmethod
    def exists(self, tenant_id: int, employee_id: int, period_start: str, period_end: str) -> bool:
        pass
    
    @abstractmethod
    def find_by_id(self, id: int, tenant_id: int) -> Optional[Payroll]: pass
    
    @abstractmethod
    def list_by_tenant(self, tenant_id: int) -> List[Payroll]: pass
    
    @abstractmethod
    def list_by_employee(self, employee_id: int, tenant_id: int) -> List[Payroll]: pass

class DependentRepository(ABC):
    @abstractmethod
    def save(self, dependent: Dependent) -> Dependent: pass
    
    @abstractmethod
    def find_by_id(self, id: int, tenant_id: int) -> Optional[Dependent]: pass
    
    @abstractmethod
    def list_by_employee(self, employee_id: int, tenant_id: int) -> List[Dependent]: pass
    
    @abstractmethod
    def delete(self, id: int, tenant_id: int) -> None: pass

class SalaryHistoryRepository(ABC):
    @abstractmethod
    def list_by_employee(self, employee_id: int, tenant_id: int) -> List[SalaryHistory]: pass
    
    @abstractmethod
    def save(self, history: SalaryHistory) -> SalaryHistory: pass

class LoanRepository(ABC):
    @abstractmethod
    def list_by_employee(self, employee_id: int, tenant_id: int) -> List[Loan]: pass
    
    @abstractmethod
    def save(self, loan: Loan) -> Loan: pass
    
    @abstractmethod
    def find_by_id(self, id: int, tenant_id: int) -> Optional[Loan]: pass
    
    @abstractmethod
    def delete(self, id: int, tenant_id: int) -> None: pass
