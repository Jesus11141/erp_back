from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ...application.use_cases import (
    RegisterPatient, ScheduleAppointment, RegisterConsultation, ProcessExam
)
from ...domain.rangos_referencia import TIPOS_EXAMEN, interpret_result
from ..repository_impl import DjangoClinicaRepository


def _verificar(request):
    if not request.tenant or not request.tenant.has_module('clinica'):
        return Response({'error': 'MÃ³dulo clÃ­nica no disponible'}, status=403)
    return None


def _paciente_dict(p):
    return {
        'id': p.id, 'id_number': p.id_number, 'name': p.name,
        'birth_date': str(p.birth_date), 'age': p.age,
        'gender': p.gender, 'blood_type': p.blood_type,
        'phone': p.phone, 'email': p.email,
        'allergies': p.allergies, 'background': p.background,
    }


def _cita_dict(c):
    return {
        'id': c.id, 'paciente_id': c.paciente_id, 'paciente_nombre': c.paciente_nombre,
        'medico_id': c.medico_id, 'medico_nombre': c.medico_nombre,
        'date': str(c.date), 'hora': str(c.hora),
        'reason': c.reason, 'status': c.status,
    }


def _resultado_dict(r):
    return {
        'analito': r.analito, 'valor': str(r.valor), 'unidad': r.unidad,
        'rango_min': str(r.rango_min), 'rango_max': str(r.rango_max),
        'status': r.status, 'color': r.color, 'icono': r.icono,
    }


def _examen_dict(e):
    return {
        'id': e.id, 'paciente_nombre': e.paciente_nombre,
        'medico_nombre': e.medico_nombre, 'tipo_examen': e.tipo_examen,
        'result_date': str(e.result_date) if e.result_date else None,
        'status': e.status,
        'tiene_criticos': e.tiene_criticos,
        'tiene_alterados': e.tiene_alterados,
        'resumen': e.resumen(),
        'results': [_resultado_dict(r) for r in e.results],
        'observations': e.observations,
    }


# â”€â”€ Pacientes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class PacientesView(APIView):
    def get(self, request):
        if e := _verificar(request): return e
        repo = DjangoClinicaRepository()
        q = request.query_params.get('q', '')
        pacientes = repo.list_patients(request.tenant.id, q)
        return Response([_paciente_dict(p) for p in pacientes])

    def post(self, request):
        if e := _verificar(request): return e
        try:
            patient = RegisterPatient(DjangoClinicaRepository()).execute(
                request.tenant.id, request.data
            )
            return Response(_paciente_dict(patient), status=201)
        except ValueError as e:
            return Response({'error': str(e)}, status=400)


class PacienteDetalleView(APIView):
    def get(self, request, paciente_id):
        if e := _verificar(request): return e
        repo = DjangoClinicaRepository()
        patient = repo.find_patient(paciente_id, request.tenant.id)
        if not patient:
            return Response({'error': 'Paciente no encontrado'}, status=404)
        historial = repo.patient_history(paciente_id, request.tenant.id)
        return Response({
            **_paciente_dict(patient),
            'consultas': historial['consultas'],
            'examenes': historial['examenes'],
        })


# â”€â”€ MÃ©dicos â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class MedicosView(APIView):
    def get(self, request):
        if e := _verificar(request): return e
        medicos = DjangoClinicaRepository().list_doctors(request.tenant.id)
        return Response([{
            'id': m.id, 'name': m.name, 'specialty': m.specialty,
            'senescyt_record': m.senescyt_record, 'phone': m.phone,
        } for m in medicos])

    def post(self, request):
        if e := _verificar(request): return e
        repo = DjangoClinicaRepository()
        try:
            from ..domain.entities import Doctor
            from decimal import Decimal
            doctor = Doctor(
                id=0, tenant_id=request.tenant.id,
                id_number=request.data.get('id_number', ''),
                name=request.data['name'],
                specialty=request.data.get('specialty', ''),
                senescyt_record=request.data.get('senescyt_record', ''),
                phone=request.data.get('phone', ''),
                email=request.data.get('email', ''),
                consultation_percentage=Decimal(str(request.data.get('consultation_percentage', 70))),
            )
            doctor = repo.save_doctor(doctor)
            return Response({'id': doctor.id, 'name': doctor.name}, status=201)
        except (ValueError, KeyError) as e:
            return Response({'error': str(e)}, status=400)


# â”€â”€ Citas â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class CitasView(APIView):
    def get(self, request):
        if e := _verificar(request): return e
        date = request.query_params.get('date')
        medico_id = request.query_params.get('medico_id')
        citas = DjangoClinicaRepository().list_appointments(
            request.tenant.id, date=date, medico_id=medico_id
        )
        return Response([_cita_dict(c) for c in citas])

    def post(self, request):
        if e := _verificar(request): return e
        try:
            appointment = ScheduleAppointment(DjangoClinicaRepository()).execute(
                request.tenant.id, request.data
            )
            return Response(_cita_dict(appointment), status=201)
        except ValueError as e:
            return Response({'error': str(e)}, status=400)


class CitaAccionView(APIView):
    def post(self, request, cita_id, accion):
        if e := _verificar(request): return e
        repo = DjangoClinicaRepository()
        appointment = repo.find_appointment(cita_id, request.tenant.id)
        if not appointment:
            return Response({'error': 'Cita no encontrada'}, status=404)
        try:
            if accion == 'confirm':   appointment.confirm()
            elif accion == 'cancel':  appointment.cancel()
            elif accion == 'attend':   appointment.attend()
            else:
                return Response({'error': 'AcciÃ³n no vÃ¡lida'}, status=400)
            repo.save_appointment(appointment)
            return Response(_cita_dict(appointment))
        except ValueError as e:
            return Response({'error': str(e)}, status=400)


# â”€â”€ Consultas â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class ConsultasView(APIView):
    def post(self, request):
        if e := _verificar(request): return e
        try:
            consultation = RegisterConsultation(DjangoClinicaRepository()).execute(
                request.tenant.id, request.data
            )
            return Response({'id': consultation.id, 'patient': consultation.paciente_nombre}, status=201)
        except ValueError as e:
            return Response({'error': str(e)}, status=400)


# â”€â”€ Laboratorio â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class ExamenesView(APIView):
    def get(self, request):
        if e := _verificar(request): return e
        paciente_id = request.query_params.get('paciente_id')
        examenes = DjangoClinicaRepository().list_exams(
            request.tenant.id, paciente_id=paciente_id
        )
        return Response([_examen_dict(e) for e in examenes])

    def post(self, request):
        if e := _verificar(request): return e
        try:
            examen = ProcessExam(DjangoClinicaRepository()).execute(
                request.tenant.id, request.data
            )
            return Response(_examen_dict(examen), status=201)
        except ValueError as e:
            return Response({'error': str(e)}, status=400)


class PlantillaExamenView(APIView):
    """Retorna los analitos que se deben ingresar para un type de examen."""
    def get(self, request, tipo_examen):
        if e := _verificar(request): return e
        if tipo_examen not in TIPOS_EXAMEN:
            return Response({'error': 'Tipo de examen no reconocido'}, status=404)
        return Response(TIPOS_EXAMEN[tipo_examen])


class InterpretarValorView(APIView):
    """
    Interpreta un valor en tiempo real mientras el laboratorista escribe.
    Ãštil para feedback inmediato en el formulario.
    """
    def post(self, request):
        if e := _verificar(request): return e
        try:
            repo = DjangoClinicaRepository()
            patient = repo.find_patient(request.data['paciente_id'], request.tenant.id)
            if not patient:
                return Response({'error': 'Paciente no encontrado'}, status=404)
            result = interpret_result(
                analito=request.data['analito'],
                valor=float(request.data['valor']),
                gender=patient.gender,
                age_group=patient.age_group,
            )
            return Response(result)
        except (ValueError, KeyError) as e:
            return Response({'error': str(e)}, status=400)


class TiposExamenView(APIView):
    """Lista todos los tipos de examen disponibles."""
    def get(self, request):
        return Response([
            {'clave': k, 'name': v['name'], 'total_analitos': len(v['analitos'])}
            for k, v in TIPOS_EXAMEN.items()
        ])

