"""
XML Comprobante de Retención Electrónica SRI Ecuador
Tipo de comprobante: 07
Ficha Técnica: Comprobantes Electrónicos versión 2.21
"""
import random
from decimal import Decimal
from xml.etree.ElementTree import Element, SubElement, tostring


def generate_access_key_retencion(fecha: str, ruc: str, environment: str,
                                    serie: str, secuencial: str,
                                    tipo_emision: str = '1') -> str:
    """Genera la clave de acceso de 49 dígitos para Retención (tipo 07)"""
    fecha_str = fecha.replace('/', '')
    tipo_comprobante = '07'
    cod_numerico = str(random.randint(10000000, 99999999))
    sin_digito = (
        fecha_str + tipo_comprobante + ruc + environment +
        serie.replace('-', '') + secuencial.zfill(9) + cod_numerico + tipo_emision
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


def generate_xml_retencion(retencion, emisor: dict) -> str:
    """
    Genera el XML de Comprobante de Retención electrónico SRI Ecuador.
    retencion: instancia de Retencion (entidad dominio)
    emisor: dict con ruc, razon_social, direccion, establecimiento, punto_emision, etc.
    """
    fecha_str = retencion.fecha.strftime('%d/%m/%Y')

    root = Element('comprobanteRetencion', id='comprobante', version='2.0.0')

    # infoTributaria
    it = SubElement(root, 'infoTributaria')
    _t(it, 'environment', retencion.environment)
    _t(it, 'tipoEmision', '1')
    _t(it, 'razonSocial', emisor['razon_social'])
    _t(it, 'nombreComercial', emisor.get('nombre_comercial', emisor['razon_social']))
    _t(it, 'ruc', emisor['ruc'])
    _t(it, 'claveAcceso', retencion.clave_acceso)
    _t(it, 'codDoc', '07')
    _t(it, 'estab', emisor.get('establecimiento', '001'))
    _t(it, 'ptoEmi', emisor.get('punto_emision', '001'))
    _t(it, 'secuencial', retencion.numero.split('-')[-1].zfill(9))
    _t(it, 'dirMatriz', emisor['direccion'])

    # infoCompRetencion
    icr = SubElement(root, 'infoCompRetencion')
    _t(icr, 'fechaEmision', fecha_str)
    _t(icr, 'dirEstablecimiento', emisor['direccion'])
    if emisor.get('contribuyente_especial'):
        _t(icr, 'contribuyenteEspecial', emisor['contribuyente_especial'])
    _t(icr, 'obligadoContabilidad', emisor.get('obligado_contabilidad', 'NO'))
    _t(icr, 'tipoIdentificacionSujetoRetenido', retencion.proveedor_tipo_id)
    _t(icr, 'razonSocialSujetoRetenido', retencion.proveedor)
    _t(icr, 'identificacionSujetoRetenido', retencion.proveedor_identificacion)
    _t(icr, 'periodoFiscal', retencion.periodo_fiscal)

    # impuestos
    impuestos_el = SubElement(root, 'impuestos')
    for item in retencion.items:
        imp = SubElement(impuestos_el, 'impuesto')
        # código: 1=Renta, 2=IVA, 6=ISD
        _t(imp, 'codigo', item.codigo_tipo)
        _t(imp, 'codigoRetencion', item.codigo_retencion)
        _t(imp, 'baseImponible', str(item.base_imponible.quantize(Decimal('0.01'))))
        _t(imp, 'porcentajeRetener', str(item.porcentaje))
        _t(imp, 'valorRetenido', str(item.valor_retenido.quantize(Decimal('0.01'))))
        _t(imp, 'codDocSustento', '01')     # 01 = factura
        _t(imp, 'numDocSustento', retencion.factura_origen_numero)
        _t(imp, 'fechaEmisionDocSustento', fecha_str)

    xml_str = tostring(root, encoding='unicode')
    return '<?xml version="1.0" encoding="UTF-8"?>' + xml_str


def _t(parent: Element, tag: str, text: str):
    el = SubElement(parent, tag)
    el.text = text
    return el
