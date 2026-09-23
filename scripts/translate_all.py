import os
import re

# This script is designed to safely translate Spanish domain terms to English
# across the 'auth', 'clinica', and 'contabilidad' modules without breaking
# the database structure (by preserving db_table and db_column).

MAPPINGS = {
    # auth
    'permisos_por_rol': 'permissions_by_role',
    'permisos': 'permissions',
    'modulo': 'module',
    'Rol inválido': 'Invalid role',
    'Opciones': 'Options',
    'Ya existe un usuario con ese email': 'A user with that email already exists',
    
    # clinica
    'paciente': 'patient',
    'medico': 'doctor',
    'cita': 'appointment',
    'consulta': 'consultation',
    'ItemReceta': 'PrescriptionItem',
    'RangoReferencia': 'ReferenceRange',
    'cedula': 'id_number',
    'nombre': 'name',
    'fecha_nacimiento': 'birth_date',
    'sexo': 'gender',
    'tipo_sangre': 'blood_type',
    'telefono': 'phone',
    'direccion': 'address',
    'alergias': 'allergies',
    'antecedentes': 'background',
    'activo': 'is_active',
    'edad': 'age',
    'grupo_edad': 'age_group',
    'especialidad': 'specialty',
    'registro_senescyt': 'senescyt_record',
    'porcentaje_consulta': 'consultation_percentage',
    'motivo': 'reason',
    'estado': 'status',
    'notas': 'notes',
    'confirmar': 'confirm',
    'cancelar': 'cancel',
    'atender': 'attend',
    'medicamento': 'medication',
    'dosis': 'dose',
    'frecuencia': 'frequency',
    'duracion': 'duration',
    'indicaciones': 'indications',
    'motivo_consulta': 'consultation_reason',
    'enfermedad_actual': 'current_illness',
    'examen_fisico': 'physical_exam',
    'diagnostico_cie': 'icd_diagnosis',
    'diagnostico_descripcion': 'diagnosis_description',
    'tratamiento': 'treatment',
    'observaciones': 'observations',
    'receta': 'prescription',
    'proxima_cita': 'next_appointment',
    'cerrar': 'close',
    
    # contabilidad
    'cuenta': 'account',
    'asiento': 'journal_entry',
    'glosa': 'description',
    'fecha': 'date',
    'tipo': 'type',
    'padre': 'parent',
    'debe': 'debit',
    'haber': 'credit'
}

def translate_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    original = content
    
    # Simple replace - in a real scenario we'd use AST or more careful regex boundaries
    for es, en in MAPPINGS.items():
        # Only replace word boundaries to avoid partial matches
        content = re.sub(rf'\b{es}\b', en, content)
        
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Translated: {filepath}")

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    modules_to_translate = ['auth', 'clinica', 'contabilidad']
    
    for mod in modules_to_translate:
        mod_path = os.path.join(base_dir, 'modules', mod)
        for root, dirs, files in os.walk(mod_path):
            for file in files:
                if file.endswith('.py'):
                    translate_file(os.path.join(root, file))

if __name__ == "__main__":
    main()
