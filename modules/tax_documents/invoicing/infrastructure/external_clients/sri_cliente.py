"""
Cliente Webservice SRI Ecuador
Recepción: https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline
Autorización: https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline
"""
import base64
import requests
from xml.etree import ElementTree as ET

URLS = {
    '1': {  # Pruebas
        'recepcion':    'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl',
        'autorizacion': 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl',
    },
    '2': {  # Producción
        'recepcion':    'https://cel.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl',
        'autorizacion': 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl',
    },
}

SOAP_RECEPCION = """<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:ec="http://ec.gob.sri.ws.recepcion">
  <soapenv:Header/>
  <soapenv:Body>
    <ec:validarComprobante>
      <xml>{xml_b64}</xml>
    </ec:validarComprobante>
  </soapenv:Body>
</soapenv:Envelope>"""

SOAP_AUTORIZACION = """<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:ec="http://ec.gob.sri.ws.autorizacion">
  <soapenv:Header/>
  <soapenv:Body>
    <ec:autorizacionComprobante>
      <claveAccesoComprobante>{clave_acceso}</claveAccesoComprobante>
    </ec:autorizacionComprobante>
  </soapenv:Body>
</soapenv:Envelope>"""


def send_receipt(signed_xml: str, environment: str) -> dict:
    """
    Envía el XML firmado al SRI
    Retorna: {'estado': 'RECIBIDA'|'DEVUELTA', 'messages': [...]}
    """
    url = URLS[environment]['recepcion'].replace('?wsdl', '')
    xml_b64 = base64.b64encode(signed_xml.encode('utf-8')).decode('utf-8')
    soap_body = SOAP_RECEPCION.format(xml_b64=xml_b64)

    try:
        resp = requests.post(
            url,
            data=soap_body.encode('utf-8'),
            headers={'Content-Type': 'text/xml; charset=utf-8'},
            timeout=30,
        )
        return _parsear_respuesta_recepcion(resp.text)
    except requests.Timeout:
        return {'estado': 'ERROR', 'messages': ['Timeout al conectar con SRI']}
    except Exception as e:
        return {'estado': 'ERROR', 'messages': [str(e)]}


def consultar_autorizacion(clave_acceso: str, environment: str) -> dict:
    """
    Consulta la autorización de un comprobante
    Retorna: {'estado': 'AUTORIZADA'|'NO_AUTORIZADA', 'numero_autorizacion': '', 'fecha': '', 'messages': [...]}
    """
    url = URLS[environment]['autorizacion'].replace('?wsdl', '')
    soap_body = SOAP_AUTORIZACION.format(clave_acceso=clave_acceso)

    try:
        resp = requests.post(
            url,
            data=soap_body.encode('utf-8'),
            headers={'Content-Type': 'text/xml; charset=utf-8'},
            timeout=30,
        )
        return _parsear_respuesta_autorizacion(resp.text)
    except requests.Timeout:
        return {'estado': 'ERROR', 'messages': ['Timeout al conectar con SRI']}
    except Exception as e:
        return {'estado': 'ERROR', 'messages': [str(e)]}


def _parsear_respuesta_recepcion(xml_resp: str) -> dict:
    try:
        root = ET.fromstring(xml_resp)
        estado_el = _find_ns_agnostic(root, 'estado')
        estado = estado_el.text if estado_el is not None else 'ERROR'
        messages = []
        for m in _find_all_ns_agnostic(root, 'mensaje'):
            identificador = _find_ns_agnostic(m, 'identificador')
            mensaje = _find_ns_agnostic(m, 'mensaje')
            if mensaje is not None and mensaje.text:
                messages.append(f"{getattr(identificador, 'text', '')} - {mensaje.text}")
        return {'estado': estado, 'messages': messages}
    except Exception as e:
        return {'estado': 'ERROR', 'messages': [f'Error parseando respuesta: {str(e)}']}


def _find_ns_agnostic(element, tag_name):
    for el in element.iter():
        if el.tag.endswith(f"}}{tag_name}") or el.tag == tag_name:
            return el
    return None

def _find_all_ns_agnostic(element, tag_name):
    return [el for el in element.iter() if el.tag.endswith(f"}}{tag_name}") or el.tag == tag_name]

def _parsear_respuesta_autorizacion(xml_resp: str) -> dict:
    try:
        root = ET.fromstring(xml_resp)
        autorizacion = _find_ns_agnostic(root, 'autorizacion')
        if autorizacion is None:
            # Check if numeroComprobantes is 0
            num_comprobantes = _find_ns_agnostic(root, 'numeroComprobantes')
            if num_comprobantes is not None and num_comprobantes.text == '0':
                return {'estado': 'NO_AUTORIZADA', 'messages': ['La factura no existe en el SRI. Fue rechazada al enviarse o la clave de acceso es inválida.']}
            return {'estado': 'NO_AUTORIZADA', 'messages': ['Sin respuesta de autorización en el XML', xml_resp[:200]]}

        estado_el = _find_ns_agnostic(autorizacion, 'estado')
        num_el = _find_ns_agnostic(autorizacion, 'numeroAutorizacion')
        fecha_el = _find_ns_agnostic(autorizacion, 'fechaAutorizacion')

        estado = estado_el.text if estado_el is not None else 'NO_AUTORIZADA'
        numero = num_el.text if num_el is not None else ''
        fecha = fecha_el.text if fecha_el is not None else ''

        messages = []
        for m in _find_all_ns_agnostic(root, 'mensaje'):
            msg = _find_ns_agnostic(m, 'mensaje')
            if msg is not None and msg.text:
                messages.append(msg.text)

        return {
            'estado': estado,
            'numero_autorizacion': numero,
            'fecha_autorizacion': fecha,
            'messages': messages,
        }
    except Exception as e:
        return {'estado': 'ERROR', 'messages': [f'Error parseando respuesta: {str(e)}']}
