"""
Validadores de identificación para Ecuador.
Usados en ventas (clientes) y facturación (comprobantes SRI).
"""


def validar_cedula_ecuador(cedula: str) -> bool:
    """
    Valida una cédula ecuatoriana (10 dígitos) usando módulo 10.
    """
    if not cedula or len(cedula) != 10 or not cedula.isdigit():
        return False
    provincia = int(cedula[:2])
    if provincia < 1 or provincia > 24:
        return False
    coeficientes = [2, 1, 2, 1, 2, 1, 2, 1, 2]
    suma = 0
    for i, coef in enumerate(coeficientes):
        valor = int(cedula[i]) * coef
        if valor >= 10:
            valor -= 9
        suma += valor
    digito_verificador = (10 - (suma % 10)) % 10
    return digito_verificador == int(cedula[9])


def validar_ruc_ecuador(ruc: str) -> bool:
    """
    Valida un RUC ecuatoriano (13 dígitos).
    - Personas naturales: cédula + '001'
    - Sociedades privadas: tercer dígito = 9, módulo 11
    - Entidades públicas: tercer dígito = 6, módulo 11
    """
    if not ruc or len(ruc) != 13 or not ruc.isdigit():
        return False
    if ruc[10:] != '001':
        return False
    tercer_digito = int(ruc[2])
    if tercer_digito < 6:
        # Persona natural: los primeros 10 dígitos son cédula
        return validar_cedula_ecuador(ruc[:10])
    elif tercer_digito == 6:
        # Entidad pública
        coeficientes = [3, 2, 7, 6, 5, 4, 3, 2]
        suma = sum(int(ruc[i]) * coeficientes[i] for i in range(8))
        residuo = suma % 11
        digito = 0 if residuo == 0 else 11 - residuo
        return digito == int(ruc[8])
    elif tercer_digito == 9:
        # Sociedad privada
        coeficientes = [4, 3, 2, 7, 6, 5, 4, 3, 2]
        suma = sum(int(ruc[i]) * coeficientes[i] for i in range(9))
        residuo = suma % 11
        digito = 0 if residuo == 0 else 11 - residuo
        return digito == int(ruc[9])
    return False


def tipo_identificacion_sri(identificacion: str) -> str:
    """
    Retorna el código de tipo de identificación SRI Ecuador:
    04 = RUC
    05 = Cédula
    06 = Pasaporte
    07 = Consumidor Final (9999999999999)
    """
    if identificacion == '9999999999999':
        return '07'
    if len(identificacion) == 13 and identificacion.isdigit():
        return '04'
    if len(identificacion) == 10 and identificacion.isdigit():
        return '05'
    return '06'
