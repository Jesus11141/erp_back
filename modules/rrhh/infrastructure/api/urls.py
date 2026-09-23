from django.urls import path
from .views import (
    EmployeesView, EmployeeDetailView,
    DependentsView, DependentDetailView,
    SalaryHistoryView, LoansView, LoanDetailView,
    AttendancesView, PayrollsView, PayrollActionView, MassPayrollsView,
    JobPositionView, JobPositionDetailView
)

urlpatterns = [
    path('employees/', EmployeesView.as_view(), name='employees'),
    path('employees/<int:employee_id>/', EmployeeDetailView.as_view(), name='employee_detail'),
    path('employees/<int:employee_id>/dependents/', DependentsView.as_view(), name='dependents'),
    path('employees/<int:employee_id>/dependents/<int:dep_id>/', DependentDetailView.as_view(), name='dependent_detail'),
    path('employees/<int:employee_id>/salary-history/', SalaryHistoryView.as_view(), name='salary_history'),
    path('employees/<int:employee_id>/loans/', LoansView.as_view(), name='loans'),
    path('employees/<int:employee_id>/loans/<int:loan_id>/', LoanDetailView.as_view(), name='loan_detail'),
    path('positions/', JobPositionView.as_view(), name='positions'),
    path('positions/<int:position_id>/', JobPositionDetailView.as_view(), name='position_detail'),
    path('attendances/', AttendancesView.as_view()),
    path('payrolls/', PayrollsView.as_view()),
    path('payrolls/generate-mass/', MassPayrollsView.as_view()),
    path('payrolls/<int:payroll_id>/<str:action>/', PayrollActionView.as_view()),
]
