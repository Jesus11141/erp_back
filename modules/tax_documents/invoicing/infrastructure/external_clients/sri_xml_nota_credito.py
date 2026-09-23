"""
XML Nota de CrÃ©dito ElectrÃ³nica SRI Ecuador
Tipo de comprobante: 04
Ficha TÃ©cnica: Comprobantes ElectrÃ³nicos versiÃ³n 2.21
"""
import random
from datetime import date
from decimal import Decimal
from xml.etree.ElementTree import Element, SubElement, tostring
from collections import defaultdict


_TARIFA_A_CODIGO = {
    '0': '0', '5': '5', '8': '8', '12': '2', '15': '4',
}


def generate_access_key_nota_credito(fecha: str, ruc: str, environment: str,
                                       serie: str, secuencial: str,
                                       tipo_emision: str = '1') -> str:
    """Genera la clave de acceso de 49 dÃ­gitos para Nota de CrÃ©dito (tipo 04)"""
    fecha_str = fecha.replace('/', '')
    tipo_comprobante = '04'
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


def generate_xml_nota_credito(nota_credito, emisor: dict) -> str:
    """
    Genera el XML de Nota de CrÃ©dito electrÃ³nica SRI Ecuador.
    nota_credito: instancia de NotaCredito (entidad dominio)
    emisor: dict con ruc, razon_social, direccion, establecimiento, punto_emision, etc.
    """
    fecha_str = nota_credito.date.strftime('%d/%m/%Y')

    # Agrupar Ã­tems por tarifa IVA
    grupos_iva: dict[str, Decimal] = defaultdict(Decimal)
    for item in nota_credito.items:
        tarifa = str(getattr(item, 'vat_rate', '15'))
        grupos_iva[tarifa] += item.subtotal

    subtotal_total = sum(grupos_iva.values()).quantize(Decimal('0.01'))
    iva_total = sum(
        base * Decimal(t) / 100 for t, base in grupos_iva.items()
    ).quantize(Decimal('0.01'))
    total = (subtotal_total + iva_total).quantize(Decimal('0.01'))

    root = Element('notaCredito', id='comprobante', version='1.1.0')

    # infoTributaria
    it = SubElement(root, 'infoTributaria')
    _t(it, 'ambiente', nota_credito.environment)
    _t(it, 'tipoEmision', '1')
    _t(it, 'razonSocial', emisor['razon_social'])
    _t(it, 'nombreComercial', emisor.get('nombre_comercial', emisor['razon_social']))
    _t(it, 'ruc', emisor['ruc'])
    _t(it, 'claveAcceso', nota_credito.access_key)
    _t(it, 'codDoc', '04')
    _t(it, 'estab', emisor.get('establecimiento', '001'))
    _t(it, 'ptoEmi', emisor.get('punto_emision', '001'))
    _t(it, 'secuencial', nota_credito.number.split('-')[-1].zfill(9))
    _t(it, 'dirMatriz', emisor['direccion'])

    # infoNotaCredito
    inc = SubElement(root, 'infoNotaCredito')
    _t(inc, 'fechaEmision', fecha_str)
    _t(inc, 'dirEstablecimiento', emisor['direccion'])
    _t(inc, 'tipoIdentificacionComprador', nota_credito.client_id_type)
    _t(inc, 'razonSocialComprador', nota_credito.client)
    _t(inc, 'identificacionComprador', nota_credito.client_identification)
    if emisor.get('contribuyente_especial'):
        _t(inc, 'contribuyenteEspecial', emisor['contribuyente_especial'])
    _t(inc, 'obligadoContabilidad', emisor.get('obligado_contabilidad', 'NO'))
    _t(inc, 'codDocModificado', '01')       # 01 = Factura
    _t(inc, 'numDocModificado', nota_credito.origin_invoice_number)
    _t(inc, 'fechaEmisionDocSustento', fecha_str)
    _t(inc, 'totalSinImpuestos', str(subtotal_total))

    _t(inc, 'valorModificacion', str(total))
    _t(inc, 'moneda', 'DOLAR')

    # totalConImpuestos agrupados por tarifa
    tci = SubElement(inc, 'totalConImpuestos')
    for tarifa, base in sorted(grupos_iva.items()):
        base_q = base.quantize(Decimal('0.01'))
        valor_q = (base * Decimal(tarifa) / 100).quantize(Decimal('0.01'))
        ti = SubElement(tci, 'totalImpuesto')
        _t(ti, 'codigo', '2')
        _t(ti, 'codigoPorcentaje', _TARIFA_A_CODIGO.get(tarifa, '2'))
        _t(ti, 'baseImponible', str(base_q))
        _t(ti, 'valor', str(valor_q))

    _t(inc, 'motivo', nota_credito.reason)

    # detalles
    detalles = SubElement(root, 'detalles')
    for item in nota_credito.items:
        tarifa_item = str(getattr(item, 'vat_rate', '15'))
        subtotal_item = item.subtotal.quantize(Decimal('0.01'))
        iva_item = (item.subtotal * Decimal(tarifa_item) / 100).quantize(Decimal('0.01'))
        det = SubElement(detalles, 'detalle')
        _t(det, 'codigoInterno', item.main_code or '001')
        _t(det, 'descripcion', item.description)
        _t(det, 'cantidad', str(item.quantity.quantize(Decimal('0.000000'))))
        _t(det, 'precioUnitario', str(item.unit_price.quantize(Decimal('0.000000'))))
        _t(det, 'descuento', '0.00')
        _t(det, 'precioTotalSinImpuesto', str(subtotal_item))
        impuestos = SubElement(det, 'impuestos')
        imp = SubElement(impuestos, 'impuesto')
        _t(imp, 'codigo', '2')
        _t(imp, 'codigoPorcentaje', _TARIFA_A_CODIGO.get(tarifa_item, '2'))
        _t(imp, 'tarifa', tarifa_item)
        _t(imp, 'baseImponible', str(subtotal_item))
        _t(imp, 'valor', str(iva_item))

    xml_str = tostring(root, encoding='unicode')
    return '<?xml version="1.0" encoding="UTF-8"?>' + xml_str


def _t(parent: Element, tag: str, text: str):
    el = SubElement(parent, tag)
    el.text = text
    return el

