from dataclasses import dataclass, field
from decimal import Decimal
from datetime import date, datetime, time
from typing import List, Optional

# â”€â”€ Paciente â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@dataclass
class Patient:
    id: int
    tenant_id: int
    id_number: str
    name: str
    birth_date: date
    gender: str                  # M, F
    blood_type: str           # A+, A-, B+, B-, AB+, AB-, O+, O-
    phone: str
    email: str
    address: str
    allergies: str = ''
    background: str = ''
    is_active: bool = True

    @property
    def age(self) -> int:
        hoy = date.today()
        return hoy.year - self.birth_date.year - (
            (hoy.month, hoy.day) < (self.birth_date.month, self.birth_date.day)
        )

    @property
    def age_group(self) -> str:
        e = self.age
        if e < 1:   return 'neonato'
        if e < 12:  return 'nino'
        if e < 18:  return 'adolescente'
        if e < 60:  return 'adulto'
        return 'adulto_mayor'


# â”€â”€ MÃ©dico â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@dataclass
class Doctor:
    id: int
    tenant_id: int
    id_number: str
    name: str
    specialty: str
    senescyt_record: str
    phone: str
    email: str
    is_active: bool = True
    consultation_percentage: Decimal = Decimal('70')  # % que le corresponde al mÃ©dico


# â”€â”€ Cita â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@dataclass
class Appointment:
    id: int
    tenant_id: int
    paciente_id: int
    paciente_nombre: str
    medico_id: int
    medico_nombre: str
    date: date
    hora: time
    reason: str
    status: str = 'scheduled'   # scheduled, confirmed, attended, canceled, no_show
    notes: str = ''

    ESTADOS = ['scheduled', 'confirmed', 'attended', 'canceled', 'no_show']

    def confirm(self):
        if self.status != 'scheduled':
            raise ValueError('Solo se puede confirm una appointment scheduled')
        self.status = 'confirmed'

    def cancel(self):
        if self.status == 'attended':
            raise ValueError('No se puede cancel una appointment ya attended')
        self.status = 'canceled'

    def attend(self):
        if self.status not in ('scheduled', 'confirmed'):
            raise ValueError('La appointment debit estar scheduled o confirmed para atenderse')
        self.status = 'attended'


# â”€â”€ Consulta â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@dataclass
class PrescriptionItem:
    medication: str
    dose: str
    frequency: str       # cada 8 horas, cada 12 horas, etc.
    duration: str         # 5 dÃ­as, 1 semana, etc.
    indications: str = ''

@dataclass
class Consultation:
    id: int
    tenant_id: int
    paciente_id: int
    paciente_nombre: str
    medico_id: int
    medico_nombre: str
    cita_id: Optional[int]
    date: datetime
    consultation_reason: str
    current_illness: str
    physical_exam: str
    icd_diagnosis: str       # CÃ³digo CIE-10 ej: J06.9
    diagnosis_description: str
    treatment: str
    observations: str = ''
    prescription: List[PrescriptionItem] = field(default_factory=list)
    next_appointment: Optional[date] = None
    status: str = 'open'    # open, closed

    def close(self):
        if self.status == 'closed':
            raise ValueError('La consultation ya estÃ¡ closed')
        self.status = 'closed'


# â”€â”€ Laboratorio â€” Motor de interpretaciÃ³n â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@dataclass
class ReferenceRange:
    """Define el rango normal para un analito segÃºn gender y grupo de age."""
    analito: str
    unidad: str
    gender: str              # M, F, ambos
    age_group: str        # neonato, nino, adolescente, adulto, adulto_mayor, todos
    valor_min: Decimal
    valor_max: Decimal
    critico_min: Optional[Decimal] = None   # valor de pÃ¡nico bajo
    critico_max: Optional[Decimal] = None   # valor de pÃ¡nico alto

    def interpretar(self, valor: Decimal) -> dict:
        if self.critico_min and valor < self.critico_min:
            return {'status': 'CRITICO_BAJO', 'color': 'rojo', 'icono': 'â¬‡â¬‡'}
        if self.critico_max and valor > self.critico_max:
            return {'status': 'CRITICO_ALTO', 'color': 'rojo', 'icono': 'â¬†â¬†'}
        if valor < self.valor_min:
            return {'status': 'BAJO', 'color': 'naranja', 'icono': 'â¬‡'}
        if valor > self.valor_max:
            return {'status': 'ALTO', 'color': 'naranja', 'icono': 'â¬†'}
        return {'status': 'NORMAL', 'color': 'verde', 'icono': 'âœ“'}


@dataclass
class AnalyteResult:
    analito: str
    valor: Decimal
    unidad: str
    rango_min: Decimal
    rango_max: Decimal
    status: str            # NORMAL, BAJO, ALTO, CRITICO_BAJO, CRITICO_ALTO
    color: str             # verde, naranja, rojo
    icono: str


@dataclass
class LabExam:
    id: int
    tenant_id: int
    paciente_id: int
    paciente_nombre: str
    medico_id: int
    medico_nombre: str
    consulta_id: Optional[int]
    tipo_examen: str           # biometria_hematica, quimica_sanguinea, orina, etc.
    fecha_solicitud: datetime
    result_date: Optional[datetime]
    status: str                # solicitado, en_proceso, completado
    results: List[AnalyteResult] = field(default_factory=list)
    observations: str = ''

    @property
    def tiene_criticos(self) -> bool:
        return any(r.status.startswith('CRITICO') for r in self.results)

    @property
    def tiene_alterados(self) -> bool:
        return any(r.status != 'NORMAL' for r in self.results)

    def resumen(self) -> str:
        total = len(self.results)
        normales = sum(1 for r in self.results if r.status == 'NORMAL')
        alterados = total - normales
        if alterados == 0:
            return f'Todos los valores normales ({total} analitos)'
        return f'{alterados} valor(es) alterado(s) de {total} analitos'

