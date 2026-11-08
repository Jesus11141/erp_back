"""
XML Comprobante de Retención Electrónica SRI Ecuador
Tipo de comprobante: 07
Ficha Técnica: Comprobantes Electrónicos versión 2.0.0
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
    Genera el XML de Comprobante de Retención electrónico SRI Ecuador (v2.0.0).
    retencion: instancia de Withholding (entidad dominio o modelo)
    emisor: dict con ruc, razon_social, direccion, establecimiento, punto_emision, etc.
    """
    ret_date = getattr(retencion, 'date', getattr(retencion, 'fecha', None))
    fecha_str = ret_date.strftime('%d/%m/%Y') if ret_date else ''

    access_key = getattr(retencion, 'access_key', getattr(retencion, 'clave_acceso', ''))
    number = getattr(retencion, 'number', getattr(retencion, 'numero', '001-001-000000001'))
    env = str(getattr(retencion, 'environment', '1'))
    supplier_id_type = getattr(retencion, 'supplier_id_type', getattr(retencion, 'proveedor_tipo_id', '04'))
    supplier_name = getattr(retencion, 'supplier', getattr(retencion, 'proveedor', ''))
    supplier_id = getattr(retencion, 'supplier_identification', getattr(retencion, 'proveedor_identificacion', ''))
    fiscal_period = getattr(retencion, 'fiscal_period', getattr(retencion, 'periodo_fiscal', ''))
    origin_invoice = getattr(retencion, 'origin_invoice_number', getattr(retencion, 'factura_origen_numero', ''))

    root = Element('comprobanteRetencion', id='comprobante', version='2.0.0')

    # infoTributaria
    it = SubElement(root, 'infoTributaria')
    _t(it, 'ambiente', env)
    _t(it, 'tipoEmision', '1')
    _t(it, 'razonSocial', emisor['razon_social'])
    _t(it, 'nombreComercial', emisor.get('nombre_comercial', emisor['razon_social']))
    _t(it, 'ruc', emisor['ruc'])
    _t(it, 'claveAcceso', access_key)
    _t(it, 'codDoc', '07')
    _t(it, 'estab', emisor.get('establecimiento', '001'))
    _t(it, 'ptoEmi', emisor.get('punto_emision', '001'))
    _t(it, 'secuencial', number.split('-')[-1].zfill(9))
    _t(it, 'dirMatriz', emisor['direccion'])

    # infoCompRetencion
    icr = SubElement(root, 'infoCompRetencion')
    _t(icr, 'fechaEmision', fecha_str)
    _t(icr, 'dirEstablecimiento', emisor['direccion'])
    if emisor.get('contribuyente_especial'):
        _t(icr, 'contribuyenteEspecial', emisor['contribuyente_especial'])
    _t(icr, 'obligadoContabilidad', emisor.get('obligado_contabilidad', 'NO'))
    _t(icr, 'tipoIdentificacionSujetoRetenido', supplier_id_type)
    _t(icr, 'razonSocialSujetoRetenido', supplier_name)
    _t(icr, 'identificacionSujetoRetenido', supplier_id)
    _t(icr, 'periodoFiscal', fiscal_period)

    # impuestos
    impuestos_el = SubElement(root, 'impuestos')
    for item in retencion.items:
        imp = SubElement(impuestos_el, 'impuesto')
        # código: 1=Renta, 2=IVA, 6=ISD
        t_code = str(getattr(item, 'type_code', getattr(item, 'codigo_tipo', '1')))
        w_code = str(getattr(item, 'withholding_code', getattr(item, 'codigo_retencion', '303')))
        tax_base = Decimal(str(getattr(item, 'tax_base', getattr(item, 'base_imponible', 0))))
        pct = Decimal(str(getattr(item, 'percentage', getattr(item, 'porcentaje', 0))))
        val_ret = getattr(item, 'withheld_value', getattr(item, 'valor_retenido', None))
        if val_ret is None:
            val_ret = (tax_base * pct / Decimal('100')).quantize(Decimal('0.01'))
        else:
            val_ret = Decimal(str(val_ret)).quantize(Decimal('0.01'))

        _t(imp, 'codigo', t_code)
        _t(imp, 'codigoRetencion', w_code)
        _t(imp, 'baseImponible', f"{tax_base.quantize(Decimal('0.01')):.2f}")
        _t(imp, 'porcentajeRetener', f"{pct:.2f}")
        _t(imp, 'valorRetenido', f"{val_ret:.2f}")
        _t(imp, 'codDocSustento', '01')     # 01 = factura
        _t(imp, 'numDocSustento', origin_invoice)
        _t(imp, 'fechaEmisionDocSustento', fecha_str)

    xml_str = tostring(root, encoding='unicode')
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str


def _t(parent: Element, tag: str, text: str):
    el = SubElement(parent, tag)
    el.text = str(text or '')
    return el
