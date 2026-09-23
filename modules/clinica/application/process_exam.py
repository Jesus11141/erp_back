from decimal import Decimal
from datetime import datetime
from ..domain.entities import (
    Patient, Doctor, Appointment, Consultation, LabExam, AnalyteResult
)
from ..domain.rangos_referencia import interpret_result, TIPOS_EXAMEN



class ProcessExam:
    """
    Caso de uso principal del motor de laboratorio.
    Recibe los valores medidos, los interpreta automÃ¡ticamente
    comparando contra los rangos de referencia del patient.
    """
    def __init__(self, repo):
        self.repo = repo

    def execute(self, tenant_id: int, datos: dict) -> LabExam:
        patient = self.repo.find_patient(datos['paciente_id'], tenant_id)
        if not patient:
            raise ValueError('Paciente no encontrado')
        doctor = self.repo.find_doctor(datos['medico_id'], tenant_id)
        if not doctor:
            raise ValueError('MÃ©dico no encontrado')

        # Interpretar cada analito automÃ¡ticamente
        results = []
        for item in datos.get('valores', []):
            analito = item['analito'].lower().strip()
            valor = Decimal(str(item['valor']))
            interpretacion = interpret_result(
                analito=analito,
                valor=float(valor),
                gender=patient.gender,
                age_group=patient.age_group,
            )
            results.append(AnalyteResult(
                analito=analito,
                valor=valor,
                unidad=interpretacion.get('unidad', item.get('unidad', '')),
                rango_min=Decimal(interpretacion['rango_min']) if interpretacion.get('rango_min') else Decimal('0'),
                rango_max=Decimal(interpretacion['rango_max']) if interpretacion.get('rango_max') else Decimal('0'),
                status=interpretacion['status'],
                color=interpretacion['color'],
                icono=interpretacion['icono'],
            ))

        examen = LabExam(
            id=0, tenant_id=tenant_id,
            paciente_id=patient.id,
            paciente_nombre=patient.name,
            medico_id=doctor.id,
            medico_nombre=doctor.name,
            consulta_id=datos.get('consulta_id'),
            tipo_examen=datos.get('tipo_examen', 'biometria_hematica'),
            fecha_solicitud=datetime.now(),
            result_date=datetime.now(),
            status='completado',
            results=results,
            observations=datos.get('observations', ''),
        )
        return self.repo.save_exam(examen)

    def get_template(self, tipo_examen: str) -> dict:
        """Retorna los analitos que debit ingresar el laboratorista para un type de examen."""
        if tipo_examen not in TIPOS_EXAMEN:
            raise ValueError(f'Tipo de examen no reconocido: {tipo_examen}')
        return TIPOS_EXAMEN[tipo_examen]


