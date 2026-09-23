from django.urls import path
from .views import (
    PacientesView, PacienteDetalleView,
    MedicosView, CitasView, CitaAccionView,
    ConsultasView, ExamenesView,
    PlantillaExamenView, InterpretarValorView, TiposExamenView,
)

urlpatterns = [
    # Pacientes
    path('pacientes/',                          PacientesView.as_view()),
    path('pacientes/<int:paciente_id>/',        PacienteDetalleView.as_view()),

    # Médicos
    path('medicos/',                            MedicosView.as_view()),

    # Citas
    path('citas/',                              CitasView.as_view()),
    path('citas/<int:cita_id>/<str:accion>/',   CitaAccionView.as_view()),

    # Consultas
    path('consultas/',                          ConsultasView.as_view()),

    # Laboratorio
    path('examenes/',                           ExamenesView.as_view()),
    path('examenes/tipos/',                     TiposExamenView.as_view()),
    path('examenes/plantilla/<str:tipo_examen>/', PlantillaExamenView.as_view()),
    path('examenes/interpretar/',               InterpretarValorView.as_view()),
]
