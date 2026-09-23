"""
Generador de PDF parametrizado.
Usa los parámetros del tenant para personalizar cada documento.
"""
from io import BytesIO
from decimal import Decimal
from typing import Optional
from datetime import date
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable, Image
from reportlab.platypus.flowables import KeepTogether
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT


def _color_hex(hex_str: str):
    """Convierte #RRGGBB a color ReportLab."""
    hex_str = hex_str.lstrip('#')
    r, g, b = tuple(int(hex_str[i:i+2], 16) / 255 for i in (0, 2, 4))
    return colors.Color(r, g, b)


def _config_desde_params(params: dict) -> dict:
    """Extrae configuración de los parámetros del tenant."""
    empresa_rfc = params.get('facturacion', {}).get('ruc_emisor', {}).get('value', '')
    if not empresa_rfc:
        empresa_rfc = params.get('general', {}).get('empresa_rfc', {}).get('value', '')

    return {
        'empresa_nombre':    params.get('general', {}).get('empresa_nombre', {}).get('value', ''),
        'empresa_rfc':       empresa_rfc,
        'empresa_direccion': params.get('general', {}).get('empresa_direccion', {}).get('value', ''),
        'empresa_telefono':  params.get('general', {}).get('empresa_telefono', {}).get('value', ''),
        'empresa_email':     params.get('general', {}).get('empresa_email', {}).get('value', ''),
        'moneda_simbolo':    params.get('general', {}).get('moneda_simbolo', {}).get('value', '$'),
        'pie_factura':       params.get('facturacion', {}).get('pie_factura', {}).get('value', 'Gracias por su compra'),
        'obligado_contabilidad': params.get('facturacion', {}).get('obligado_contabilidad', {}).get('value', 'NO'),
        'contribuyente_especial': params.get('facturacion', {}).get('contribuyente_especial', {}).get('value', ''),
        'primary_color':    '#1976D2',
        'secondary_color':  '#424242',
    }


def _obtener_logo_element(logo_url: str) -> Optional[Image]:
    """Resuelve la ruta física del logo y devuelve un elemento Image de ReportLab."""
    if not logo_url:
        return None
    from django.conf import settings
    import os
    try:
        rel_path = logo_url
        if rel_path.startswith(settings.MEDIA_URL):
            rel_path = rel_path[len(settings.MEDIA_URL):]
        path_disk = os.path.join(settings.MEDIA_ROOT, rel_path)
        if os.path.exists(path_disk):
            # Limitar tamaño máximo para el header
            return Image(path_disk, width=4.5*cm, height=2.2*cm, kind='bound')
    except Exception:
        pass
    return None


def generate_invoice_pdf(invoice: dict, params: dict, tenant: dict) -> bytes:
    """
    Genera PDF de factura en formato RIDE (estándar SRI Ecuador) con diseño moderno y elegante.
    """
    buffer = BytesIO()
    cfg = _config_desde_params(params)
    cfg['primary_color'] = tenant.get('primary_color', '#1976D2')
    cfg['empresa_nombre'] = cfg['empresa_nombre'] or tenant.get('name', 'Mi Empresa')

    primary_color = _color_hex(cfg['primary_color'])
    simbolo = cfg['moneda_simbolo']

    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=1.5*cm, leftMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    elementos = []

    # ESTILOS COMUNES
    estilo_normal = ParagraphStyle('normal', fontSize=8, fontName='Helvetica', leading=10, textColor=colors.HexColor('#334155'))
    estilo_bold = ParagraphStyle('bold', fontSize=8, fontName='Helvetica-Bold', leading=10, textColor=colors.HexColor('#1E293B'))
    estilo_bold_large = ParagraphStyle('bold_large', fontSize=12, fontName='Helvetica-Bold', leading=14, textColor=primary_color)
    estilo_title = ParagraphStyle('title', fontSize=12, fontName='Helvetica-Bold', leading=14, textColor=colors.HexColor('#0F172A'))
    estilo_white = ParagraphStyle('white', fontSize=8, fontName='Helvetica-Bold', leading=10, textColor=colors.white)
    
    # ── ENCABEZADO ────────────────────────────────────────────
    # Columna Izquierda
    col_izq = []
    logo_el = _obtener_logo_element(tenant.get('logo_url'))
    if logo_el:
        col_izq.append(logo_el)
        col_izq.append(Spacer(1, 0.5*cm))
        
    info_empresa = [
        [Paragraph(cfg['empresa_nombre'], estilo_bold_large)],
        [Spacer(1, 0.2*cm)],
        [Paragraph(f"<b>Dir. Matriz:</b> {cfg['empresa_direccion']}", estilo_normal)],
        [Paragraph(f"<b>Dir. Sucursal:</b> {cfg['empresa_direccion']}", estilo_normal)],
        [Spacer(1, 0.3*cm)],
    ]
    if cfg['contribuyente_especial']:
        info_empresa.append([Paragraph(f"<b>Contribuyente Especial Nro:</b> {cfg['contribuyente_especial']}", estilo_normal)])
    
    info_empresa.append([Paragraph(f"<b>OBLIGADO A LLEVAR CONTABILIDAD:</b> {cfg['obligado_contabilidad']}", estilo_normal)])
    
    tabla_empresa = Table(info_empresa, colWidths=[8.5*cm])
    tabla_empresa.setStyle(TableStyle([
        ('LINEBEFORE', (0,0), (-1,-1), 2.5, primary_color),
        ('PADDING', (0,0), (-1,-1), 8),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
    ]))
    col_izq.append(tabla_empresa)

    # Columna Derecha
    clave_acceso = invoice.get('access_key') or '1234567890123456789012345678901234567890123456789'
    auth_num = invoice.get('authorization_number') or clave_acceso
    fecha_auth = invoice.get('authorization_date') or 'PENDIENTE'
    estado = invoice.get('status', 'PENDIENTE').upper()
    
    col_der_flowables = [
        Paragraph(f"<b>R.U.C.:</b> &nbsp;&nbsp; {cfg['empresa_rfc']}", estilo_title),
        Spacer(1, 0.2*cm),
        Paragraph("F A C T U R A", ParagraphStyle('f', fontSize=18, fontName='Helvetica-Bold', leading=22, textColor=primary_color)),
        Spacer(1, 0.2*cm),
        Paragraph(f"<b>ESTADO SRI:</b> {estado}", estilo_normal),
        Spacer(1, 0.1*cm),
        Paragraph(f"<b>No.</b> &nbsp;&nbsp; {invoice.get('number', '')}", estilo_title),
        Spacer(1, 0.2*cm),
        Paragraph("<b>NÚMERO DE AUTORIZACIÓN:</b>", estilo_normal),
        Paragraph(f"{auth_num}", ParagraphStyle('a', fontSize=8, fontName='Helvetica', leading=12, textColor=colors.HexColor('#475569'))),
        Spacer(1, 0.2*cm),
        Table([
            [Paragraph("<b>FECHA Y HORA DE<br/>AUTORIZACIÓN:</b>", estilo_normal), Paragraph(f"{fecha_auth}", estilo_normal)]
        ], colWidths=[3.5*cm, 5.1*cm], style=[('PADDING', (0,0), (-1,-1), 0), ('VALIGN', (0,0), (-1,-1), 'MIDDLE')]),
        Spacer(1, 0.1*cm),
        Table([
            [Paragraph("<b>AMBIENTE:</b>", estilo_normal), Paragraph("PRODUCCION" if invoice.get('environment') == '2' else "PRUEBAS", estilo_normal)],
            [Paragraph("<b>EMISIÓN:</b>", estilo_normal), Paragraph("NORMAL", estilo_normal)]
        ], colWidths=[2.5*cm, 6.1*cm], style=[('PADDING', (0,0), (-1,-1), 0), ('VALIGN', (0,0), (-1,-1), 'MIDDLE')]),
        Spacer(1, 0.2*cm),
        Paragraph("<b>CLAVE DE ACCESO</b>", estilo_normal),
        Spacer(1, 0.1*cm)
    ]
    try:
        from reportlab.graphics.barcode import code128
        barcode = code128.Code128(clave_acceso, barHeight=30, barWidth=0.6)
        col_der_flowables.append(barcode)
    except Exception:
        pass
        
    col_der_flowables.append(Spacer(1, 0.1*cm))
    col_der_flowables.append(Paragraph(clave_acceso, ParagraphStyle('c', fontSize=7, fontName='Helvetica', alignment=TA_CENTER, textColor=colors.HexColor('#475569'))))

    tabla_sri = Table([[col_der_flowables]], colWidths=[9*cm])
    tabla_sri.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('PADDING', (0,0), (-1,-1), 10),
    ]))
    
    # Unir cabeceras
    tabla_encabezado = Table([[col_izq, tabla_sri]], colWidths=[9*cm, 9*cm])
    tabla_encabezado.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 0),
    ]))
    elementos.append(tabla_encabezado)
    elementos.append(Spacer(1, 0.4*cm))

    # ── DATOS CLIENTE ────────────────────────────────────────────
    cliente_info = [
        [Paragraph(f"<b>Razón Social / Nombres:</b> {invoice.get('client', '')}", estilo_normal),
         Paragraph(f"<b>Identificación:</b> {invoice.get('client_identification', '')}", estilo_normal)],
        [Paragraph(f"<b>Fecha de Emisión:</b> {invoice.get('date', '')}", estilo_normal),
         Paragraph(f"<b>Guía de Remisión:</b>", estilo_normal)],
        [Paragraph(f"<b>Dirección:</b> {invoice.get('client_address') or ''}", estilo_normal), '']
    ]
    tabla_cli = Table(cliente_info, colWidths=[11*cm, 7*cm])
    tabla_cli.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('PADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('SPAN', (0,2), (1,2)), # Span direccion
    ]))
    elementos.append(tabla_cli)
    elementos.append(Spacer(1, 0.4*cm))

    # ── TABLA DE ITEMS ───────────────────────────────────────────
    cabeceras = [
        Paragraph('<b>Cod. Principal</b>', estilo_white), 
        Paragraph('<b>Cant</b>', estilo_white), 
        Paragraph('<b>Descripción</b>', estilo_white), 
        Paragraph('<b>Precio<br/>Unitario</b>', ParagraphStyle('w_r', parent=estilo_white, alignment=TA_RIGHT)), 
        Paragraph('<b>Descuento</b>', ParagraphStyle('w_r', parent=estilo_white, alignment=TA_RIGHT)), 
        Paragraph('<b>Precio Total</b>', ParagraphStyle('w_r', parent=estilo_white, alignment=TA_RIGHT))
    ]
    filas = [cabeceras]
    
    subtotales_iva = {}
    total_descuento = Decimal('0.00')
    total_subtotal_bruto = Decimal('0.00')

    for idx, item in enumerate(invoice.get('items', []), 1):
        quantity = Decimal(str(item.get('quantity', 0)))
        precio = Decimal(str(item.get('unit_price', 0)))
        discount = Decimal(str(item.get('discount', 0)))
        vat_rate = str(item.get('vat_rate', '15'))
        
        base = quantity * precio
        desc_val = (base * discount / Decimal('100')).quantize(Decimal('0.01'))
        subtotal = base - desc_val
        
        total_descuento += desc_val
        total_subtotal_bruto += base
        subtotales_iva[vat_rate] = subtotales_iva.get(vat_rate, Decimal('0.00')) + subtotal

        filas.append([
            Paragraph(f"{idx}", estilo_normal), # Fake Cod Principal if none
            Paragraph(str(quantity), estilo_normal),
            Paragraph(item.get('description', ''), estilo_normal),
            Paragraph(f"{precio:,.2f}", ParagraphStyle('r', fontSize=8, alignment=TA_RIGHT, textColor=colors.HexColor('#334155'))),
            Paragraph(f"{desc_val:,.2f}", ParagraphStyle('r', fontSize=8, alignment=TA_RIGHT, textColor=colors.HexColor('#334155'))),
            Paragraph(f"{subtotal:,.2f}", ParagraphStyle('r', fontSize=8, alignment=TA_RIGHT, textColor=colors.HexColor('#334155'))),
        ])

    tabla_items = Table(filas, colWidths=[2.5*cm, 1.5*cm, 7.5*cm, 2.5*cm, 2*cm, 2*cm])
    tabla_items.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (1,0), (1,-1), 'CENTER'),
        ('ALIGN', (3,0), (-1,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 6),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
    ]))
    elementos.append(tabla_items)
    elementos.append(Spacer(1, 0.4*cm))

    # ── TOTALES Y ADICIONAL ────────────────────────────────────────
    # Información Adicional
    info_adic = []
    if invoice.get('client_email'):
        info_adic.append([Paragraph(f"<b>Email Cliente:</b> {invoice.get('client_email')}", estilo_normal)])
    if cfg['empresa_telefono']:
        info_adic.append([Paragraph(f"<b>Teléfono Empresa:</b> {cfg['empresa_telefono']}", estilo_normal)])
    info_adic.append([Paragraph(f"<b>Forma de Pago:</b> OTROS CON UTILIZACIÓN DEL SISTEMA FINANCIERO", estilo_normal)])

    tabla_adic_flow = []
    if info_adic:
        tabla_adic_header = Table([[Paragraph("<b>Información Adicional</b>", estilo_bold)]], colWidths=[9.5*cm])
        tabla_adic_header.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F1F5F9')),
            ('PADDING', (0,0), (-1,-1), 5),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ]))
        tabla_adic_flow.append(tabla_adic_header)
        
        tabla_adic_body = Table(info_adic, colWidths=[9.5*cm])
        tabla_adic_body.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0,0), (-1,-1), 5),
            ('LINEBELOW', (0,0), (-1,-2), 0.5, colors.HexColor('#F1F5F9')),
        ]))
        tabla_adic_flow.append(tabla_adic_body)
    
    # Totales
    datos_totales = []
    
    # Prepare standard fields
    base_15 = subtotales_iva.get('15', Decimal('0.00'))
    base_0 = subtotales_iva.get('0', Decimal('0.00'))
    base_no_obj = subtotales_iva.get('no_objeto', Decimal('0.00'))
    base_exento = subtotales_iva.get('exento', Decimal('0.00'))
    
    subtotal_sin_imp = base_15 + base_0 + base_no_obj + base_exento
    
    iva_15 = (base_15 * Decimal('0.15')).quantize(Decimal('0.01'))
    total_neto = subtotal_sin_imp + iva_15

    def add_tot(label, val, is_total=False):
        style_label = estilo_bold if is_total else estilo_normal
        style_val = ParagraphStyle('r', fontSize=8, fontName='Helvetica-Bold' if is_total else 'Helvetica', alignment=TA_RIGHT, textColor=primary_color if is_total else colors.HexColor('#334155'))
        datos_totales.append([
            Paragraph(label, style_label),
            Paragraph(f"{simbolo}{val:,.2f}", style_val)
        ])

    add_tot('SUBTOTAL 15%', base_15)
    add_tot('SUBTOTAL 0%', base_0)
    add_tot('SUBTOTAL No objeto de IVA', base_no_obj)
    add_tot('SUBTOTAL SIN IMPUESTOS', subtotal_sin_imp)
    add_tot('SUBTOTAL Exento de IVA', base_exento)
    add_tot('DESCUENTO', total_descuento)
    add_tot('ICE', Decimal('0.00'))
    add_tot('IVA 15%', iva_15)
    add_tot('IRBPNR', Decimal('0.00'))
    add_tot('PROPINA', Decimal('0.00'))
    add_tot('VALOR TOTAL', total_neto, is_total=True)

    tabla_totales = Table(datos_totales, colWidths=[5.5*cm, 3*cm])
    tabla_totales.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('LINEBELOW', (0,0), (-1,-2), 0.5, colors.HexColor('#F1F5F9')),
        ('PADDING', (0,0), (-1,-1), 4),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#F8FAFC')),
    ]))
    
    tabla_bottom = Table([[tabla_adic_flow, tabla_totales]], colWidths=[9.5*cm, 8.5*cm])
    tabla_bottom.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 0),
    ]))
    
    elementos.append(KeepTogether(tabla_bottom))

    doc.build(elementos)
    return buffer.getvalue()


def generate_quote_pdf(quote: dict, params: dict, tenant: dict) -> bytes:
    """
    Genera PDF de cotización parametrizado con logotipos, descuentos y totales correctos.
    """
    buffer = BytesIO()
    cfg = _config_desde_params(params)
    cfg['primary_color'] = tenant.get('primary_color', '#1976D2')
    cfg['empresa_nombre'] = cfg['empresa_nombre'] or tenant.get('name', 'Mi Empresa')
    
    dias_cotiz = params.get('ventas', {}).get('dias_cotizacion', {}).get('valor', '15')
    cfg['pie_factura'] = f"Cotización válida por {dias_cotiz} días. {cfg['pie_factura']}"

    primary_color = _color_hex(cfg['primary_color'])
    simbolo = cfg['moneda_simbolo']

    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=1.5*cm, leftMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    estilos = getSampleStyleSheet()
    elementos = []

    # ── ENCABEZADO CON LOGO ─────────────────────────────────────
    estilo_empresa = ParagraphStyle('empresa', fontSize=14, leading=17, fontName='Helvetica-Bold', textColor=primary_color)
    estilo_sub = ParagraphStyle('sub', fontSize=8.5, textColor=colors.grey)
    estilo_titulo = ParagraphStyle('titulo', fontSize=22, leading=26, fontName='Helvetica-Bold',
                                   textColor=primary_color, alignment=TA_RIGHT)

    col_izquierda = []
    logo_el = _obtener_logo_element(tenant.get('logo_url'))
    if logo_el:
        col_izquierda.append(logo_el)
        col_izquierda.append(Spacer(1, 0.2*cm))
    col_izquierda.extend([
        Paragraph(cfg['empresa_nombre'], estilo_empresa),
        Paragraph(f"<b>RUC:</b> {cfg['empresa_rfc']}", estilo_sub),
        Paragraph(f"<b>Dirección:</b> {cfg['empresa_direccion']}", estilo_sub),
        Paragraph(f"<b>Teléfono:</b> {cfg['empresa_telefono']}", estilo_sub),
    ])

    col_derecha = [
        Paragraph('COTIZACIÓN', estilo_titulo),
        Paragraph(f"<b>Fecha:</b> {quote.get('date', '')}", ParagraphStyle('d', fontSize=10, alignment=TA_RIGHT)),
        Paragraph(f"<b>Estado:</b> {quote.get('status', '').upper()}", ParagraphStyle('d', fontSize=10, alignment=TA_RIGHT)),
    ]

    tabla_enc = Table([[col_izquierda, col_derecha]], colWidths=[10*cm, 8*cm])
    tabla_enc.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    elementos.append(tabla_enc)
    elementos.append(Spacer(1, 0.4*cm))
    elementos.append(HRFlowable(width='100%', thickness=2, color=primary_color))
    elementos.append(Spacer(1, 0.4*cm))

    # ── DATOS CLIENTE ────────────────────────────────────────────
    estilo_seccion = ParagraphStyle('sec', fontSize=9.5, fontName='Helvetica-Bold', textColor=primary_color)
    estilo_dato = ParagraphStyle('dato', fontSize=9)

    datos_cliente = [
        [Paragraph('<b>COTIZAR A:</b>', estilo_seccion), ''],
        [Paragraph(f"<b>Client:</b> {quote.get('cliente_nombre', '')}", estilo_dato),
         Paragraph(f"<b>RUC/Cédula:</b> {quote.get('client_identification', 'N/D')}", estilo_dato)],
        [Paragraph(f"<b>Dirección:</b> {quote.get('client_address') or 'N/D'}", estilo_dato),
         Paragraph(f"<b>Email:</b> {quote.get('client_email') or 'N/D'}", estilo_dato)],
    ]
    tabla_cli = Table(datos_cliente, colWidths=[9*cm, 9*cm])
    tabla_cli.setStyle(TableStyle([
        ('SPAN', (0, 0), (1, 0)),
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.95, 0.95, 0.95)),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elementos.append(tabla_cli)
    elementos.append(Spacer(1, 0.5*cm))

    # ── TABLA DE ITEMS ───────────────────────────────────────────
    cabeceras = ['#', 'Descripción', 'Cant.', 'Precio Unit.', 'Desc.%', 'Subtotal']
    filas = [cabeceras]
    
    total_descuento = Decimal('0.00')
    total_subtotal_bruto = Decimal('0.00')
    total_neto_sin_iva = Decimal('0.00')

    for idx, item in enumerate(quote.get('items', []), 1):
        quantity = Decimal(str(item.get('quantity', 0)))
        precio = Decimal(str(item.get('unit_price', 0)))
        discount = Decimal(str(item.get('discount', 0)))
        
        base = quantity * precio
        desc_val = (base * discount / Decimal('100')).quantize(Decimal('0.01'))
        subtotal = base - desc_val
        
        total_descuento += desc_val
        total_subtotal_bruto += base
        total_neto_sin_iva += subtotal

        filas.append([
            str(idx),
            item.get('description', ''),
            str(quantity),
            f"{simbolo}{precio:,.2f}",
            f"{discount}%",
            f"{simbolo}{subtotal:,.2f}",
        ])

    tabla_items = Table(filas, colWidths=[1*cm, 8*cm, 2*cm, 3*cm, 2*cm, 3*cm])
    tabla_items.setStyle(TableStyle([
        ('BACKGROUND',   (0, 0), (-1, 0), primary_color),
        ('TEXTCOLOR',    (0, 0), (-1, 0), colors.white),
        ('FONTNAME',     (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',     (0, 0), (-1, -1), 9),
        ('ALIGN',        (2, 0), (-1, -1), 'RIGHT'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.Color(0.97, 0.97, 0.97)]),
        ('GRID',         (0, 0), (-1, -1), 0.5, colors.Color(0.85, 0.85, 0.85)),
        ('PADDING',      (0, 0), (-1, -1), 5),
    ]))
    elementos.append(tabla_items)
    elementos.append(Spacer(1, 0.4*cm))

    # ── TOTALES ──────────────────────────────────────────────────
    iva_pct = Decimal(str(params.get('ventas', {}).get('iva', {}).get('valor', '15')))
    iva_val = (total_neto_sin_iva * iva_pct / Decimal('100')).quantize(Decimal('0.01'))
    total_con_iva = total_neto_sin_iva + iva_val

    datos_totales = []
    if total_descuento > 0:
        datos_totales.append(['', 'Subtotal Bruto:', f"{simbolo}{total_subtotal_bruto:,.2f}"])
        datos_totales.append(['', 'Descuento:', f"-{simbolo}{total_descuento:,.2f}"])
        
    datos_totales.extend([
        ['', f"Subtotal IVA {iva_pct}%:", f"{simbolo}{total_neto_sin_iva:,.2f}"],
        ['', f"IVA ({iva_pct}%):", f"{simbolo}{iva_val:,.2f}"],
        ['', 'TOTAL:', f"{simbolo}{total_con_iva:,.2f}"],
    ])

    tabla_totales = Table(datos_totales, colWidths=[11*cm, 4*cm, 4*cm])
    tabla_totales.setStyle(TableStyle([
        ('ALIGN',     (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME',  (1, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE',  (0, 0), (-1, -1), 9.5),
        ('FONTSIZE',  (1, -1), (-1, -1), 11.5),
        ('TEXTCOLOR', (1, -1), (-1, -1), primary_color),
        ('BACKGROUND',(0, -1), (-1, -1), colors.Color(0.95, 0.95, 0.95)),
        ('LINEABOVE', (0, -1), (-1, -1), 1.5, primary_color),
        ('PADDING',   (0, 0), (-1, -1), 4),
    ]))
    elementos.append(tabla_totales)
    
    if quote.get('notas'):
        elementos.append(Spacer(1, 0.5*cm))
        elementos.append(Paragraph('<b>Notas Adicionales:</b>', ParagraphStyle('n', fontSize=9, fontName='Helvetica-Bold', textColor=primary_color)))
        elementos.append(Paragraph(quote.get('notas'), ParagraphStyle('n2', fontSize=8.5)))
        
    elementos.append(Spacer(1, 0.6*cm))

    # ── PIE DE PÁGINA ────────────────────────────────────────────
    elementos.append(HRFlowable(width='100%', thickness=1, color=colors.lightgrey))
    elementos.append(Spacer(1, 0.3*cm))
    elementos.append(Paragraph(cfg['pie_factura'],
                                ParagraphStyle('pie', fontSize=8.5, textColor=colors.grey, alignment=TA_CENTER)))

    doc.build(elementos)
    return buffer.getvalue()


def generate_report_pdf(titulo: str, columnas: list, filas: list, params: dict, tenant: dict) -> bytes:
    """
    Generates a professional corporate PDF report with a grid of data.
    """
    from datetime import date
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5*cm, leftMargin=1.5*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm,
    )
    
    color_hex = tenant.get('primary_color', '#1976D2')
    primary_color = _color_hex(color_hex)
    cfg = _config_desde_params(params)
    empresa_nombre = cfg['empresa_nombre'] or tenant.get('name', 'ERP')
    
    elementos = []
    
    # ── HEADER BANNER ──
    estilos = getSampleStyleSheet()
    titulo_style = ParagraphStyle(
        'ReportTitle',
        parent=estilos['Heading1'],
        fontSize=20,
        textColor=primary_color,
        spaceAfter=10,
        alignment=TA_LEFT,
    )
    
    col_izq = [
        Paragraph(titulo, titulo_style),
        Paragraph(f"Empresa: {empresa_nombre}", ParagraphStyle('Sub', fontSize=10, textColor=colors.grey)),
        Paragraph(f"Fecha de impresión: {date.today().strftime('%Y-%m-%d')}", ParagraphStyle('Sub2', fontSize=9, textColor=colors.grey))
    ]
    
    col_der = []
    logo_el = _obtener_logo_element(tenant.get('logo_url'))
    if logo_el:
        col_der.append(logo_el)
        
    t_header = Table([[col_izq, col_der]], colWidths=[13*cm, 5*cm])
    t_header.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    
    elementos.append(t_header)
    elementos.append(Spacer(1, 0.2*cm))
    elementos.append(HRFlowable(width='100%', thickness=1.5, color=primary_color, spaceAfter=20))

    # ── TABLA DE DATOS ──
    # Definir anchos específicos según el tipo de reporte para evitar que sobresalga del A4
    n_cols = len(columnas)
    col_widths = None
    if n_cols == 9:
        # Reporte de Utilidades y Margen (9 columnas, max 18cm)
        col_widths = [1.5*cm, 2.5*cm, 1.8*cm, 4.0*cm, 1.2*cm, 1.7*cm, 1.7*cm, 1.7*cm, 1.9*cm]
    elif n_cols == 4:
        # Reporte de Top Productos (4 columnas, max 18cm)
        col_widths = [3.0*cm, 7.5*cm, 3.5*cm, 4.0*cm]
    else:
        # Genérico proporcional
        col_widths = [(18.0 / n_cols)*cm] * n_cols

    # Estilos de textos dentro de las celdas
    estilo_cabecera = ParagraphStyle('HeadStyle', fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.white)
    estilo_celda = ParagraphStyle('BodyStyle', fontName='Helvetica', fontSize=7.5, leading=9, textColor=colors.black)

    # Convertir todas las celdas a Paragraph para autowrap en celdas de ancho fijo
    datos_tabla = []
    # Fila de cabecera
    datos_tabla.append([Paragraph(str(col), estilo_cabecera) for col in columnas])
    # Filas de datos
    for fila in filas:
        datos_tabla.append([Paragraph(str(celda), estilo_celda) for celda in fila])
    
    tabla = Table(datos_tabla, colWidths=col_widths, hAlign='LEFT')
    tabla.setStyle(TableStyle([
        ('BACKGROUND',     (0, 0), (-1, 0), primary_color),
        ('ALIGN',          (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN',         (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.Color(0.96, 0.96, 0.96)]),
        ('GRID',           (0, 0), (-1, -1), 0.5, colors.Color(0.88, 0.88, 0.88)),
        ('PADDING',        (0, 0), (-1, -1), 5),
    ]))
    elementos.append(tabla)
    
    doc.build(elementos)
    return buffer.getvalue()



def generate_cash_closure_pdf(closing: dict, params: dict, tenant: dict) -> bytes:
    """
    Generates a professional Cash Close Audit PDF report with primary colors.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5*cm, leftMargin=1.5*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm,
    )
    
    color_hex = tenant.get('primary_color', '#1976D2')
    primary_color = _color_hex(color_hex)
    cfg = _config_desde_params(params)
    simbolo = cfg['moneda_simbolo']
    empresa_nombre = cfg['empresa_nombre'] or tenant.get('name', 'ERP')
    
    elementos = []
    estilos = getSampleStyleSheet()
    
    # Header Title
    title_style = ParagraphStyle(
        'ReportTitle',
        parent=estilos['Heading1'],
        fontSize=20,
        leading=24,
        textColor=primary_color,
        spaceAfter=10,
        alignment=TA_LEFT,
    )
    
    col_izq = [
        Paragraph("AUDITORÍA DE CIERRE DE CAJA", title_style),
        Paragraph(f"Empresa: {empresa_nombre}", ParagraphStyle('Sub', fontSize=10, textColor=colors.grey)),
        Paragraph(f"Fecha de reporte: {date.today().strftime('%Y-%m-%d')}", ParagraphStyle('Sub2', fontSize=9, textColor=colors.grey))
    ]
    
    col_der = []
    logo_el = _obtener_logo_element(tenant.get('logo_url'))
    if logo_el:
        # Hacer el logo un poco más pequeño para este reporte si se desea, o usar el tamaño por defecto
        col_der.append(logo_el)
        
    t_header = Table([[col_izq, col_der]], colWidths=[13*cm, 5*cm])
    t_header.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    
    elementos.append(t_header)
    elementos.append(Spacer(1, 0.2*cm))
    elementos.append(HRFlowable(width='100%', thickness=1.5, color=primary_color, spaceAfter=20))
    
    # 1. DETALLES DE SESIÓN (Tabla de cabecera)
    estilo_dato = ParagraphStyle('dato', fontSize=9.5)
    detalles_data = [
        [
            Paragraph(f"<b>Caja:</b> {closing['caja_nombre']}", estilo_dato),
            Paragraph(f"<b>Cajero:</b> {closing['cajero']}", estilo_dato)
        ],
        [
            Paragraph(f"<b>Apertura:</b> {closing['fecha_apertura']}", estilo_dato),
            Paragraph(f"<b>Cierre:</b> {closing['fecha_cierre']}", estilo_dato)
        ]
    ]
    t_detalles = Table(detalles_data, colWidths=[9*cm, 9*cm])
    t_detalles.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.Color(0.96, 0.96, 0.96)),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(0.88, 0.88, 0.88)),
    ]))
    elementos.append(t_detalles)
    elementos.append(Spacer(1, 0.6*cm))
    
    # 2. TABLA DE RESUMEN FINANCIERO
    estilo_seccion = ParagraphStyle('sec', fontSize=10.5, fontName='Helvetica-Bold', textColor=primary_color)
    elementos.append(Paragraph("Resumen de Transacciones", estilo_seccion))
    elementos.append(Spacer(1, 0.2*cm))
    
    saldo_inicial = float(closing.get('saldo_inicial') or 0.0)
    total_efectivo = float(closing.get('total_efectivo') or 0.0)
    total_tarjeta = float(closing.get('total_tarjeta') or 0.0)
    total_transferencia = float(closing.get('total_transferencia') or 0.0)
    total_sales = float(closing.get('total_sales') or 0.0)
    saldo_esperado = float(closing.get('saldo_esperado') or 0.0)
    saldo_contado = float(closing.get('saldo_contado') or 0.0)

    total_ingresos = float(closing.get('total_ingresos') or 0.0)
    total_egresos = float(closing.get('total_egresos') or 0.0)

    closing_breakdown = closing.get('closing_breakdown') or {}
    conteos = closing_breakdown.get('conteos', {})
    cant_efectivo = conteos.get('efectivo', 0)
    cant_tarjeta = conteos.get('tarjeta', 0)
    cant_transferencia = conteos.get('transferencia', 0)

    txt_efectivo = f"(+) Ventas en Efectivo ({cant_efectivo} venta{'s' if cant_efectivo != 1 else ''})" if cant_efectivo else "(+) Ventas en Efectivo"
    txt_tarjeta = f"(+) Ventas con Tarjeta ({cant_tarjeta} venta{'s' if cant_tarjeta != 1 else ''})" if cant_tarjeta else "(+) Ventas con Tarjeta de Crédito"
    txt_transferencia = f"(+) Ventas por Transferencia ({cant_transferencia} venta{'s' if cant_transferencia != 1 else ''})" if cant_transferencia else "(+) Ventas por Transferencia Bancaria"

    tabla_ventas_data = [
        ["Concepto / Método de Pago", "Monto"],
        ["Saldo Inicial de Apertura", f"{simbolo}{saldo_inicial:.2f}"],
        [txt_efectivo, f"{simbolo}{total_efectivo:.2f}"],
        [txt_tarjeta, f"{simbolo}{total_tarjeta:.2f}"],
        [txt_transferencia, f"{simbolo}{total_transferencia:.2f}"],
        ["TOTAL VENTAS REGISTRADAS", f"{simbolo}{total_sales:.2f}"],
        ["(+) Ingresos / Entradas Manuales de Caja", f"{simbolo}{total_ingresos:.2f}"],
        ["(-) Retiros / Salidas Manuales de Caja", f"{simbolo}{total_egresos:.2f}"],
        ["SALDO ESPERADO EN CAJA (Inicial + Efec. + Ing. - Sal.)", f"{simbolo}{saldo_esperado:.2f}"],
        ["SALDO CONTADO FÍSICAMENTE", f"{simbolo}{saldo_contado:.2f}"],
    ]
    
    t_ventas = Table(tabla_ventas_data, colWidths=[12*cm, 6*cm])
    t_ventas.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9.5),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(0.85, 0.85, 0.85)),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('FONTNAME', (0, -2), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -2), (-1, -2), colors.Color(0.95, 0.95, 0.95)),
        ('BACKGROUND', (0, -1), (-1, -1), colors.Color(0.9, 0.9, 0.9)),
    ]))
    elementos.append(t_ventas)
    elementos.append(Spacer(1, 0.6*cm))
    
    # 3. CUADRE Y DIFERENCIA
    dif = float(closing.get('diferencia') or 0.0)
    if dif == 0:
        dif_hex = '#2E7D32'  # Verde
        dif_texto = "CUADRADO (OK)"
    elif dif > 0:
        dif_hex = '#E65100'  # Naranja
        dif_texto = f"SOBRANTE DE {simbolo}{dif:.2f}"
    else:
        dif_hex = '#C62828'  # Rojo
        dif_texto = f"FALTANTE DE {simbolo}{abs(dif):.2f}"
        
    cuadre_data = [
        [
            Paragraph(f"<b>Diferencia de Cuadre:</b>", ParagraphStyle('lbl', fontSize=11, fontName='Helvetica-Bold')),
            Paragraph(f"<font color='{dif_hex}'><b>{dif_texto}</b></font>", ParagraphStyle('val', fontSize=11, alignment=TA_RIGHT))
        ]
    ]
    t_cuadre = Table(cuadre_data, colWidths=[9*cm, 9*cm])
    t_cuadre.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.Color(0.97, 0.97, 0.97)),
        ('LINEBELOW', (0, 0), (-1, -1), 2, colors.HexColor(dif_hex)),
        ('PADDING', (0, 0), (-1, -1), 10),
    ]))

    elementos.append(t_cuadre)
    elementos.append(Spacer(1, 0.6*cm))
    
    efectivo_desglose = closing_breakdown.get('efectivo_desglose')
    if efectivo_desglose:
        bills = efectivo_desglose.get('bills', {})
        coins = efectivo_desglose.get('coins', {})
        if bills or coins:
            desglose_data = [["Denominación", "Cantidad", "Subtotal"]]
            total_desglose = 0.0
            for k, v in bills.items():
                if int(v) > 0:
                    sub = float(k) * int(v)
                    total_desglose += sub
                    desglose_data.append([f"Billete {simbolo}{k}", str(v), f"{simbolo}{sub:.2f}"])
            for k, v in coins.items():
                if int(v) > 0:
                    sub = float(k) * int(v)
                    total_desglose += sub
                    desglose_data.append([f"Moneda {simbolo}{k}", str(v), f"{simbolo}{sub:.2f}"])
            
            if len(desglose_data) > 1:
                desglose_data.append(["TOTAL EFECTIVO CONTADO", "", f"{simbolo}{total_desglose:.2f}"])
                elementos.append(Paragraph("<b>Desglose Físico de Efectivo:</b>", ParagraphStyle('desg', fontSize=10, fontName='Helvetica-Bold', textColor=primary_color)))
                elementos.append(Spacer(1, 0.2*cm))
                t_desglose = Table(desglose_data, colWidths=[6*cm, 4*cm, 4*cm])
                t_desglose.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), primary_color),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                    ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(0.85, 0.85, 0.85)),
                    ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                    ('BACKGROUND', (0, -1), (-1, -1), colors.Color(0.95, 0.95, 0.95)),
                ]))
                elementos.append(t_desglose)
                elementos.append(Spacer(1, 0.6*cm))
    
    # 4. OBSERVACIONES
    elementos.append(Paragraph("<b>Observaciones de Cierre:</b>", ParagraphStyle('obs', fontSize=10, fontName='Helvetica-Bold', textColor=primary_color)))
    elementos.append(Paragraph(str(closing.get('observaciones') or 'Sin observaciones registradas durante este turno.'), ParagraphStyle('obs2', fontSize=9)))
    elementos.append(Spacer(1, 1.0*cm))
    
    # Detalle de Transacciones (si existen)
    transacciones = closing_breakdown.get('transacciones', [])
    if transacciones:
        # Título de la sección de detalles
        
        # Título de la nueva página de detalles
        elementos.append(Paragraph("DETALLE CRONOLÓGICO DE TRANSACCIONES", title_style))
        elementos.append(HRFlowable(width='100%', thickness=1.5, color=primary_color, spaceAfter=15))
        
        tabla_tx_data = [
            ["Fecha/Hora", "Cliente", "Método", "Comprobante", "Monto"]
        ]
        for tx in transacciones:
            metodo_label = str(tx.get('metodo_pago', '')).capitalize()
            comp_val = str(tx.get('comprobante') or '')
            if not comp_val or comp_val == 'None' or comp_val.strip() == '':
                comp_val = '-'
            tabla_tx_data.append([
                tx.get('fecha', ''),
                tx.get('cliente', ''),
                metodo_label,
                comp_val,
                f"{simbolo}{float(tx.get('total') or 0.0):.2f}"
            ])
            
        t_tx = Table(tabla_tx_data, colWidths=[4*cm, 5.5*cm, 3*cm, 3.5*cm, 2*cm])
        t_tx.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8.5),
            ('ALIGN', (4, 0), (4, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(0.85, 0.85, 0.85)),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        elementos.append(t_tx)
        elementos.append(Spacer(1, 1.0*cm))

    # 5. FIRMAS DE RESPONSABILIDAD
    firmas_data = [
        ["________________________", "________________________"],
        ["Firma Cajero", "Firma Supervisor / Auditor"]
    ]
    t_firmas = Table(firmas_data, colWidths=[9*cm, 9*cm])
    t_firmas.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9.5),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.grey),
    ]))
    elementos.append(t_firmas)
    
    doc.build(elementos)
    return buffer.getvalue()


def generate_closure_summary_pdf(report_data: dict, params: dict, tenant: dict) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.2*cm, leftMargin=1.2*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm,
    )
    
    color_hex = tenant.get('primary_color', '#1976D2')
    primary_color = _color_hex(color_hex)
    cfg = _config_desde_params(params)
    simbolo = cfg['moneda_simbolo']
    empresa_nombre = cfg['empresa_nombre'] or tenant.get('name', 'ERP')
    
    meta = report_data['meta']
    details = report_data['details']
    totals = report_data['totals']
    
    elementos = []
    estilos = getSampleStyleSheet()
    
    title_text = "REPORTE CONSOLIDADO DE CIERRES DE CAJA"
    if meta['is_employee_report']:
        title_text = f"VENTAS DEL TRABAJADOR: {meta['employee_name'].upper()}"
        
    title_style = ParagraphStyle(
        'ReportTitle',
        parent=estilos['Heading1'],
        fontSize=18,
        leading=22,
        textColor=primary_color,
        spaceAfter=10,
        alignment=TA_LEFT,
    )
    
    col_izq = [
        Paragraph(title_text, title_style),
        Paragraph(f"Empresa: {empresa_nombre}", ParagraphStyle('Sub', fontSize=10, textColor=colors.grey)),
        Paragraph(f"Fecha de reporte: {date.today().strftime('%Y-%m-%d')}", ParagraphStyle('Sub2', fontSize=9, textColor=colors.grey))
    ]
    
    col_der = []
    logo_el = _obtener_logo_element(tenant.get('logo_url'))
    if logo_el:
        col_der.append(logo_el)
        
    t_header = Table([[col_izq, col_der]], colWidths=[13*cm, 5*cm])
    t_header.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    
    elementos.append(t_header)
    elementos.append(Spacer(1, 0.2*cm))
    elementos.append(HRFlowable(width='100%', thickness=1.5, color=primary_color, spaceAfter=15))
    
    # 1. Filtros Aplicados Box
    estilo_dato = ParagraphStyle('dato', fontSize=9)
    detalles_data = [
        [
            Paragraph(f"<b>Rango:</b> {meta['start_date']} al {meta['end_date']}", estilo_dato),
            Paragraph(f"<b>Temporalidad:</b> {meta['period_type'].upper()}", estilo_dato)
        ],
        [
            Paragraph(f"<b>Local:</b> {meta['branch_name']}", estilo_dato),
            Paragraph(f"<b>Caja:</b> {meta['register_name']}", estilo_dato)
        ]
    ]
    t_detalles = Table(detalles_data, colWidths=[9.3*cm, 9.3*cm])
    t_detalles.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.Color(0.96, 0.96, 0.96)),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(0.88, 0.88, 0.88)),
    ]))
    elementos.append(t_detalles)
    elementos.append(Spacer(1, 0.6*cm))
    
    # 2. Main Table
    estilo_seccion = ParagraphStyle('sec', fontSize=11, fontName='Helvetica-Bold', textColor=primary_color)
    elementos.append(Paragraph("Resumen Financiero Consolidado", estilo_seccion))
    elementos.append(Spacer(1, 0.2*cm))
    
    estilo_celda = ParagraphStyle('celda', fontSize=8)
    estilo_celda_hdr = ParagraphStyle('celdahdr', fontSize=8, fontName='Helvetica-Bold', textColor=colors.white)
    
    if meta['is_employee_report']:
        headers = ["Caja / Turno", "Ef. Ventas", "Tj. Ventas", "Tr. Ventas", "Ventas", "Total Recaudado"]
        col_widths = [6.6*cm, 2.4*cm, 2.4*cm, 2.4*cm, 1.8*cm, 3.0*cm]
        
        rows = [[Paragraph(f"<b>{h}</b>", estilo_celda_hdr) for h in headers]]
        
        for d in details:
            rows.append([
                Paragraph(d['register_name'], estilo_celda),
                Paragraph(f"{simbolo}{d['cash']:.2f}", estilo_celda),
                Paragraph(f"{simbolo}{d['card']:.2f}", estilo_celda),
                Paragraph(f"{simbolo}{d['transfer']:.2f}", estilo_celda),
                Paragraph(str(d['sales_count']), estilo_celda),
                Paragraph(f"<b>{simbolo}{d['total']:.2f}</b>", estilo_celda)
            ])
            
        # Totals row
        rows.append([
            Paragraph("<b>TOTALES</b>", estilo_celda),
            Paragraph(f"<b>{simbolo}{totals['cash']:.2f}</b>", estilo_celda),
            Paragraph(f"<b>{simbolo}{totals['card']:.2f}</b>", estilo_celda),
            Paragraph(f"<b>{simbolo}{totals['transfer']:.2f}</b>", estilo_celda),
            Paragraph(f"<b>{totals['sales_count']}</b>", estilo_celda),
            Paragraph(f"<b>{simbolo}{totals['total']:.2f}</b>", estilo_celda)
        ])
        
        t_main = Table(rows, colWidths=col_widths)
        t_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), primary_color),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(0.85, 0.85, 0.85)),
            ('PADDING', (0, 0), (-1, -1), 5),
            ('BACKGROUND', (0, -1), (-1, -1), colors.Color(0.92, 0.95, 0.98)),
        ])
        t_main.setStyle(t_style)
        elementos.append(t_main)
        
    else:
        headers = ["Caja", "Cajero", "Ventas", "Inicial", "Efectivo", "Tarjeta", "Transfer.", "Esperado", "Contado", "Diferencia"]
        col_widths = [1.8*cm, 2.0*cm, 1.2*cm, 1.8*cm, 1.8*cm, 1.8*cm, 1.8*cm, 2.0*cm, 2.0*cm, 2.4*cm]
        
        rows = [[Paragraph(f"<b>{h}</b>", estilo_celda_hdr) for h in headers]]
        
        for d in details:
            dif_val = d['difference']
            dif_color = 'red' if dif_val < 0 else ('green' if dif_val == 0 else 'orange')
            estilo_dif = ParagraphStyle('dif', parent=estilo_celda, fontName='Helvetica-Bold', textColor=colors.HexColor(dif_color))
            
            rows.append([
                Paragraph(d['register_name'], estilo_celda),
                Paragraph(d['cashier_name'][:10], estilo_celda),
                Paragraph(str(d['sales_count']), estilo_celda),
                Paragraph(f"{simbolo}{d['initial_balance']:.2f}", estilo_celda),
                Paragraph(f"{simbolo}{d['total_cash']:.2f}", estilo_celda),
                Paragraph(f"{simbolo}{d['total_card']:.2f}", estilo_celda),
                Paragraph(f"{simbolo}{d['total_transfer']:.2f}", estilo_celda),
                Paragraph(f"{simbolo}{d['expected_balance']:.2f}", estilo_celda),
                Paragraph(f"{simbolo}{d['counted_balance']:.2f}", estilo_celda),
                Paragraph(f"{simbolo}{dif_val:.2f}", estilo_dif)
            ])
            
        # Totals row
        dif_val = totals['difference']
        dif_color = 'red' if dif_val < 0 else ('green' if dif_val == 0 else 'orange')
        estilo_dif = ParagraphStyle('dif_tot', parent=estilo_celda, fontName='Helvetica-Bold', textColor=colors.HexColor(dif_color))
        
        rows.append([
            Paragraph("<b>TOTALES</b>", estilo_celda),
            Paragraph("", estilo_celda),
            Paragraph(f"<b>{totals['sales_count']}</b>", estilo_celda),
            Paragraph(f"<b>{simbolo}{totals['initial_balance']:.2f}</b>", estilo_celda),
            Paragraph(f"<b>{simbolo}{totals['total_cash']:.2f}</b>", estilo_celda),
            Paragraph(f"<b>{simbolo}{totals['total_card']:.2f}</b>", estilo_celda),
            Paragraph(f"<b>{simbolo}{totals['total_transfer']:.2f}</b>", estilo_celda),
            Paragraph(f"<b>{simbolo}{totals['expected_balance']:.2f}</b>", estilo_celda),
            Paragraph(f"<b>{simbolo}{totals['counted_balance']:.2f}</b>", estilo_celda),
            Paragraph(f"<b>{simbolo}{dif_val:.2f}</b>", estilo_dif)
        ])
        
        t_main = Table(rows, colWidths=col_widths)
        t_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), primary_color),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(0.85, 0.85, 0.85)),
            ('PADDING', (0, 0), (-1, -1), 4),
            ('BACKGROUND', (0, -1), (-1, -1), colors.Color(0.92, 0.95, 0.98)),
        ])
        t_main.setStyle(t_style)
        elementos.append(t_main)
        
    elementos.append(Spacer(1, 1.2*cm))
    
    # 3. FIRMAS DE RESPONSABILIDAD
    firmas_data = [
        ["________________________", "________________________"],
        ["Firma Cajero", "Firma Supervisor / Auditor"]
    ]
    t_firmas = Table(firmas_data, colWidths=[9.3*cm, 9.3*cm])
    t_firmas.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9.5),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.grey),
    ]))
    elementos.append(t_firmas)
    
    doc.build(elementos)
    return buffer.getvalue()



