"""
Generador de XML para Factura ElectrÃ³nica SRI Ecuador
Ficha TÃ©cnica: Comprobantes ElectrÃ³nicos versiÃ³n 2.21
Soporte para mÃºltiples tarifas de IVA por Ã­tem (0%, 5%, 8%, 15%)
"""
import hashlib
import random
from datetime import datetime
from decimal import Decimal
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
from collections import defaultdict


# Mapeo tarifa IVA â†’ cÃ³digo de porcentaje SRI Ecuador
_TARIFA_A_CODIGO = {
    '0':  '0',   # 0%   â†’ cÃ³digo 0
    '5':  '5',   # 5%   â†’ cÃ³digo 5 (materiales de construcciÃ³n)
    '8':  '8',   # 8%   â†’ cÃ³digo 8 (turismo)
    '12': '2',   # 12%  â†’ cÃ³digo 2 (histÃ³rico, por compatibilidad)
    '15': '2',   # 15%  â†’ cÃ³digo 2 (tarifa vigente)
}


def generate_access_key(fecha: str, ruc: str, environment: str, serie: str,
                          secuencial: str, tipo_emision: str = '1') -> str:
    """
    Genera la clave de acceso de 49 dÃ­gitos segÃºn SRI Ecuador
    fecha: DD/MM/YYYY
    """
    fecha_str = fecha.replace('/', '')          # DDMMYYYY
    tipo_comprobante = '01'                      # 01 = Factura
    cod_numerico = str(random.randint(10000000, 99999999))
    sin_digito = (
        str(fecha).replace('/', '').strip() +
        str(tipo_comprobante).strip() +
        str(ruc).strip().zfill(13) +
        str(environment).strip() +
        str(serie).replace('-', '').strip() +
        str(secuencial).strip().zfill(9) +
        str(cod_numerico).strip() +
        str(tipo_emision).strip()
    )
    sin_digito = sin_digito.replace(' ', '')
    print(f"DEBUG SRI ACCESS KEY: '{sin_digito}'")
    digito = _modulo11(sin_digito)
    return sin_digito + str(digito)


def _modulo11(cadena: str) -> int:
    factor = 2
    suma = 0
    for c in reversed(cadena):
        suma += int(c) * factor
        factor = factor + 1 if factor < 7 else 2
    residuo = suma % 11
    if residuo == 0:
        return 0
    if residuo == 1:
        return 1
    return 11 - residuo


def generate_xml(factura, emisor: dict) -> str:
    """
    Genera el XML de factura electrÃ³nica SRI.
    Soporta mÃºltiples tarifas de IVA por Ã­tem segÃºn ficha tÃ©cnica SRI Ecuador v2.21.

    emisor: dict con ruc, razon_social, nombre_comercial, direccion,
            obligado_contabilidad, contribuyente_especial,
            establecimiento, punto_emision
    """
    fecha_str = factura.fecha.strftime('%d/%m/%Y')

    # â”€â”€ Agrupar Ã­tems por tarifa IVA para calcular bases imponibles â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    grupos_iva: dict[str, Decimal] = defaultdict(Decimal)
    for item in factura.items:
        tarifa = str(getattr(item, 'tarifa_iva', '15'))
        grupos_iva[tarifa] += item.subtotal

    subtotal_total = sum(grupos_iva.values())
    iva_total = sum(
        base * Decimal(tarifa) / 100
        for tarifa, base in grupos_iva.items()
    )
    total = subtotal_total + iva_total

    subtotal_total = subtotal_total.quantize(Decimal('0.01'))
    iva_total = iva_total.quantize(Decimal('0.01'))
    total = total.quantize(Decimal('0.01'))

    root = Element('factura', id='comprobante', version='2.1.0')

    # â”€â”€ infoTributaria â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    it = SubElement(root, 'infoTributaria')
    _t(it, 'environment', factura.environment)
    _t(it, 'tipoEmision', '1')
    _t(it, 'razonSocial', emisor['razon_social'])
    _t(it, 'nombreComercial', emisor.get('nombre_comercial', emisor['razon_social']))
    _t(it, 'ruc', emisor['ruc'])
    _t(it, 'claveAcceso', getattr(factura, 'clave_acceso', getattr(factura, 'access_key', '')))
    _t(it, 'codDoc', '01')
    _t(it, 'estab', emisor.get('establecimiento', '001'))
    _t(it, 'ptoEmi', emisor.get('punto_emision', '001'))
    _t(it, 'secuencial', (getattr(factura, 'numero', getattr(factura, 'number', '001-001-000000001'))).split('-')[-1].zfill(9))
    _t(it, 'dirMatriz', emisor['direccion'])

    # â”€â”€ infoFactura â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    inf = SubElement(root, 'infoFactura')
    _t(inf, 'fechaEmision', fecha_str)
    _t(inf, 'dirEstablecimiento', emisor['direccion'])
    if emisor.get('contribuyente_especial'):
        _t(inf, 'contribuyenteEspecial', emisor['contribuyente_especial'])
    _t(inf, 'obligadoContabilidad', emisor.get('obligado_contabilidad', 'NO'))
    _t(inf, 'tipoIdentificacionComprador', getattr(factura, 'cliente_tipo_id', getattr(factura, 'client_id_type', '07')) or '07')
    _t(inf, 'razonSocialComprador', getattr(factura, 'cliente', getattr(factura, 'client', 'CONSUMIDOR FINAL')) or 'CONSUMIDOR FINAL')
    _t(inf, 'identificacionComprador', getattr(factura, 'cliente_identificacion', getattr(factura, 'client_identification', '9999999999999')) or '9999999999999')
    _t(inf, 'direccionComprador', getattr(factura, 'cliente_direccion', getattr(factura, 'client_address', 'S/N')) or 'S/N')
    _t(inf, 'totalSinImpuestos', str(subtotal_total))
    _t(inf, 'totalDescuento', '0.00')

    # totalConImpuestos â€” un bloque por tarifa de IVA
    tci = SubElement(inf, 'totalConImpuestos')
    for tarifa, base in sorted(grupos_iva.items()):
        base_q = base.quantize(Decimal('0.01'))
        valor_q = (base * Decimal(tarifa) / 100).quantize(Decimal('0.01'))
        codigo_pct = _TARIFA_A_CODIGO.get(tarifa, '2')
        ti = SubElement(tci, 'totalImpuesto')
        _t(ti, 'codigo', '2')                   # 2 = IVA
        _t(ti, 'codigoPorcentaje', codigo_pct)
        _t(ti, 'baseImponible', str(base_q))
        _t(ti, 'valor', str(valor_q))

    _t(inf, 'propina', '0.00')
    _t(inf, 'importeTotal', str(total))
    _t(inf, 'moneda', 'DOLAR')

    # pagos
    pagos = SubElement(inf, 'pagos')
    pago = SubElement(pagos, 'pago')
    _t(pago, 'formaPago', getattr(factura, 'payment_method', '01') or '01')     # 01 = sin utilizaciÃ³n del sistema financiero
    _t(pago, 'total', str(total))
    _t(pago, 'plazo', '0')
    _t(pago, 'unidadTiempo', 'dias')

    # â”€â”€ detalles â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    detalles = SubElement(root, 'detalles')
    for item in factura.items:
        tarifa_item = str(getattr(item, 'tarifa_iva', '15'))
        codigo_pct_item = _TARIFA_A_CODIGO.get(tarifa_item, '2')
        subtotal_item = item.subtotal.quantize(Decimal('0.01'))
        iva_item = (item.subtotal * Decimal(tarifa_item) / 100).quantize(Decimal('0.01'))

        det = SubElement(detalles, 'detalle')
        _t(det, 'codigoPrincipal', item.codigo_principal or '001')
        if item.codigo_auxiliar:
            _t(det, 'codigoAuxiliar', item.codigo_auxiliar)
        _t(det, 'descripcion', item.descripcion)
        _t(det, 'cantidad', str(item.cantidad.quantize(Decimal('0.000000'))))
        _t(det, 'precioUnitario', str(item.precio_unitario.quantize(Decimal('0.000000'))))
        _t(det, 'discount', '0.00')
        _t(det, 'precioTotalSinImpuesto', str(subtotal_item))
        impuestos = SubElement(det, 'impuestos')
        imp = SubElement(impuestos, 'impuesto')
        _t(imp, 'codigo', '2')
        _t(imp, 'codigoPorcentaje', codigo_pct_item)
        _t(imp, 'tarifa', tarifa_item)
        _t(imp, 'baseImponible', str(subtotal_item))
        _t(imp, 'valor', str(iva_item))

    # â”€â”€ infoAdicional â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    cliente_email = getattr(factura, 'cliente_email', getattr(factura, 'client_email', ''))
    if cliente_email:
        ia = SubElement(root, 'infoAdicional')
        campo = SubElement(ia, 'campoAdicional', nombre='email')
        campo.text = str(cliente_email)

    xml_str = tostring(root, encoding='unicode')
    return '<?xml version="1.0" encoding="UTF-8"?>' + xml_str


def _t(parent: Element, tag: str, text: str):
    el = SubElement(parent, tag)
    el.text = text
    return el

