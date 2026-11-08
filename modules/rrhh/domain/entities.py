from dataclasses import dataclass, field
from decimal import Decimal
from datetime import date
from typing import List, Optional

@dataclass
class Employee:
    id: int
    tenant_id: int
    name: str
    email: str
    phone: str
    position: str
    department: str
    hire_date: date
    salary: Decimal
    contract_type: str  # full_time, part_time, freelance
    identification: str = ''
    bank_name: str = ''
    bank_account_type: str = 'ahorros'
    bank_account_number: str = ''
    cash_register_pin: str = ''
    active: bool = True
    has_iess: bool = False
    accumulates_13th: bool = True
    accumulates_14th: bool = True
    active_dependents_count: int = 0

    @property
    def tenure_days(self) -> int:
        return (date.today() - self.hire_date).days

    @property
    def tenure_years(self) -> float:
        return round(self.tenure_days / 365, 1)

@dataclass
class Dependent:
    id: int
    tenant_id: int
    employee_id: int
    full_name: str
    birth_date: date
    relationship: str
    identification: str = ''
    has_disability: bool = False
    active: bool = True

    @property
    def age(self) -> int:
        today = date.today()
        return today.year - self.birth_date.year - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))

    @property
    def is_valid_carga(self) -> bool:
        # En Ecuador, cargas son hijos menores de 18 años, o cónyuge, o hijos con discapacidad sin límite de edad
        if self.relationship == 'hijo' and not self.has_disability and self.age >= 18:
            return False
        return self.active

@dataclass
class SalaryHistory:
    id: int
    tenant_id: int
    employee_id: int
    old_salary: Decimal
    new_salary: Decimal
    change_date: date
    reason: str

@dataclass
class Loan:
    id: int
    tenant_id: int
    employee_id: int
    type: str
    total_amount: Decimal
    monthly_installment: Decimal
    start_date: date
    active: bool

@dataclass
class Attendance:
    id: int
    tenant_id: int
    employee_id: int
    employee_name: str
    date: date
    check_in: str
    check_out: str
    status: str  # present, absent, late, permission

@dataclass
class Payroll:
    id: int
    tenant_id: int
    employee_id: int
    employee_name: str
    period_start: date
    period_end: date
    base_salary: Decimal
    deductions: Decimal
    bonuses: Decimal
    iess_personal: Decimal = Decimal('0')
    iess_employer: Decimal = Decimal('0')
    thirteenth_salary: Decimal = Decimal('0')
    fourteenth_salary: Decimal = Decimal('0')
    reserve_funds: Decimal = Decimal('0')
    net_salary: Decimal = Decimal('0')
    status: str = 'draft'  # draft, approved, paid
    employee_identification: str = ''

    @property
    def total_net(self) -> Decimal:
        return self.base_salary + self.bonuses - self.deductions - self.iess_personal

    def calculate_ecuador(self, tenure_days: int, sbu: Decimal = Decimal('460.00'),
                          monthly_thirteenth: bool = True,
                          monthly_fourteenth: bool = True,
                          monthly_reserve_funds: bool = True):
        # Ingreso Gravado (base para el IESS) = base_salary + bonuses
        taxable_income = self.base_salary + self.bonuses
        
        # Aporte Personal IESS (9.45%)
        self.iess_personal = (taxable_income * Decimal('0.0945')).quantize(Decimal('0.01'))
        
        # Aporte Patronal IESS (12.15%)
        self.iess_employer = (taxable_income * Decimal('0.1215')).quantize(Decimal('0.01'))
        
        # Cálculo de décimos y fondos de reserva
        d3_val = (taxable_income / Decimal('12')).quantize(Decimal('0.01'))
        d4_val = (sbu / Decimal('12')).quantize(Decimal('0.01'))
        fr_val = (taxable_income * Decimal('0.0833')).quantize(Decimal('0.01')) if tenure_days >= 365 else Decimal('0.00')

        # Asignar a la nómina (solo si está activo el pago mensualizado en el rol)
        self.thirteenth_salary = d3_val if monthly_thirteenth else Decimal('0.00')
        self.fourteenth_salary = d4_val if monthly_fourteenth else Decimal('0.00')
        self.reserve_funds = fr_val if monthly_reserve_funds else Decimal('0.00')
            
        # Neto a recibir (salario base + bonos + décimos mensualizados - deducciones - iess_personal)
        self.net_salary = (taxable_income + self.thirteenth_salary + self.fourteenth_salary + self.reserve_funds - self.deductions - self.iess_personal).quantize(Decimal('0.01'))

    def approve(self):
        if self.status != 'draft':
            raise ValueError("Only a draft payroll can be approved")
        self.status = 'approved'

    def mark_paid(self):
        if self.status != 'approved':
            raise ValueError("Only an approved payroll can be paid")
        self.status = 'paid'
