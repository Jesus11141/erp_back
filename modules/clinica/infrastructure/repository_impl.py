from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from ..domain.entities import Patient, Doctor, Appointment, Consultation, LabExam, AnalyteResult, PrescriptionItem
from .django_models import PatientModel, DoctorModel, AppointmentModel, ConsultationModel, ItemRecetaModel, LabExamModel, ResultadoAnalitoModel


class DjangoClinicaRepository:

    # â”€â”€ Pacientes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _patient(self, m: PatientModel) -> Patient:
        return Patient(
            id=m.id, tenant_id=m.tenant_id, id_number=m.id_number, name=m.name,
            birth_date=m.birth_date, gender=m.gender, blood_type=m.blood_type,
            phone=m.phone, email=m.email, address=m.address,
            allergies=m.allergies, background=m.background, is_active=m.is_active,
        )

    def list_patients(self, tenant_id: int, q: str = '') -> List[Patient]:
        qs = PatientModel.objects.filter(tenant_id=tenant_id, is_active=True)
        if q:
            qs = qs.filter(nombre__icontains=q) | PatientModel.objects.filter(tenant_id=tenant_id, cedula__icontains=q)
        return [self._patient(m) for m in qs]

    def find_patient(self, paciente_id: int, tenant_id: int) -> Optional[Patient]:
        try:
            return self._patient(PatientModel.objects.get(id=paciente_id, tenant_id=tenant_id))
        except PatientModel.DoesNotExist:
            return None

    def find_by_cedula(self, id_number: str, tenant_id: int) -> Optional[Patient]:
        try:
            return self._patient(PatientModel.objects.get(id_number=id_number, tenant_id=tenant_id))
        except PatientModel.DoesNotExist:
            return None

    def save_patient(self, p: Patient) -> Patient:
        if p.id:
            PatientModel.objects.filter(id=p.id).update(
                name=p.name, phone=p.phone, email=p.email,
                address=p.address, allergies=p.allergies, background=p.background,
                blood_type=p.blood_type,
            )
            m = PatientModel.objects.get(id=p.id)
        else:
            m = PatientModel.objects.create(
                tenant_id=p.tenant_id, id_number=p.id_number, name=p.name,
                birth_date=p.birth_date, gender=p.gender, blood_type=p.blood_type,
                phone=p.phone, email=p.email, address=p.address,
                allergies=p.allergies, background=p.background,
            )
        return self._patient(m)

    def patient_history(self, paciente_id: int, tenant_id: int) -> dict:
        consultas = ConsultationModel.objects.filter(paciente_id=paciente_id, tenant_id=tenant_id)
        examenes = LabExamModel.objects.filter(paciente_id=paciente_id, tenant_id=tenant_id)
        return {
            'consultas': [{'id': c.id, 'date': str(c.date), 'medico_nombre': c.medico_nombre,
                           'icd_diagnosis': c.icd_diagnosis, 'diagnosis_description': c.diagnosis_description,
                           'consultation_reason': c.consultation_reason} for c in consultas],
            'examenes': [{'id': e.id, 'tipo_examen': e.tipo_examen, 'result_date': str(e.result_date) if e.result_date else None,
                          'tiene_criticos': e.results.filter(estado__startswith='CRITICO').exists(),
                          'tiene_alterados': e.results.exclude(status='NORMAL').exists()} for e in examenes],
        }

    # â”€â”€ MÃ©dicos â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _doctor(self, m: DoctorModel) -> Doctor:
        return Doctor(
            id=m.id, tenant_id=m.tenant_id, id_number=m.id_number, name=m.name,
            specialty=m.specialty, senescyt_record=m.senescyt_record,
            phone=m.phone, email=m.email, is_active=m.is_active,
            consultation_percentage=m.consultation_percentage,
        )

    def list_doctors(self, tenant_id: int) -> List[Doctor]:
        return [self._doctor(m) for m in DoctorModel.objects.filter(tenant_id=tenant_id, is_active=True)]

    def find_doctor(self, medico_id: int, tenant_id: int) -> Optional[Doctor]:
        try:
            return self._doctor(DoctorModel.objects.get(id=medico_id, tenant_id=tenant_id))
        except DoctorModel.DoesNotExist:
            return None

    def save_doctor(self, m: Doctor) -> Doctor:
        model = DoctorModel.objects.create(
            tenant_id=m.tenant_id, id_number=m.id_number, name=m.name,
            specialty=m.specialty, senescyt_record=m.senescyt_record,
            phone=m.phone, email=m.email, consultation_percentage=m.consultation_percentage,
        )
        return self._doctor(model)

    # â”€â”€ Citas â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _appointment(self, m: AppointmentModel) -> Appointment:
        return Appointment(
            id=m.id, tenant_id=m.tenant_id, paciente_id=m.paciente_id,
            paciente_nombre=m.paciente_nombre, medico_id=m.medico_id,
            medico_nombre=m.medico_nombre, date=m.date, hora=m.hora,
            reason=m.reason, status=m.status, notes=m.notes,
        )

    def list_appointments(self, tenant_id: int, date=None, medico_id=None) -> List[Appointment]:
        qs = AppointmentModel.objects.filter(tenant_id=tenant_id)
        if date:
            qs = qs.filter(date=date)
        if medico_id:
            qs = qs.filter(medico_id=medico_id)
        return [self._appointment(m) for m in qs]

    def find_appointment(self, cita_id: int, tenant_id: int) -> Optional[Appointment]:
        try:
            return self._appointment(AppointmentModel.objects.get(id=cita_id, tenant_id=tenant_id))
        except AppointmentModel.DoesNotExist:
            return None

    def save_appointment(self, c: Appointment) -> Appointment:
        if c.id:
            AppointmentModel.objects.filter(id=c.id).update(status=c.status, notes=c.notes)
            m = AppointmentModel.objects.get(id=c.id)
        else:
            m = AppointmentModel.objects.create(
                tenant_id=c.tenant_id, paciente_id=c.paciente_id,
                paciente_nombre=c.paciente_nombre, medico_id=c.medico_id,
                medico_nombre=c.medico_nombre, date=c.date, hora=c.hora,
                reason=c.reason, status=c.status,
            )
        return self._appointment(m)

    # â”€â”€ Consultas â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def save_consultation(self, c: Consultation) -> Consultation:
        m = ConsultationModel.objects.create(
            tenant_id=c.tenant_id, paciente_id=c.paciente_id,
            paciente_nombre=c.paciente_nombre, medico_id=c.medico_id,
            medico_nombre=c.medico_nombre, cita_id=c.cita_id,
            consultation_reason=c.consultation_reason, current_illness=c.current_illness,
            physical_exam=c.physical_exam, icd_diagnosis=c.icd_diagnosis,
            diagnosis_description=c.diagnosis_description,
            treatment=c.treatment, observations=c.observations,
        )
        for item in c.prescription:
            ItemRecetaModel.objects.create(
                consultation=m, medication=item.medication, dose=item.dose,
                frequency=item.frequency, duration=item.duration,
                indications=item.indications,
            )
        return c

    # â”€â”€ ExÃ¡menes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _exam(self, m: LabExamModel) -> LabExam:
        results = [
            AnalyteResult(
                analito=r.analito, valor=r.valor, unidad=r.unidad,
                rango_min=r.rango_min, rango_max=r.rango_max,
                status=r.status, color=r.color, icono=r.icono,
            ) for r in m.results.all()
        ]
        return LabExam(
            id=m.id, tenant_id=m.tenant_id, paciente_id=m.paciente_id,
            paciente_nombre=m.paciente_nombre, medico_id=m.medico_id,
            medico_nombre=m.medico_nombre, consulta_id=m.consulta_id,
            tipo_examen=m.tipo_examen, fecha_solicitud=m.fecha_solicitud,
            result_date=m.result_date, status=m.status,
            results=results, observations=m.observations,
        )

    def list_exams(self, tenant_id: int, paciente_id=None) -> List[LabExam]:
        qs = LabExamModel.objects.filter(tenant_id=tenant_id)
        if paciente_id:
            qs = qs.filter(paciente_id=paciente_id)
        return [self._exam(m) for m in qs]

    def save_exam(self, e: LabExam) -> LabExam:
        m = LabExamModel.objects.create(
            tenant_id=e.tenant_id, paciente_id=e.paciente_id,
            paciente_nombre=e.paciente_nombre, medico_id=e.medico_id,
            medico_nombre=e.medico_nombre, consulta_id=e.consulta_id,
            tipo_examen=e.tipo_examen, result_date=e.result_date,
            status=e.status, observations=e.observations,
        )
        for r in e.results:
            ResultadoAnalitoModel.objects.create(
                examen=m, analito=r.analito, valor=r.valor, unidad=r.unidad,
                rango_min=r.rango_min, rango_max=r.rango_max,
                status=r.status, color=r.color, icono=r.icono,
            )
        return self._exam(m)

