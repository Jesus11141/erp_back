"""
Módulo de Generación de Anexo Transaccional Simplificado (ATS) en XML
Cumple con la especificación técnica del Servicio de Rentas Internas (SRI) del Ecuador y DIMM Anexos.
"""
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
import re
from typing import List, Dict, Any, Optional
import xml.etree.ElementTree as ET
from xml.dom import minidom

from django.db.models import Sum
from modules.accounting.infrastructure.django_models import SriCredentialModel, PurchaseInvoiceModel
from modules.compras.infrastructure.django_models import FacturaCompraModel
from modules.tax_documents.invoicing.infrastructure.persistence.django_models import InvoiceModel
from modules.tenants.infrastructure.django_models import TenantModel


def sanitize_text(val: Optional[str]) -> str:
    """Elimina caracteres de control y limpia texto para XML legal."""
    if not val:
        return ""
    cleaned = str(val).strip()
    # Eliminar saltos de línea y tabulaciones excesivas
    cleaned = re.sub(r'[\r\n\t]+', ' ', cleaned)
    # Reemplazar caracteres no permitidos en XML
    cleaned = re.sub(r'[^\x20-\x7E\xA0-\xFF]', '', cleaned)
    return cleaned


def format_decimal(val: Any) -> str:
    """Formatea cualquier valor numérico a cadena con 2 decimales redondeado."""
    if val is None:
        return "0.00"
    try:
        d = Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return f"{d:.2f}"
    except Exception:
        return "0.00"


def split_invoice_number(doc_num: str) -> tuple[str, str, str]:
    """
    Separa un número de comprobante tipo '001-001-000000001'
    en (establecimiento, punto_emision, secuencial).
    """
    if not doc_num:
        return "001", "001", "000000001"
    parts = re.split(r'[-/.]', doc_num.strip())
    if len(parts) >= 3:
        estab = parts[0].zfill(3)[:3]
        pto = parts[1].zfill(3)[:3]
        sec = parts[2].zfill(9)[:9]
        return estab, pto, sec
    elif len(parts) == 1 and len(parts[0]) == 15:
        return parts[0][:3], parts[0][3:6], parts[0][6:].zfill(9)
    # Por defecto
    clean_digits = re.sub(r'\D', '', doc_num)
    if len(clean_digits) >= 15:
        return clean_digits[:3], clean_digits[3:6], clean_digits[6:15]
    return "001", "001", clean_digits.zfill(9)[:9] if clean_digits else "000000001"


def get_supplier_id_type(ident: str) -> str:
    """
    Determina el código de tipo de identificación del proveedor según el SRI:
    '01': RUC (13 dígitos)
    '02': Cédula (10 dígitos)
    '03': Pasaporte
    """
    cleaned = re.sub(r'\D', '', str(ident or ''))
    if len(cleaned) == 13:
        return "01"
    if len(cleaned) == 10:
        return "02"
    return "03"


def get_supplier_tipo_prov(ident: str) -> str:
    """
    Determina el tipo de proveedor según el SRI:
    '01': Persona Natural (Cédula o RUC con 3er dígito < 6)
    '02': Sociedad / Jurídica (RUC con 3er dígito 9 o 6)
    """
    cleaned = re.sub(r'\D', '', str(ident or ''))
    if len(cleaned) == 10:
        return "01"
    if len(cleaned) == 13:
        third_digit = cleaned[2]
        if third_digit in ('9', '6'):
            return "02"
        return "01"
    return "02"


def get_client_id_type(id_type: str, ident: str) -> str:
    """
    Mapea el tipo de identificación del cliente según la codificación del ATS SRI:
    '04': RUC
    '05': Cédula
    '06': Pasaporte / Identificación Exterior
    '07': Consumidor Final
    """
    cleaned = str(ident or '').strip()
    if cleaned in ('9999999999999', '9999999999'):
        return "07"
    if id_type in ('04', '05', '06', '07'):
        return id_type
    
    digits = re.sub(r'\D', '', cleaned)
    if len(digits) == 13:
        return "04"
    if len(digits) == 10:
        return "05"
    return "06"


def map_payment_method(code: Optional[str]) -> str:
    """
    Normaliza el código SRI de forma de pago.
    01: Sin utilización del sistema financiero (Efectivo)
    20: Otros con utilización del sistema financiero (Transferencia/Cheque/Tarjeta)
    """
    c = str(code or '').strip()
    if c in ('01', '16', '17', '18', '19', '20', '21'):
        return c
    if c.lower() in ('efectivo', 'cash', 'contado'):
        return "01"
    return "20"


@dataclass
class AtsPeriod:
    year: int
    month: int

    def __post_init__(self):
        if not (2000 <= self.year <= 2100):
            raise ValueError(f"Año inválido: {self.year}")
        if not (1 <= self.month <= 12):
            raise ValueError(f"Mes inválido: {self.month}")


@dataclass
class AtsInformante:
    ruc: str
    razon_social: str
    num_estab: str = "001"


class GetAtsSummaryUseCase:
    """Consulta y calcula las métricas previas para la interfaz de usuario."""

    def execute(self, tenant_id: int, year: int, month: int) -> Dict[str, Any]:
        period = AtsPeriod(year=year, month=month)
        
        # 1. Datos del Informante
        cred = SriCredentialModel.objects.filter(tenant_id=tenant_id).first()
        tenant = TenantModel.objects.filter(id=tenant_id).first()
        
        ruc = cred.ruc if cred and cred.ruc else (tenant.ruc if tenant and tenant.ruc else "")
        razon_social = cred.company_name if cred and cred.company_name else (tenant.name if tenant else "Empresa")
        
        # 2. Facturas de Compra (Registradas)
        compras_qs = FacturaCompraModel.objects.filter(
            tenant_id=tenant_id,
            date__year=period.year,
            date__month=period.month,
            status='registrada'
        )
        
        comp_count = compras_qs.count()
        comp_sub0 = Decimal('0.00')
        comp_sub_iva = Decimal('0.00')
        comp_vat = Decimal('0.00')
        comp_total = Decimal('0.00')
        
        warnings = []
        if not ruc or len(re.sub(r'\D', '', ruc)) != 13:
            warnings.append("El RUC del emisor no está configurado o no tiene 13 dígitos.")

        for c in compras_qs:
            comp_sub0 += Decimal(str(c.subtotal_0 or 0))
            comp_sub_iva += Decimal(str(c.subtotal_iva or 0))
            comp_vat += Decimal(str(c.vat or 0))
            comp_total += Decimal(str(c.total or 0))
            
            if not c.access_key and not c.invoice_number:
                warnings.append(f"Factura de compra ID #{c.id} carece de número y clave de acceso.")

        # Opcional: Revisar también PurchaseInvoiceModel si no se usó FacturaCompraModel
        if comp_count == 0:
            pi_qs = PurchaseInvoiceModel.objects.filter(
                tenant_id=tenant_id,
                emission_date__year=period.year,
                emission_date__month=period.month
            )
            if pi_qs.exists():
                comp_count = pi_qs.count()
                for p in pi_qs:
                    comp_sub0 += Decimal(str(p.base_0 or 0))
                    comp_sub_iva += Decimal(str(p.base_12 or 0))
                    comp_vat += Decimal(str(p.iva_amount or 0))
                    comp_total += Decimal(str(p.total_amount or 0))

        # 3. Facturas de Venta Autorizadas
        ventas_qs = InvoiceModel.objects.filter(
            tenant_id=tenant_id,
            date__year=period.year,
            date__month=period.month,
            status='authorized'
        ).prefetch_related('items')
        
        ventas_count = ventas_qs.count()
        ventas_sub0 = Decimal('0.00')
        ventas_sub_iva = Decimal('0.00')
        ventas_vat = Decimal('0.00')
        ventas_total = Decimal('0.00')

        for inv in ventas_qs:
            # Calcular subtotales desde los items
            inv_sub0 = Decimal('0.00')
            inv_sub_iva = Decimal('0.00')
            inv_items = inv.items.all()
            if inv_items:
                for it in inv_items:
                    qty = Decimal(str(it.quantity or 0))
                    price = Decimal(str(it.unit_price or 0))
                    disc = Decimal(str(it.discount or 0))
                    base = qty * price
                    sub = base - (base * disc / Decimal('100'))
                    rate = str(it.vat_rate or '15').strip()
                    if rate in ('0', 'no_objeto', 'exento'):
                        inv_sub0 += sub
                    else:
                        inv_sub_iva += sub
            else:
                # Si no hay items, usar vat del modelo
                inv_sub_iva = Decimal('0.00')

            inv_vat = (inv_sub_iva * (Decimal(str(inv.vat or 15)) / Decimal('100'))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            
            ventas_sub0 += inv_sub0
            ventas_sub_iva += inv_sub_iva
            ventas_vat += inv_vat
            ventas_total += (inv_sub0 + inv_sub_iva + inv_vat)

        # 4. Comprobantes Anulados
        anulados_qs = InvoiceModel.objects.filter(
            tenant_id=tenant_id,
            date__year=period.year,
            date__month=period.month,
            status__in=['canceled', 'cancelled', 'void']
        )
        anulados_count = anulados_qs.count()

        return {
            'period': {
                'year': period.year,
                'month': period.month,
                'formatted': f"{period.month:02d}/{period.year}"
            },
            'informante': {
                'ruc': ruc,
                'razon_social': razon_social
            },
            'purchases': {
                'count': comp_count,
                'subtotal_0': float(comp_sub0),
                'subtotal_iva': float(comp_sub_iva),
                'vat': float(comp_vat),
                'total': float(comp_total)
            },
            'sales': {
                'count': ventas_count,
                'subtotal_0': float(ventas_sub0),
                'subtotal_iva': float(ventas_sub_iva),
                'vat': float(ventas_vat),
                'total': float(ventas_total),
                'total_sin_iva': float(ventas_sub0 + ventas_sub_iva)
            },
            'cancelled': {
                'count': anulados_count
            },
            'warnings': warnings[:10]  # Primeras 10 advertencias
        }


class GenerateAtsXmlUseCase:
    """Genera el contenido XML del ATS según las normas del SRI."""

    def execute(self, tenant_id: int, year: int, month: int) -> str:
        period = AtsPeriod(year=year, month=month)
        
        # 1. Informante
        cred = SriCredentialModel.objects.filter(tenant_id=tenant_id).first()
        tenant = TenantModel.objects.filter(id=tenant_id).first()
        
        raw_ruc = cred.ruc if cred and cred.ruc else (tenant.ruc if tenant and tenant.ruc else "0000000000001")
        ruc = re.sub(r'\D', '', str(raw_ruc)).zfill(13)[:13]
        razon_social = sanitize_text(cred.company_name if cred and cred.company_name else (tenant.name if tenant else "Empresa"))
        
        # 2. Consultar Ventas del Mes
        ventas_qs = InvoiceModel.objects.filter(
            tenant_id=tenant_id,
            date__year=period.year,
            date__month=period.month,
            status='authorized'
        ).prefetch_related('items').order_by('date', 'id')

        # Agrupar ventas por cliente y tipo de comprobante
        ventas_by_client: Dict[str, Dict[str, Any]] = {}
        ventas_by_estab: Dict[str, Decimal] = {}
        total_ventas_periodo = Decimal('0.00')

        for inv in ventas_qs:
            estab, pto, sec = split_invoice_number(inv.number)
            client_ident = sanitize_text(inv.client_identification) or "9999999999999"
            tp_id = get_client_id_type(inv.client_id_type, client_ident)
            
            # Calcular base 0 e IVA de la factura
            inv_sub0 = Decimal('0.00')
            inv_sub_iva = Decimal('0.00')
            inv_items = inv.items.all()
            if inv_items:
                for it in inv_items:
                    qty = Decimal(str(it.quantity or 0))
                    price = Decimal(str(it.unit_price or 0))
                    disc = Decimal(str(it.discount or 0))
                    base = qty * price
                    sub = base - (base * disc / Decimal('100'))
                    rate = str(it.vat_rate or '15').strip()
                    if rate in ('0', 'no_objeto', 'exento'):
                        inv_sub0 += sub
                    else:
                        inv_sub_iva += sub
            else:
                inv_sub_iva = Decimal('0.00')

            inv_vat = (inv_sub_iva * (Decimal(str(inv.vat or 15)) / Decimal('100'))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            inv_total_sin_iva = inv_sub0 + inv_sub_iva

            total_ventas_periodo += inv_total_sin_iva
            ventas_by_estab[estab] = ventas_by_estab.get(estab, Decimal('0.00')) + inv_total_sin_iva

            client_key = f"{tp_id}_{client_ident}"
            if client_key not in ventas_by_client:
                ventas_by_client[client_key] = {
                    'tpIdCliente': tp_id,
                    'idCliente': client_ident,
                    'count': 0,
                    'baseImponible': Decimal('0.00'),
                    'baseImpGrav': Decimal('0.00'),
                    'montoIva': Decimal('0.00'),
                    'formaPago': map_payment_method(inv.payment_method)
                }

            ventas_by_client[client_key]['count'] += 1
            ventas_by_client[client_key]['baseImponible'] += inv_sub0
            ventas_by_client[client_key]['baseImpGrav'] += inv_sub_iva
            ventas_by_client[client_key]['montoIva'] += inv_vat

        # Número total de establecimientos
        num_estabs = max(len(ventas_by_estab), 1)

        # 3. Construir Árbol XML <iva>
        root = ET.Element("iva")
        
        # Cabecera
        ET.SubElement(root, "TipoIDInformante").text = "R"
        ET.SubElement(root, "IdInformante").text = ruc
        ET.SubElement(root, "razonSocial").text = razon_social
        ET.SubElement(root, "Anio").text = str(period.year)
        ET.SubElement(root, "Mes").text = f"{period.month:02d}"
        ET.SubElement(root, "numEstabRuc").text = f"{num_estabs:03d}"
        ET.SubElement(root, "totalVentas").text = format_decimal(total_ventas_periodo)
        ET.SubElement(root, "codigoOperativo").text = "IVA"

        # 4. Sección <compras>
        compras_qs = FacturaCompraModel.objects.filter(
            tenant_id=tenant_id,
            date__year=period.year,
            date__month=period.month,
            status='registrada'
        ).select_related('supplier').order_by('date', 'id')

        # Fallback a PurchaseInvoiceModel si FacturaCompraModel está vacío
        has_purchases = compras_qs.exists()
        pi_qs = []
        if not has_purchases:
            pi_qs = list(PurchaseInvoiceModel.objects.filter(
                tenant_id=tenant_id,
                emission_date__year=period.year,
                emission_date__month=period.month
            ).select_related('supplier').order_by('emission_date', 'id'))
            has_purchases = len(pi_qs) > 0

        if has_purchases:
            compras_elem = ET.SubElement(root, "compras")
            
            if compras_qs.exists():
                for comp in compras_qs:
                    det = ET.SubElement(compras_elem, "detalleCompras")
                    ET.SubElement(det, "codSustento").text = "01"
                    
                    supp_id = comp.supplier.identification if comp.supplier else "9999999999999"
                    supp_name = comp.supplier.business_name if comp.supplier else comp.supplier_name
                    tp_prov = get_supplier_id_type(supp_id)
                    
                    ET.SubElement(det, "tpIdProv").text = tp_prov
                    ET.SubElement(det, "idProv").text = supp_id
                    ET.SubElement(det, "tipoComprobante").text = "01"
                    ET.SubElement(det, "tipoProv").text = get_supplier_tipo_prov(supp_id)
                    ET.SubElement(det, "denominacionProv").text = sanitize_text(supp_name)
                    ET.SubElement(det, "parteRel").text = "NO"
                    
                    reg_date = comp.registration_date or comp.date
                    ET.SubElement(det, "fechaRegistro").text = reg_date.strftime("%d/%m/%Y")
                    
                    estab, pto, sec = split_invoice_number(comp.invoice_number)
                    ET.SubElement(det, "establecimiento").text = estab
                    ET.SubElement(det, "puntoEmision").text = pto
                    ET.SubElement(det, "secuencial").text = sec
                    ET.SubElement(det, "fechaEmision").text = comp.date.strftime("%d/%m/%Y")
                    
                    auth = comp.access_key.strip() if comp.access_key else "0" * 37
                    ET.SubElement(det, "autorizacion").text = auth
                    
                    ET.SubElement(det, "baseNoGraIva").text = "0.00"
                    ET.SubElement(det, "baseImponible").text = format_decimal(comp.subtotal_0)
                    ET.SubElement(det, "baseImpGrav").text = format_decimal(comp.subtotal_iva)
                    ET.SubElement(det, "baseImpExe").text = "0.00"
                    ET.SubElement(det, "montoIce").text = "0.00"
                    ET.SubElement(det, "montoIva").text = format_decimal(comp.vat)
                    
                    # Retenciones SRI
                    ET.SubElement(det, "valRetBien10").text = "0.00"
                    ET.SubElement(det, "valRetServ20").text = "0.00"
                    ET.SubElement(det, "valorRetBienes").text = "0.00"
                    ET.SubElement(det, "valRetServ50").text = "0.00"
                    ET.SubElement(det, "valorRetServicios").text = "0.00"
                    ET.SubElement(det, "valRetServ100").text = "0.00"
                    ET.SubElement(det, "totbasesImpReemb").text = "0.00"
                    
                    # Pago Exterior
                    pago_ext = ET.SubElement(det, "pagoExterior")
                    ET.SubElement(pago_ext, "pagoLocExt").text = "01"
                    ET.SubElement(pago_ext, "paisEfecPago").text = "NA"
                    ET.SubElement(pago_ext, "aplicConvDobTrib").text = "NA"
                    ET.SubElement(pago_ext, "pagExtSujRetNorLeg").text = "NA"
                    
                    # Formas de Pago
                    formas = ET.SubElement(det, "formasDePago")
                    f_pago = "01" if comp.payment_condition == "contado" else "20"
                    ET.SubElement(formas, "formaPago").text = f_pago
            else:
                for pi in pi_qs:
                    det = ET.SubElement(compras_elem, "detalleCompras")
                    ET.SubElement(det, "codSustento").text = "01"
                    supp_id = pi.supplier.ruc if pi.supplier else "9999999999999"
                    supp_name = pi.supplier.business_name if pi.supplier else "Proveedor"
                    
                    ET.SubElement(det, "tpIdProv").text = get_supplier_id_type(supp_id)
                    ET.SubElement(det, "idProv").text = supp_id
                    ET.SubElement(det, "tipoComprobante").text = "01"
                    ET.SubElement(det, "tipoProv").text = get_supplier_tipo_prov(supp_id)
                    ET.SubElement(det, "denominacionProv").text = sanitize_text(supp_name)
                    ET.SubElement(det, "parteRel").text = "NO"
                    ET.SubElement(det, "fechaRegistro").text = pi.emission_date.strftime("%d/%m/%Y")
                    
                    estab, pto, sec = split_invoice_number(pi.document_number)
                    ET.SubElement(det, "establecimiento").text = estab
                    ET.SubElement(det, "puntoEmision").text = pto
                    ET.SubElement(det, "secuencial").text = sec
                    ET.SubElement(det, "fechaEmision").text = pi.emission_date.strftime("%d/%m/%Y")
                    
                    ET.SubElement(det, "autorizacion").text = pi.access_key or ("0" * 37)
                    ET.SubElement(det, "baseNoGraIva").text = "0.00"
                    ET.SubElement(det, "baseImponible").text = format_decimal(pi.base_0)
                    ET.SubElement(det, "baseImpGrav").text = format_decimal(pi.base_12)
                    ET.SubElement(det, "baseImpExe").text = "0.00"
                    ET.SubElement(det, "montoIce").text = "0.00"
                    ET.SubElement(det, "montoIva").text = format_decimal(pi.iva_amount)
                    ET.SubElement(det, "valRetBien10").text = "0.00"
                    ET.SubElement(det, "valRetServ20").text = "0.00"
                    ET.SubElement(det, "valorRetBienes").text = "0.00"
                    ET.SubElement(det, "valRetServ50").text = "0.00"
                    ET.SubElement(det, "valorRetServicios").text = "0.00"
                    ET.SubElement(det, "valRetServ100").text = "0.00"
                    ET.SubElement(det, "totbasesImpReemb").text = "0.00"
                    
                    pago_ext = ET.SubElement(det, "pagoExterior")
                    ET.SubElement(pago_ext, "pagoLocExt").text = "01"
                    ET.SubElement(pago_ext, "paisEfecPago").text = "NA"
                    ET.SubElement(pago_ext, "aplicConvDobTrib").text = "NA"
                    ET.SubElement(pago_ext, "pagExtSujRetNorLeg").text = "NA"
                    
                    formas = ET.SubElement(det, "formasDePago")
                    ET.SubElement(formas, "formaPago").text = "01"

        # 5. Sección <ventas>
        if ventas_by_client:
            ventas_elem = ET.SubElement(root, "ventas")
            for c_data in ventas_by_client.values():
                det = ET.SubElement(ventas_elem, "detalleVentas")
                ET.SubElement(det, "tpIdCliente").text = c_data['tpIdCliente']
                ET.SubElement(det, "idCliente").text = c_data['idCliente']
                ET.SubElement(det, "parteRelVtas").text = "NO"
                ET.SubElement(det, "tipoComprobante").text = "18"
                ET.SubElement(det, "tipoEmision").text = "E"
                ET.SubElement(det, "numeroComprobantes").text = str(c_data['count'])
                ET.SubElement(det, "baseNoGraIva").text = "0.00"
                ET.SubElement(det, "baseImponible").text = format_decimal(c_data['baseImponible'])
                ET.SubElement(det, "baseImpGrav").text = format_decimal(c_data['baseImpGrav'])
                ET.SubElement(det, "montoIva").text = format_decimal(c_data['montoIva'])
                ET.SubElement(det, "montoIce").text = "0.00"
                ET.SubElement(det, "valorRetIva").text = "0.00"
                ET.SubElement(det, "valorRetRenta").text = "0.00"
                
                formas = ET.SubElement(det, "formasDePago")
                ET.SubElement(formas, "formaPago").text = c_data['formaPago']

        # 6. Sección <ventasEstablecimiento>
        ventas_estab_elem = ET.SubElement(root, "ventasEstablecimiento")
        if ventas_by_estab:
            for cod_estab, monto_estab in ventas_by_estab.items():
                v_est = ET.SubElement(ventas_estab_elem, "ventaEst")
                ET.SubElement(v_est, "codEstab").text = cod_estab
                ET.SubElement(v_est, "ventasEstab").text = format_decimal(monto_estab)
                ET.SubElement(v_est, "ivaComp").text = "0.00"
        else:
            v_est = ET.SubElement(ventas_estab_elem, "ventaEst")
            ET.SubElement(v_est, "codEstab").text = "001"
            ET.SubElement(v_est, "ventasEstab").text = "0.00"
            ET.SubElement(v_est, "ivaComp").text = "0.00"

        # 7. Sección <anulados>
        anulados_qs = InvoiceModel.objects.filter(
            tenant_id=tenant_id,
            date__year=period.year,
            date__month=period.month,
            status__in=['canceled', 'cancelled', 'void']
        ).order_by('id')

        if anulados_qs.exists():
            anulados_elem = ET.SubElement(root, "anulados")
            for an in anulados_qs:
                det = ET.SubElement(anulados_elem, "detalleAnulados")
                ET.SubElement(det, "tipoComprobante").text = "01"
                estab, pto, sec = split_invoice_number(an.number)
                ET.SubElement(det, "establecimiento").text = estab
                ET.SubElement(det, "puntoEmision").text = pto
                ET.SubElement(det, "secuencialInicio").text = sec
                ET.SubElement(det, "secuencialFin").text = sec
                auth = an.access_key or an.authorization_number or ("0" * 37)
                ET.SubElement(det, "autorizacion").text = auth

        # Formatear e Indentar XML con declaración UTF-8
        rough_string = ET.tostring(root, encoding="utf-8")
        parsed = minidom.parseString(rough_string)
        pretty_xml = parsed.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")
        
        # Asegurar declaración XML estándar
        lines = [l for l in pretty_xml.splitlines() if l.strip()]
        return "\n".join(lines)
