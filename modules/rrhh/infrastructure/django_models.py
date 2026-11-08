from django.db import models

class JobPositionModel(models.Model):
    tenant_id = models.IntegerField()
    name = models.CharField(max_length=150, db_column='nombre')
    active = models.BooleanField(default=True, db_column='activo')

    class Meta:
        app_label = 'rrhh'
        db_table = 'puestos'

class EmployeeModel(models.Model):
    CONTRACT_CHOICES = [('tiempo_completo','Tiempo Completo'),('medio_tiempo','Medio Tiempo'),('honorarios','Honorarios')]
    tenant_id = models.IntegerField()
    name = models.CharField(max_length=150, db_column='nombre')
    identification = models.CharField(max_length=20, blank=True, default='', db_column='cedula')
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True, db_column='telefono')
    position = models.CharField(max_length=100, db_column='puesto')
    department = models.CharField(max_length=100, default='General', db_column='departamento')
    hire_date = models.DateField(db_column='fecha_ingreso')
    salary = models.DecimalField(max_digits=12, decimal_places=2, db_column='salario')
    contract_type = models.CharField(max_length=20, choices=CONTRACT_CHOICES, default='tiempo_completo', db_column='tipo_contrato')
    pin_caja = models.CharField(max_length=50, blank=True, default='', db_column='pin_caja')
    active = models.BooleanField(default=True, db_column='activo')
    
    # Datos Bancarios para Acreditación de Nómina
    bank_name = models.CharField(max_length=100, blank=True, default='', db_column='banco')
    bank_account_type = models.CharField(max_length=20, blank=True, default='ahorros', db_column='tipo_cuenta_banco')
    bank_account_number = models.CharField(max_length=50, blank=True, default='', db_column='numero_cuenta_banco')
    
    # Configuraciones de Nómina (Ecuador)
    has_iess = models.BooleanField(default=False, db_column='tiene_iess')
    accumulates_13th = models.BooleanField(default=True, db_column='acumula_decimo_tercero')
    accumulates_14th = models.BooleanField(default=True, db_column='acumula_decimo_cuarto')

    # Enlace débil con UserModel de auth para seguridad
    user_id = models.IntegerField(null=True, blank=True, help_text="ID del usuario del sistema")

    class Meta:
        app_label = 'rrhh'
        db_table = 'empleados'

class DependentModel(models.Model):
    RELATION_CHOICES = [('hijo','Hijo/a'),('conyuge','Cónyuge'),('padre','Padre/Madre'),('otro','Otro')]
    tenant_id = models.IntegerField()
    employee = models.ForeignKey(EmployeeModel, on_delete=models.CASCADE, related_name='dependents', db_column='empleado_id')
    full_name = models.CharField(max_length=150, db_column='nombres_completos')
    identification = models.CharField(max_length=20, blank=True, db_column='cedula')
    birth_date = models.DateField(db_column='fecha_nacimiento')
    relationship = models.CharField(max_length=20, choices=RELATION_CHOICES, db_column='parentesco')
    has_disability = models.BooleanField(default=False, db_column='tiene_discapacidad')
    active = models.BooleanField(default=True, db_column='activo')

    class Meta:
        app_label = 'rrhh'
        db_table = 'cargas_familiares'

class SalaryHistoryModel(models.Model):
    tenant_id = models.IntegerField()
    employee = models.ForeignKey(EmployeeModel, on_delete=models.CASCADE, related_name='salary_history')
    old_salary = models.DecimalField(max_digits=10, decimal_places=2)
    new_salary = models.DecimalField(max_digits=10, decimal_places=2)
    change_date = models.DateTimeField(auto_now_add=True)
    reason = models.CharField(max_length=255, default="Actualización de contrato")

    class Meta:
        app_label = 'rrhh'
        db_table = 'historial_sueldos'

class LoanModel(models.Model):
    LOAN_TYPES = [('biess', 'Préstamo BIESS'), ('interno', 'Préstamo Interno (Anticipo)')]
    tenant_id = models.IntegerField()
    employee = models.ForeignKey(EmployeeModel, on_delete=models.CASCADE, related_name='loans')
    type = models.CharField(max_length=20, choices=LOAN_TYPES)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    monthly_installment = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateField()
    active = models.BooleanField(default=True)

    class Meta:
        app_label = 'rrhh'
        db_table = 'prestamos_empleados'

class AttendanceModel(models.Model):
    STATUS_CHOICES = [('presente','Presente'),('ausente','Ausente'),('tardanza','Tardanza'),('permiso','Permiso')]
    tenant_id = models.IntegerField()
    employee = models.ForeignKey(EmployeeModel, on_delete=models.PROTECT, db_column='empleado_id')
    employee_name = models.CharField(max_length=150, db_column='empleado_nombre')
    date = models.DateField(db_column='fecha')
    check_in = models.CharField(max_length=10, blank=True, db_column='hora_entrada')
    check_out = models.CharField(max_length=10, blank=True, db_column='hora_salida')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='presente', db_column='estado')

    class Meta:
        app_label = 'rrhh'
        db_table = 'asistencias'
        ordering = ['-date']

class PayrollModel(models.Model):
    STATUS_CHOICES = [('draft','Borrador'),('aprobada','Aprobada'),('pagada','Pagada')]
    tenant_id = models.IntegerField()
    employee = models.ForeignKey(EmployeeModel, on_delete=models.PROTECT, db_column='empleado_id')
    employee_name = models.CharField(max_length=150, db_column='empleado_nombre')
    period_start = models.DateField(db_column='periodo_inicio')
    period_end = models.DateField(db_column='periodo_fin')
    base_salary = models.DecimalField(max_digits=12, decimal_places=2, db_column='salario_base')
    deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_column='deducciones')
    bonuses = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_column='bonos')
    
    # Campos NÃ³mina Ecuador (IESS y Provisiones)
    iess_personal = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_column='iess_personal')
    iess_patronal = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_column='iess_patronal')
    thirteenth_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_column='decimo_tercero')
    fourteenth_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_column='decimo_cuarto')
    reserve_funds = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_column='fondos_reserva')
    net_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_column='neto_recibir')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', db_column='estado')

    class Meta:
        app_label = 'rrhh'
        db_table = 'nominas'
        ordering = ['-period_start']

