from decimal import Decimal
from datetime import datetime
from ..domain.entities import (
    Patient, Doctor, Appointment, Consultation, LabExam, AnalyteResult
)
from ..domain.rangos_referencia import interpret_result, TIPOS_EXAMEN



class RegisterPatient:
    def __init__(self, repo):
        self.repo = repo

    def execute(self, tenant_id: int, datos: dict) -> Patient:
        if not datos.get('id_number'):
            raise ValueError('La cÃ©dula es requerida')
        if not datos.get('name'):
            raise ValueError('El name es requerido')
        if self.repo.find_by_cedula(datos['id_number'], tenant_id):
            raise ValueError(f"Ya existe un patient con cÃ©dula {datos['id_number']}")
        from datetime import date
        patient = Patient(
            id=0, tenant_id=tenant_id,
            id_number=datos['id_number'],
            name=datos['name'],
            birth_date=date.fromisoformat(datos['birth_date']),
            gender=datos.get('gender', 'M'),
            blood_type=datos.get('blood_type', ''),
            phone=datos.get('phone', ''),
            email=datos.get('email', ''),
            address=datos.get('address', ''),
            allergies=datos.get('allergies', ''),
            background=datos.get('background', ''),
        )
        return self.repo.save_patient(patient)




