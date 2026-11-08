"""
Generador de XML para Guía de Remisión Electrónica SRI Ecuador
Tipo de comprobante: 06
Ficha Técnica: Comprobantes Electrónicos versión 1.1.0
"""
import random
from datetime import datetime, date
from decimal import Decimal
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom


def generate_access_key_guia(
    fecha: str,
    ruc: str,
    environment: str,
    serie: str,
    secuencial: str,
    tipo_emision: str = '1'
) -> str:
    """
    Genera la clave de acceso de 49 dígitos para Guía de Remisión (tipo 06).
    fecha: DD/MM/YYYY
    """
    fecha_str = fecha.replace('/', '')
    tipo_comprobante = '06'
    cod_numerico = str(random.randint(10000000, 99999999))
    sin_digito = (
        fecha_str + tipo_comprobante + ruc.strip().zfill(13) + environment.strip() +
        serie.replace('-', '').strip() + secuencial.strip().zfill(9) + cod_numerico + tipo_emision
    )
    return sin_digito + str(_modulo11(sin_digito))


def _modulo11(cadena: str) -> int:
    factor, suma = 2, 0
    for c in reversed(cadena):
        suma += int(c) * factor
        factor = factor + 1 if factor < 7 else 2
    residuo = suma % 11
    if residuo == 0: return 0
    if residuo == 1: return 1
    return 11 - residuo


def _t(parent, tag: str, text):
    el = SubElement(parent, tag)
    el.text = str(text) if text is not None else ''
    return el


def _fmt_date(d) -> str:
    if isinstance(d, (datetime, date)):
        return d.strftime('%d/%m/%Y')
    if isinstance(d, str) and len(d) >= 10:
        try:
            return datetime.strptime(d[:10], '%Y-%m-%d').strftime('%d/%m/%Y')
        except ValueError:
            return d
    return ''


def generate_xml_guia_remision(guia, emisor: dict) -> str:
    """
    Genera el XML para Guía de Remisión (v1.1.0) compatible con SRI Ecuador.
    """
    root = Element('guiaRemision', id='comprobante', version='1.1.0')

    date_emision = getattr(guia, 'date_emission', date.today())
    fecha_emision_str = _fmt_date(date_emision)
    start_date_str = _fmt_date(getattr(guia, 'start_date', date.today()))
    end_date_str = _fmt_date(getattr(guia, 'end_date', date.today()))

    access_key = getattr(guia, 'access_key', '')
    number = getattr(guia, 'number', '001-001-000000001')
    parts = number.split('-')
    estab = parts[0] if len(parts) > 0 else '001'
    pto_emi = parts[1] if len(parts) > 1 else '001'
    secuencial = parts[2] if len(parts) > 2 else '000000001'

    env = str(getattr(guia, 'environment', emisor.get('environment', '1')))

    # 1. infoTributaria
    it = SubElement(root, 'infoTributaria')
    _t(it, 'ambiente', env)
    _t(it, 'tipoEmision', '1')
    _t(it, 'razonSocial', emisor.get('razon_social', ''))
    _t(it, 'nombreComercial', emisor.get('nombre_comercial') or emisor.get('razon_social', ''))
    _t(it, 'ruc', emisor.get('ruc', ''))
    _t(it, 'claveAcceso', access_key)
    _t(it, 'codDoc', '06')
    _t(it, 'estab', estab)
    _t(it, 'ptoEmi', pto_emi)
    _t(it, 'secuencial', secuencial.zfill(9))
    _t(it, 'dirMatriz', emisor.get('direccion', ''))

    # 2. infoGuiaRemision
    igr = SubElement(root, 'infoGuiaRemision')
    _t(igr, 'dirEstablecimiento', emisor.get('direccion', ''))
    _t(igr, 'dirPartida', getattr(guia, 'starting_address', emisor.get('direccion', '')))
    _t(igr, 'razonSocialTransportista', getattr(guia, 'carrier_name', ''))
    _t(igr, 'tipoIdentificacionTransportista', getattr(guia, 'carrier_id_type', '04'))
    _t(igr, 'rucTransportista', getattr(guia, 'carrier_ruc', ''))
    _t(igr, 'obligadoContabilidad', emisor.get('obligado_contabilidad', 'NO'))
    _t(igr, 'fechaIniTraslado', start_date_str)
    _t(igr, 'fechaFinTraslado', end_date_str)
    _t(igr, 'placa', str(getattr(guia, 'vehicle_plate', '')).upper().strip())

    # 3. destinatarios
    destinatarios = SubElement(root, 'destinatarios')
    dest = SubElement(destinatarios, 'destinatario')
    _t(dest, 'identificacionDestinatario', getattr(guia, 'recipient_id', ''))
    _t(dest, 'razonSocialDestinatario', getattr(guia, 'recipient_name', ''))
    _t(dest, 'dirDestinatario', getattr(guia, 'recipient_address', ''))
    _t(dest, 'motivoTraslado', getattr(guia, 'transfer_reason', 'Venta') or 'Venta')
    if getattr(guia, 'route', ''):
        _t(dest, 'ruta', getattr(guia, 'route'))

    origin_num = getattr(guia, 'origin_doc_number', '')
    if origin_num:
        _t(dest, 'codDocSustento', getattr(guia, 'origin_doc_type', '01') or '01')
        _t(dest, 'numDocSustento', origin_num)
        auth_num = getattr(guia, 'origin_doc_auth', '')
        if auth_num:
            _t(dest, 'numAutDocSustento', auth_num)
        doc_date = getattr(guia, 'origin_doc_date', None)
        if doc_date:
            _t(dest, 'fechaEmisionDocSustento', _fmt_date(doc_date))

    # Detalles de mercadería
    detalles = SubElement(dest, 'detalles')
    for item in getattr(guia, 'items', []):
        d = SubElement(detalles, 'detalle')
        _t(d, 'codigoInterno', getattr(item, 'internal_code', '') or '001')
        _t(d, 'descripcion', getattr(item, 'description', ''))
        qty = Decimal(str(getattr(item, 'quantity', 1))).quantize(Decimal('0.01'))
        _t(d, 'cantidad', f"{qty:.2f}")

    xml_bytes = tostring(root, encoding='utf-8')
    return minidom.parseString(xml_bytes).toprettyxml(indent='  ', encoding='utf-8').decode('utf-8')
