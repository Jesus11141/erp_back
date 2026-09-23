from django.db import models


class PatientModel(models.Model):
    SEXOS = [('M', 'Masculino'), ('F', 'Femenino')]
    tenant_id       = models.IntegerField()
    id_number          = models.CharField(max_length=20)
    name          = models.CharField(max_length=150)
    birth_date = models.DateField()
    gender            = models.CharField(max_length=1, choices=SEXOS, default='M')
    blood_type     = models.CharField(max_length=5, blank=True)
    phone        = models.CharField(max_length=20, blank=True)
    email           = models.EmailField(blank=True)
    address       = models.TextField(blank=True)
    allergies        = models.TextField(blank=True)
    background    = models.TextField(blank=True)
    is_active          = models.BooleanField(default=True)

    class Meta:
        app_label = 'clinica'
        db_table = 'clinica_pacientes'
        unique_together = ('id_number', 'tenant_id')


class DoctorModel(models.Model):
    tenant_id           = models.IntegerField()
    id_number              = models.CharField(max_length=20, blank=True)
    name              = models.CharField(max_length=150)
    specialty        = models.CharField(max_length=100, blank=True)
    senescyt_record   = models.CharField(max_length=50, blank=True)
    phone            = models.CharField(max_length=20, blank=True)
    email               = models.EmailField(blank=True)
    consultation_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=70)
    is_active              = models.BooleanField(default=True)

    class Meta:
        app_label = 'clinica'
        db_table = 'clinica_medicos'


class AppointmentModel(models.Model):
    ESTADOS = [('scheduled','Programada'),('confirmed','Confirmada'),
               ('attended','Atendida'),('canceled','Cancelada'),('no_show','No asistiÃ³')]
    tenant_id       = models.IntegerField()
    patient        = models.ForeignKey(PatientModel, on_delete=models.PROTECT)
    paciente_nombre = models.CharField(max_length=150)
    doctor          = models.ForeignKey(DoctorModel, on_delete=models.PROTECT)
    medico_nombre   = models.CharField(max_length=150)
    date           = models.DateField(null=True, blank=True)
    hora            = models.TimeField()
    reason          = models.TextField(blank=True)
    status          = models.CharField(max_length=20, choices=ESTADOS, default='scheduled')
    notes           = models.TextField(blank=True)

    class Meta:
        app_label = 'clinica'
        db_table = 'clinica_citas'
        ordering = ['date', 'hora']


class ConsultationModel(models.Model):
    tenant_id               = models.IntegerField()
    patient                = models.ForeignKey(PatientModel, on_delete=models.PROTECT)
    paciente_nombre         = models.CharField(max_length=150)
    doctor                  = models.ForeignKey(DoctorModel, on_delete=models.PROTECT)
    medico_nombre           = models.CharField(max_length=150)
    appointment                    = models.ForeignKey(AppointmentModel, on_delete=models.SET_NULL, null=True, blank=True)
    date                   = models.DateTimeField(auto_now_add=True)
    consultation_reason         = models.TextField(blank=True)
    current_illness       = models.TextField(blank=True)
    physical_exam           = models.TextField(blank=True)
    icd_diagnosis         = models.CharField(max_length=20, blank=True)
    diagnosis_description = models.TextField(blank=True)
    treatment             = models.TextField(blank=True)
    observations           = models.TextField(blank=True)
    status                  = models.CharField(max_length=20, default='open')

    class Meta:
        app_label = 'clinica'
        db_table = 'clinica_consultas'
        ordering = ['-date']


class ItemRecetaModel(models.Model):
    consultation    = models.ForeignKey(ConsultationModel, on_delete=models.CASCADE, related_name='prescription', null=True, blank=True)
    medication = models.CharField(max_length=150, default='')
    dose       = models.CharField(max_length=100, default='')
    frequency  = models.CharField(max_length=100, default='')
    duration    = models.CharField(max_length=100, default='')
    indications = models.TextField(blank=True, default='')

    class Meta:
        app_label = 'clinica'
        db_table = 'clinica_receta_items'


class LabExamModel(models.Model):
    ESTADOS = [('solicitado','Solicitado'),('en_proceso','En proceso'),('completado','Completado')]
    tenant_id       = models.IntegerField()
    patient        = models.ForeignKey(PatientModel, on_delete=models.PROTECT)
    paciente_nombre = models.CharField(max_length=150)
    doctor          = models.ForeignKey(DoctorModel, on_delete=models.PROTECT)
    medico_nombre   = models.CharField(max_length=150)
    consultation        = models.ForeignKey(ConsultationModel, on_delete=models.SET_NULL, null=True, blank=True)
    tipo_examen     = models.CharField(max_length=50)
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    result_date = models.DateTimeField(null=True, blank=True)
    status          = models.CharField(max_length=20, choices=ESTADOS, default='solicitado')
    observations   = models.TextField(blank=True)

    class Meta:
        app_label = 'clinica'
        db_table = 'clinica_examenes'
        ordering = ['-fecha_solicitud']


class ResultadoAnalitoModel(models.Model):
    examen      = models.ForeignKey(LabExamModel, on_delete=models.CASCADE, related_name='results')
    analito     = models.CharField(max_length=100)
    valor       = models.DecimalField(max_digits=12, decimal_places=4)
    unidad      = models.CharField(max_length=30, blank=True)
    rango_min   = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    rango_max   = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    status      = models.CharField(max_length=20, default='normal')
    color       = models.CharField(max_length=10)
    icono       = models.CharField(max_length=5)

    class Meta:
        app_label = 'clinica'
        db_table = 'clinica_resultados'


