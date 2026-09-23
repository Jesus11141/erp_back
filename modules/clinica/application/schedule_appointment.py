from decimal import Decimal
from datetime import datetime
from ..domain.entities import (
    Patient, Doctor, Appointment, Consultation, LabExam, AnalyteResult
)
from ..domain.rangos_referencia import interpret_result, TIPOS_EXAMEN



class ScheduleAppointment:
    def __init__(self, repo):
        self.repo = repo

    def execute(self, tenant_id: int, datos: dict) -> Appointment:
        from datetime import date, time
        patient = self.repo.find_patient(datos['paciente_id'], tenant_id)
        if not patient:
            raise ValueError('Paciente no encontrado')
        doctor = self.repo.find_doctor(datos['medico_id'], tenant_id)
        if not doctor:
            raise ValueError('MÃ©dico no encontrado')
        appointment = Appointment(
            id=0, tenant_id=tenant_id,
            paciente_id=patient.id,
            paciente_nombre=patient.name,
            medico_id=doctor.id,
            medico_nombre=doctor.name,
            date=date.fromisoformat(datos['date']),
            hora=time.fromisoformat(datos['hora']),
            reason=datos.get('reason', ''),
        )
        return self.repo.save_appointment(appointment)




