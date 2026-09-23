from decimal import Decimal
from datetime import datetime
from ..domain.entities import (
    Patient, Doctor, Appointment, Consultation, LabExam, AnalyteResult
)
from ..domain.rangos_referencia import interpret_result, TIPOS_EXAMEN



class RegisterConsultation:
    def __init__(self, repo):
        self.repo = repo

    def execute(self, tenant_id: int, datos: dict) -> Consultation:
        patient = self.repo.find_patient(datos['paciente_id'], tenant_id)
        if not patient:
            raise ValueError('Paciente no encontrado')
        doctor = self.repo.find_doctor(datos['medico_id'], tenant_id)
        if not doctor:
            raise ValueError('MÃ©dico no encontrado')

        from ..domain.entities import PrescriptionItem
        prescription = [
            PrescriptionItem(
                medication=item['medication'],
                dose=item['dose'],
                frequency=item['frequency'],
                duration=item['duration'],
                indications=item.get('indications', ''),
            )
            for item in datos.get('prescription', [])
        ]

        consultation = Consultation(
            id=0, tenant_id=tenant_id,
            paciente_id=patient.id,
            paciente_nombre=patient.name,
            medico_id=doctor.id,
            medico_nombre=doctor.name,
            cita_id=datos.get('cita_id'),
            date=datetime.now(),
            consultation_reason=datos.get('consultation_reason', ''),
            current_illness=datos.get('current_illness', ''),
            physical_exam=datos.get('physical_exam', ''),
            icd_diagnosis=datos.get('icd_diagnosis', ''),
            diagnosis_description=datos.get('diagnosis_description', ''),
            treatment=datos.get('treatment', ''),
            observations=datos.get('observations', ''),
            prescription=prescription,
        )
        return self.repo.save_consultation(consultation)




