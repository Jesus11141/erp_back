from decimal import Decimal
from .entities import ReferenceRange

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# CATÃLOGO DE RANGOS DE REFERENCIA
# Fuente: valores estÃ¡ndar de laboratorio clÃ­nico (OMS / laboratorios Ecuador)
# Cada entrada: (analito, unidad, gender, age_group, min, max, critico_min, critico_max)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _r(analito, unidad, gender, age_group, vmin, vmax, cmin=None, cmax=None):
    return ReferenceRange(
        analito=analito, unidad=unidad, gender=gender, age_group=age_group,
        valor_min=Decimal(str(vmin)), valor_max=Decimal(str(vmax)),
        critico_min=Decimal(str(cmin)) if cmin else None,
        critico_max=Decimal(str(cmax)) if cmax else None,
    )

RANGOS: list[ReferenceRange] = [

    # â”€â”€ BIOMETRÃA HEMÃTICA â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Hemoglobina
    _r('hemoglobina',       'g/dL',  'M', 'adulto',        13.5, 17.5, 7.0,  20.0),
    _r('hemoglobina',       'g/dL',  'F', 'adulto',        12.0, 16.0, 7.0,  20.0),
    _r('hemoglobina',       'g/dL',  'M', 'adulto_mayor',  12.0, 17.0, 7.0,  20.0),
    _r('hemoglobina',       'g/dL',  'F', 'adulto_mayor',  11.5, 16.0, 7.0,  20.0),
    _r('hemoglobina',       'g/dL',  'ambos', 'nino',       11.0, 14.0, 7.0,  20.0),
    _r('hemoglobina',       'g/dL',  'ambos', 'adolescente',12.0, 16.0, 7.0,  20.0),
    _r('hemoglobina',       'g/dL',  'ambos', 'neonato',    14.0, 24.0, 10.0, 30.0),

    # Hematocrito
    _r('hematocrito',       '%',     'M', 'adulto',        41.0, 53.0, 20.0, 60.0),
    _r('hematocrito',       '%',     'F', 'adulto',        36.0, 46.0, 20.0, 60.0),
    _r('hematocrito',       '%',     'ambos', 'nino',       33.0, 43.0, 20.0, 60.0),

    # GlÃ³bulos rojos
    _r('globulos_rojos',    'x10â¶/ÂµL', 'M', 'adulto',      4.5,  5.9,  2.0,  8.0),
    _r('globulos_rojos',    'x10â¶/ÂµL', 'F', 'adulto',      4.0,  5.2,  2.0,  8.0),

    # GlÃ³bulos blancos
    _r('globulos_blancos',  'x10Â³/ÂµL', 'ambos', 'adulto',   4.5, 11.0,  2.0, 30.0),
    _r('globulos_blancos',  'x10Â³/ÂµL', 'ambos', 'nino',     5.0, 15.0,  2.0, 30.0),
    _r('globulos_blancos',  'x10Â³/ÂµL', 'ambos', 'neonato',  9.0, 30.0,  2.0, 50.0),

    # Plaquetas
    _r('plaquetas',         'x10Â³/ÂµL', 'ambos', 'adulto',  150.0, 400.0, 50.0, 1000.0),
    _r('plaquetas',         'x10Â³/ÂµL', 'ambos', 'nino',    150.0, 450.0, 50.0, 1000.0),

    # NeutrÃ³filos, linfocitos, monocitos (%)
    _r('neutrofilos',       '%',     'ambos', 'adulto',     50.0, 70.0),
    _r('linfocitos',        '%',     'ambos', 'adulto',     20.0, 40.0),
    _r('monocitos',         '%',     'ambos', 'adulto',      2.0,  8.0),
    _r('eosinofilos',       '%',     'ambos', 'adulto',      1.0,  4.0),
    _r('basofilos',         '%',     'ambos', 'adulto',      0.0,  1.0),

    # VCM, HCM, CHCM
    _r('vcm',               'fL',    'ambos', 'adulto',     80.0, 100.0),
    _r('hcm',               'pg',    'ambos', 'adulto',     27.0,  33.0),
    _r('chcm',              'g/dL',  'ambos', 'adulto',     32.0,  36.0),

    # â”€â”€ QUÃMICA SANGUÃNEA â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Glucosa
    _r('glucosa',           'mg/dL', 'ambos', 'adulto',     70.0, 100.0, 40.0, 500.0),
    _r('glucosa',           'mg/dL', 'ambos', 'nino',       60.0,  99.0, 40.0, 400.0),
    _r('glucosa_2h',        'mg/dL', 'ambos', 'adulto',      0.0, 140.0, 40.0, 500.0),

    # Urea y creatinina
    _r('urea',              'mg/dL', 'ambos', 'adulto',     15.0,  45.0),
    _r('creatinina',        'mg/dL', 'M',     'adulto',      0.7,   1.3,  0.2,  10.0),
    _r('creatinina',        'mg/dL', 'F',     'adulto',      0.5,   1.1,  0.2,  10.0),
    _r('acido_urico',       'mg/dL', 'M',     'adulto',      3.5,   7.2),
    _r('acido_urico',       'mg/dL', 'F',     'adulto',      2.6,   6.0),

    # Perfil lipÃ­dico
    _r('colesterol_total',  'mg/dL', 'ambos', 'adulto',      0.0, 200.0, None, 300.0),
    _r('colesterol_ldl',    'mg/dL', 'ambos', 'adulto',      0.0, 130.0, None, 190.0),
    _r('colesterol_hdl',    'mg/dL', 'M',     'adulto',     40.0, 999.0),
    _r('colesterol_hdl',    'mg/dL', 'F',     'adulto',     50.0, 999.0),
    _r('trigliceridos',     'mg/dL', 'ambos', 'adulto',      0.0, 150.0, None, 500.0),

    # HepÃ¡ticas
    _r('tgo_ast',           'U/L',   'ambos', 'adulto',      5.0,  40.0, None, 1000.0),
    _r('tgp_alt',           'U/L',   'ambos', 'adulto',      5.0,  41.0, None, 1000.0),
    _r('fosfatasa_alcalina','U/L',   'ambos', 'adulto',     44.0, 147.0),
    _r('bilirrubina_total', 'mg/dL', 'ambos', 'adulto',      0.2,   1.2, None,  15.0),
    _r('bilirrubina_directa','mg/dL','ambos', 'adulto',      0.0,   0.3),
    _r('proteinas_totales', 'g/dL',  'ambos', 'adulto',      6.0,   8.3),
    _r('albumina',          'g/dL',  'ambos', 'adulto',      3.5,   5.0),

    # Tiroides
    _r('tsh',               'ÂµUI/mL','ambos', 'adulto',      0.4,   4.0, None,  10.0),
    _r('t4_libre',          'ng/dL', 'ambos', 'adulto',      0.8,   1.8),
    _r('t3_libre',          'pg/mL', 'ambos', 'adulto',      2.3,   4.2),

    # Electrolitos
    _r('sodio',             'mEq/L', 'ambos', 'adulto',    136.0, 145.0, 120.0, 160.0),
    _r('potasio',           'mEq/L', 'ambos', 'adulto',      3.5,   5.1,   2.5,   6.5),
    _r('cloro',             'mEq/L', 'ambos', 'adulto',     98.0, 107.0),
    _r('calcio',            'mg/dL', 'ambos', 'adulto',      8.5,  10.5,   6.0,  13.0),
    _r('magnesio',          'mg/dL', 'ambos', 'adulto',      1.7,   2.2),

    # Hemoglobina glicosilada
    _r('hba1c',             '%',     'ambos', 'adulto',      4.0,   5.6, None,  14.0),

    # PCR e inflamaciÃ³n
    _r('pcr',               'mg/L',  'ambos', 'adulto',      0.0,   5.0, None,  200.0),
    _r('vsg',               'mm/h',  'M',     'adulto',      0.0,  15.0),
    _r('vsg',               'mm/h',  'F',     'adulto',      0.0,  20.0),

    # â”€â”€ ORINA â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    _r('ph_orina',          '',      'ambos', 'adulto',      4.5,   8.0),
    _r('densidad_orina',    '',      'ambos', 'adulto',   1005.0, 1030.0),
    _r('proteinas_orina',   'mg/dL', 'ambos', 'adulto',      0.0,  14.0),
    _r('glucosa_orina',     'mg/dL', 'ambos', 'adulto',      0.0,  15.0),
]


def buscar_rango(analito: str, gender: str, age_group: str) -> ReferenceRange | None:
    """
    Busca el rango de referencia mÃ¡s especÃ­fico para un analito.
    Prioridad: gender+age exacto > gender+todos > ambos+age > ambos+todos
    """
    analito = analito.lower().strip()
    candidatos = [r for r in RANGOS if r.analito == analito]
    if not candidatos:
        return None

    def puntaje(r: ReferenceRange) -> int:
        p = 0
        if r.gender == gender:          p += 2
        elif r.gender == 'ambos':     p += 1
        if r.age_group == age_group: p += 2
        elif r.age_group == 'todos':  p += 1
        return p

    return max(candidatos, key=puntaje)


def interpret_result(analito: str, valor: float, gender: str, age_group: str) -> dict:
    """
    Dado un analito y su valor medido, retorna la interpretaciÃ³n completa.
    """
    from decimal import Decimal
    rango = buscar_rango(analito, gender, age_group)
    if not rango:
        return {
            'status': 'SIN_RANGO',
            'color': 'gris',
            'icono': '?',
            'rango_min': None,
            'rango_max': None,
            'unidad': '',
        }
    interpretacion = rango.interpretar(Decimal(str(valor)))
    return {
        **interpretacion,
        'rango_min': str(rango.valor_min),
        'rango_max': str(rango.valor_max),
        'unidad': rango.unidad,
        'critico_min': str(rango.critico_min) if rango.critico_min else None,
        'critico_max': str(rango.critico_max) if rango.critico_max else None,
    }


# Tipos de examen disponibles con sus analitos por defecto
TIPOS_EXAMEN = {
    'biometria_hematica': {
        'name': 'BiometrÃ­a HemÃ¡tica Completa',
        'analitos': [
            'hemoglobina', 'hematocrito', 'globulos_rojos', 'globulos_blancos',
            'plaquetas', 'neutrofilos', 'linfocitos', 'monocitos',
            'eosinofilos', 'basofilos', 'vcm', 'hcm', 'chcm',
        ]
    },
    'quimica_sanguinea': {
        'name': 'QuÃ­mica SanguÃ­nea',
        'analitos': ['glucosa', 'urea', 'creatinina', 'acido_urico']
    },
    'perfil_lipidico': {
        'name': 'Perfil LipÃ­dico',
        'analitos': ['colesterol_total', 'colesterol_ldl', 'colesterol_hdl', 'trigliceridos']
    },
    'perfil_hepatico': {
        'name': 'Perfil HepÃ¡tico',
        'analitos': ['tgo_ast', 'tgp_alt', 'fosfatasa_alcalina', 'bilirrubina_total',
                     'bilirrubina_directa', 'proteinas_totales', 'albumina']
    },
    'perfil_tiroideo': {
        'name': 'Perfil Tiroideo',
        'analitos': ['tsh', 't4_libre', 't3_libre']
    },
    'electrolitos': {
        'name': 'Electrolitos',
        'analitos': ['sodio', 'potasio', 'cloro', 'calcio', 'magnesio']
    },
    'hba1c': {
        'name': 'Hemoglobina Glicosilada',
        'analitos': ['hba1c']
    },
    'orina': {
        'name': 'Elemental y MicroscÃ³pico de Orina',
        'analitos': ['ph_orina', 'densidad_orina', 'proteinas_orina', 'glucosa_orina']
    },
}

