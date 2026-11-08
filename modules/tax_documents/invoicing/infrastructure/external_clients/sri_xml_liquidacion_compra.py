"""
Generador de XML para Liquidación de Compra de Bienes y Prestación de Servicios SRI Ecuador
Tipo de comprobante: 03
Ficha Técnica: Comprobantes Electrónicos versión 1.1.0
"""
import random
from datetime import datetime, date
from decimal import Decimal
from collections import defaultdict
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

_TARIFA_A_CODIGO = {
    '0':  '0',   # 0%
    '5':  '5',   # 5% (construcción)
    '15': '2',   # 15% (vigente)
    '12': '2',   # 12% (histórico)
}


def generate_access_key_liquidacion(
    fecha: str,
    ruc: str,
    environment: str,
    serie: str,
    secuencial: str,
    tipo_emision: str = '1'
) -> str:
    """
    Genera la clave de acceso de 49 dígitos para Liquidación de Compra (tipo 03).
    fecha: DD/MM/YYYY
    """
    fecha_str = fecha.replace('/', '')
    tipo_comprobante = '03'
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


def generate_xml_liquidacion_compra(liquidacion, emisor: dict) -> str:
    """
    Genera el XML de Liquidación de Compra (v1.1.0) compatible con SRI Ecuador.
    """
    root = Element('liquidacionCompra', id='comprobante', version='1.1.0')

    doc_date = getattr(liquidacion, 'date', date.today())
    fecha_str = _fmt_date(doc_date)

    access_key = getattr(liquidacion, 'access_key', '')
    number = getattr(liquidacion, 'number', '001-001-000000001')
    parts = number.split('-')
    estab = parts[0] if len(parts) > 0 else '001'
    pto_emi = parts[1] if len(parts) > 1 else '001'
    secuencial = parts[2] if len(parts) > 2 else '000000001'

    env = str(getattr(liquidacion, 'environment', emisor.get('environment', '1')))

    # 1. infoTributaria
    it = SubElement(root, 'infoTributaria')
    _t(it, 'ambiente', env)
    _t(it, 'tipoEmision', '1')
    _t(it, 'razonSocial', emisor.get('razon_social', ''))
    _t(it, 'nombreComercial', emisor.get('nombre_comercial') or emisor.get('razon_social', ''))
    _t(it, 'ruc', emisor.get('ruc', ''))
    _t(it, 'claveAcceso', access_key)
    _t(it, 'codDoc', '03')
    _t(it, 'estab', estab)
    _t(it, 'ptoEmi', pto_emi)
    _t(it, 'secuencial', secuencial.zfill(9))
    _t(it, 'dirMatriz', emisor.get('direccion', ''))

    # Agrupar impuestos por tarifa
    impuestos_por_tarifa = defaultdict(lambda: {'base': Decimal('0.00'), 'valor': Decimal('0.00')})
    total_sin_impuestos = Decimal('0.00')
    total_descuento = Decimal('0.00')

    items = getattr(liquidacion, 'items', [])
    for item in items:
        qty = Decimal(str(getattr(item, 'quantity', 1)))
        price = Decimal(str(getattr(item, 'unit_price', 0)))
        disc = Decimal(str(getattr(item, 'discount', 0)))
        vat_rate_str = str(getattr(item, 'vat_rate', '15'))

        base = (qty * price) - disc
        total_sin_impuestos += base
        total_descuento += disc

        vat_pct = Decimal(vat_rate_str) / Decimal('100')
        vat_val = (base * vat_pct).quantize(Decimal('0.01'))

        cod_porcentaje = _TARIFA_A_CODIGO.get(vat_rate_str, '2')
        impuestos_por_tarifa[(cod_porcentaje, vat_rate_str)]['base'] += base
        impuestos_por_tarifa[(cod_porcentaje, vat_rate_str)]['valor'] += vat_val

    total_iva = sum(v['valor'] for v in impuestos_por_tarifa.values())
    importe_total = (total_sin_impuestos + total_iva).quantize(Decimal('0.01'))

    # 2. infoLiquidacionCompra
    ilc = SubElement(root, 'infoLiquidacionCompra')
    _t(ilc, 'fechaEmision', fecha_str)
    _t(ilc, 'dirEstablecimiento', emisor.get('direccion', ''))
    _t(ilc, 'obligadoContabilidad', emisor.get('obligado_contabilidad', 'NO'))
    _t(ilc, 'tipoIdentificacionProveedor', getattr(liquidacion, 'supplier_id_type', '05'))
    _t(ilc, 'razonSocialProveedor', getattr(liquidacion, 'supplier', ''))
    _t(ilc, 'identificacionProveedor', getattr(liquidacion, 'supplier_identification', ''))
    _t(ilc, 'direccionProveedor', getattr(liquidacion, 'supplier_address', 'S/N') or 'S/N')
    _t(ilc, 'totalSinImpuestos', f"{total_sin_impuestos:.2f}")
    _t(ilc, 'totalDescuento', f"{total_descuento:.2f}")

    # totalConImpuestos
    tci = SubElement(ilc, 'totalConImpuestos')
    for (cod_porc, tarifa_str), datos in impuestos_por_tarifa.items():
        ti = SubElement(tci, 'totalImpuesto')
        _t(ti, 'codigo', '2')
        _t(ti, 'codigoPorcentaje', cod_porc)
        _t(ti, 'baseImponible', f"{datos['base']:.2f}")
        _t(ti, 'valor', f"{datos['valor']:.2f}")

    _t(ilc, 'importeTotal', f"{importe_total:.2f}")
    _t(ilc, 'moneda', 'DOLAR')

    # pagos
    pagos = SubElement(ilc, 'pagos')
    pago = SubElement(pagos, 'pago')
    _t(pago, 'formaPago', getattr(liquidacion, 'payment_method', '01') or '01')
    _t(pago, 'total', f"{importe_total:.2f}")

    # 3. detalles
    detalles = SubElement(root, 'detalles')
    for item in items:
        qty = Decimal(str(getattr(item, 'quantity', 1)))
        price = Decimal(str(getattr(item, 'unit_price', 0)))
        disc = Decimal(str(getattr(item, 'discount', 0)))
        vat_rate_str = str(getattr(item, 'vat_rate', '15'))
        base = (qty * price) - disc
        vat_pct = Decimal(vat_rate_str) / Decimal('100')
        vat_val = (base * vat_pct).quantize(Decimal('0.01'))
        cod_porc = _TARIFA_A_CODIGO.get(vat_rate_str, '2')

        d = SubElement(detalles, 'detalle')
        _t(d, 'codigoPrincipal', getattr(item, 'product_code', '') or '001')
        _t(d, 'descripcion', getattr(item, 'description', ''))
        _t(d, 'cantidad', f"{qty:.2f}")
        _t(d, 'precioUnitario', f"{price:.4f}")
        _t(d, 'descuento', f"{disc:.2f}")
        _t(d, 'precioTotalSinImpuesto', f"{base:.2f}")

        impuestos = SubElement(d, 'impuestos')
        impuesto = SubElement(impuestos, 'impuesto')
        _t(impuesto, 'codigo', '2')
        _t(impuesto, 'codigoPorcentaje', cod_porc)
        _t(impuesto, 'tarifa', vat_rate_str)
        _t(impuesto, 'baseImponible', f"{base:.2f}")
        _t(impuesto, 'valor', f"{vat_val:.2f}")

    # infoAdicional
    email = getattr(liquidacion, 'supplier_email', '')
    notes = getattr(liquidacion, 'notes', '')
    if email or notes:
        ia = SubElement(root, 'infoAdicional')
        if email:
            ca = SubElement(ia, 'campoAdicional', nombre='Email')
            ca.text = email
        if notes:
            ca = SubElement(ia, 'campoAdicional', nombre='Observaciones')
            ca.text = notes

    xml_bytes = tostring(root, encoding='utf-8')
    return minidom.parseString(xml_bytes).toprettyxml(indent='  ', encoding='utf-8').decode('utf-8')
