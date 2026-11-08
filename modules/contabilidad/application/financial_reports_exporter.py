"""
Generador de Estados Financieros Oficiales (Balance General y Estado de Resultados).
Soporta exportación a PDF (ReportLab) y Excel (openpyxl) corporativos y ejecutivos.
Extrae automáticamente la identidad y firmas de la empresa desde los parámetros del Tenant:
- Logo corporativo
- Nombre comercial / Razón social
- RUC
- Dirección, teléfono y correo
- Firma y cargo del Representante Legal
- Firma, cargo y matrícula del Contador Público
"""

import os
from io import BytesIO
from datetime import datetime, date
from typing import Optional, Dict, Any

from django.conf import settings
from django.db.models import Sum

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable, Image, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

from shared.parametros import param
from modules.tenants.infrastructure.django_models import TenantModel
from ..infrastructure.django_models import AccountModel, JournalEntryLineModel


# ---------------------------------------------------------------------------
# Contexto de la Empresa desde Parámetros y Tenant
# ---------------------------------------------------------------------------

def get_company_context(tenant_id: int) -> Dict[str, Any]:
    """
    Obtiene la metadata corporativa del tenant para la cabecera y pie de firmas.
    """
    tenant = TenantModel.objects.filter(id=tenant_id).first()

    empresa_nombre = (
        param(tenant_id, 'general', 'empresa_nombre') 
        or (getattr(tenant, 'name', '') if tenant else '') 
        or 'Empresa del Sistema'
    )
    empresa_rfc = (
        param(tenant_id, 'general', 'empresa_rfc') 
        or param(tenant_id, 'facturacion', 'ruc_emisor') 
        or (getattr(tenant, 'ruc', '') if tenant else '')
        or '0000000000001'
    )
    empresa_direccion = (
        param(tenant_id, 'general', 'empresa_direccion') 
        or 'Matriz Central'
    )
    empresa_telefono = (
        param(tenant_id, 'general', 'empresa_telefono') 
        or (getattr(tenant, 'contact_phone', '') if tenant else '')
    )
    empresa_email = (
        param(tenant_id, 'general', 'empresa_email') 
        or (getattr(tenant, 'contact_email', '') if tenant else '')
    )
    empresa_representante = (
        param(tenant_id, 'general', 'empresa_representante') 
        or 'Representante Legal'
    )
    empresa_contador = (
        param(tenant_id, 'general', 'empresa_contador') 
        or 'Contador Público Autorizado'
    )
    empresa_contador_ruc = (
        param(tenant_id, 'general', 'empresa_contador_ruc') 
        or ''
    )
    logo_url = (
        param(tenant_id, 'general', 'logo_url') 
        or (getattr(tenant, 'logo_url', '') if tenant else '')
    )
    primary_color = (
        (getattr(tenant, 'primary_color', '') if tenant else '') 
        or '#1E3A8A'
    )

    return {
        'empresa_nombre': empresa_nombre,
        'empresa_rfc': empresa_rfc,
        'empresa_direccion': empresa_direccion,
        'empresa_telefono': empresa_telefono,
        'empresa_email': empresa_email,
        'empresa_representante': empresa_representante,
        'empresa_contador': empresa_contador,
        'empresa_contador_ruc': empresa_contador_ruc,
        'logo_url': logo_url,
        'primary_color': primary_color,
    }


def _obtener_logo_element(logo_url: str) -> Optional[Image]:
    """Resuelve la ruta física del logo para ReportLab."""
    if not logo_url:
        return None
    try:
        rel_path = logo_url
        if rel_path.startswith(settings.MEDIA_URL):
            rel_path = rel_path[len(settings.MEDIA_URL):]
        path_disk = os.path.join(settings.MEDIA_ROOT, rel_path)
        if os.path.exists(path_disk):
            return Image(path_disk, width=3.8 * cm, height=1.9 * cm, kind='bound')
    except Exception:
        pass
    return None


def _color_hex(hex_str: str) -> colors.Color:
    """Convierte hex a reportlab Color."""
    hex_clean = hex_str.lstrip('#')
    if len(hex_clean) != 6:
        return colors.HexColor('#1E3A8A')
    r = int(hex_clean[0:2], 16) / 255.0
    g = int(hex_clean[2:4], 16) / 255.0
    b = int(hex_clean[4:6], 16) / 255.0
    return colors.Color(r, g, b)


def _fmt_money(val) -> str:
    """Formatea monto a $#,##0.00"""
    try:
        num = float(val or 0)
        return f"${num:,.2f}"
    except (ValueError, TypeError):
        return "$0.00"


# ---------------------------------------------------------------------------
# Consultas de Datos de Balances (Capa de Servicio)
# ---------------------------------------------------------------------------

def fetch_balance_sheet_data(tenant_id: int, date_up_to: Optional[str] = None) -> Dict[str, Any]:
    """Calcula las partidas de Balance General al corte especificado."""
    qs = JournalEntryLineModel.objects.filter(entry__tenant_id=tenant_id)
    if date_up_to:
        qs = qs.filter(entry__date__lte=date_up_to)

    qs_balance = qs.filter(account__type__in=['is_active', 'pasivo', 'patrimonio'])

    aggregations = qs_balance.values(
        'account__id', 'account__code', 'account__name', 'account__type'
    ).annotate(
        total_debit=Sum('debit'),
        total_credit=Sum('credit')
    ).order_by('account__code')

    activos = []
    pasivos = []
    patrimonio = []
    total_activos = 0.0
    total_pasivos = 0.0
    total_patrimonio = 0.0

    for agg in aggregations:
        debit = float(agg['total_debit'] or 0)
        credit = float(agg['total_credit'] or 0)
        acc_type = agg['account__type']
        code = agg.get('account__code', '')
        name = agg['account__name']

        if acc_type == 'is_active':
            bal = debit - credit
            total_activos += bal
            activos.append({'id': agg['account__id'], 'code': code, 'name': name, 'balance': bal})
        elif acc_type == 'pasivo':
            bal = credit - debit
            total_pasivos += bal
            pasivos.append({'id': agg['account__id'], 'code': code, 'name': name, 'balance': bal})
        elif acc_type == 'patrimonio':
            bal = credit - debit
            total_patrimonio += bal
            patrimonio.append({'id': agg['account__id'], 'code': code, 'name': name, 'balance': bal})

    # Net income from P&L up to date
    qs_pnl = qs.filter(account__type__in=['ingreso', 'egreso']).aggregate(
        debit=Sum('debit'), credit=Sum('credit')
    )
    net_income = float((qs_pnl['credit'] or 0) - (qs_pnl['debit'] or 0))

    if net_income != 0:
        patrimonio.append({
            'id': 'utilidad_ejercicio',
            'code': '3.3.01',
            'name': 'Utilidad del Ejercicio' if net_income >= 0 else 'Pérdida del Ejercicio',
            'balance': net_income
        })
        total_patrimonio += net_income

    ecuacion_balance = round(total_activos, 2) == round(total_pasivos + total_patrimonio, 2)

    return {
        'activos': activos,
        'total_activos': total_activos,
        'pasivos': pasivos,
        'total_pasivos': total_pasivos,
        'patrimonio': patrimonio,
        'total_patrimonio': total_patrimonio,
        'ecuacion_balance': ecuacion_balance,
        'date_up_to': date_up_to or date.today().strftime('%Y-%m-%d')
    }


def fetch_pnl_data(tenant_id: int, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
    """Calcula las partidas del Estado de Resultados (P&L)."""
    qs = JournalEntryLineModel.objects.filter(entry__tenant_id=tenant_id)
    if start_date:
        qs = qs.filter(entry__date__gte=start_date)
    if end_date:
        qs = qs.filter(entry__date__lte=end_date)

    qs = qs.filter(account__type__in=['ingreso', 'egreso'])

    aggregations = qs.values(
        'account__id', 'account__code', 'account__name', 'account__type'
    ).annotate(
        total_debit=Sum('debit'),
        total_credit=Sum('credit')
    ).order_by('account__code')

    ingresos = []
    egresos = []
    total_ingresos = 0.0
    total_egresos = 0.0

    for agg in aggregations:
        debit = float(agg['total_debit'] or 0)
        credit = float(agg['total_credit'] or 0)
        acc_type = agg['account__type']
        code = agg.get('account__code', '')
        name = agg['account__name']

        if acc_type == 'ingreso':
            bal = credit - debit
            total_ingresos += bal
            ingresos.append({'id': agg['account__id'], 'code': code, 'name': name, 'balance': bal})
        elif acc_type == 'egreso':
            bal = debit - credit
            total_egresos += bal
            egresos.append({'id': agg['account__id'], 'code': code, 'name': name, 'balance': bal})

    utilidad_neta = total_ingresos - total_egresos

    return {
        'ingresos': ingresos,
        'total_ingresos': total_ingresos,
        'egresos': egresos,
        'total_egresos': total_egresos,
        'utilidad_neta': utilidad_neta,
        'start_date': start_date or date.today().strftime('%Y-%m-01'),
        'end_date': end_date or date.today().strftime('%Y-%m-%d')
    }


# ---------------------------------------------------------------------------
# EXPORTACIÓN: BALANCE GENERAL EN PDF
# ---------------------------------------------------------------------------

def generate_balance_sheet_pdf(data: dict, tenant_id: int, date_up_to: str) -> bytes:
    """Genera el PDF oficial del Balance General."""
    ctx = get_company_context(tenant_id)
    primary_color = _color_hex(ctx['primary_color'])

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm
    )

    elementos = []

    # Estilos
    styles = getSampleStyleSheet()
    estilo_empresa = ParagraphStyle('EmpresaHdr', fontName='Helvetica-Bold', fontSize=14, leading=17, textColor=primary_color)
    estilo_empresa_sub = ParagraphStyle('EmpresaSub', fontName='Helvetica', fontSize=8.5, leading=12, textColor=colors.HexColor('#475569'))
    estilo_titulo = ParagraphStyle('TituloDoc', fontName='Helvetica-Bold', fontSize=12, leading=15, textColor=colors.HexColor('#0F172A'), alignment=TA_CENTER)
    estilo_subtitulo = ParagraphStyle('SubDoc', fontName='Helvetica', fontSize=8.5, leading=11, textColor=colors.HexColor('#64748B'), alignment=TA_CENTER)
    
    estilo_th = ParagraphStyle('TH', fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.white)
    estilo_td = ParagraphStyle('TD', fontName='Helvetica', fontSize=8, leading=10, textColor=colors.HexColor('#1E293B'))
    estilo_td_num = ParagraphStyle('TDNum', fontName='Helvetica', fontSize=8, leading=10, textColor=colors.HexColor('#1E293B'), alignment=TA_RIGHT)
    estilo_tot_label = ParagraphStyle('TotLbl', fontName='Helvetica-Bold', fontSize=8.5, leading=11, textColor=colors.HexColor('#0F172A'))
    estilo_tot_val = ParagraphStyle('TotVal', fontName='Helvetica-Bold', fontSize=8.5, leading=11, textColor=colors.HexColor('#0F172A'), alignment=TA_RIGHT)

    # 1. Cabecera Corporativa
    col_logo = []
    logo_el = _obtener_logo_element(ctx['logo_url'])
    if logo_el:
        col_logo.append(logo_el)
    else:
        col_logo.append(Paragraph(f"<b>{ctx['empresa_nombre']}</b>", estilo_empresa))

    col_info = [
        Paragraph(f"<b>{ctx['empresa_nombre']}</b>", estilo_empresa),
        Paragraph(f"<b>R.U.C.:</b> {ctx['empresa_rfc']}", estilo_empresa_sub),
        Paragraph(f"<b>Dirección:</b> {ctx['empresa_direccion']}", estilo_empresa_sub),
        Paragraph(f"<b>Teléfono:</b> {ctx['empresa_telefono']} &nbsp;|&nbsp; <b>Email:</b> {ctx['empresa_email']}", estilo_empresa_sub),
    ]

    tabla_cabecera = Table([[col_logo, col_info]], colWidths=[5.5 * cm, 12.5 * cm])
    tabla_cabecera.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    elementos.append(tabla_cabecera)
    elementos.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceAfter=8))

    # 2. Título del Reporte
    fecha_corte = date_up_to or data.get('date_up_to', '')
    elementos.append(Paragraph("ESTADO DE SITUACIÓN FINANCIERA (BALANCE GENERAL)", estilo_titulo))
    elementos.append(Paragraph(f"Al {fecha_corte} &nbsp;·&nbsp; Expresado en Dólares de los Estados Unidos de América (USD)", estilo_subtitulo))
    elementos.append(Spacer(1, 0.3 * cm))

    # 3. Estado de la Ecuación Contable
    cuadrado = data.get('ecuacion_balance', False)
    tot_act = data.get('total_activos', 0)
    tot_pas = data.get('total_pasivos', 0)
    tot_pat = data.get('total_patrimonio', 0)
    
    if cuadrado:
        ecuacion_txt = f"<b>✓ Ecuación Patrimonial Cuadrada:</b> Activo ({_fmt_money(tot_act)}) = Pasivo ({_fmt_money(tot_pas)}) + Patrimonio ({_fmt_money(tot_pat)})"
        bg_ecuacion = colors.HexColor('#ECFDF5')
        border_ecuacion = colors.HexColor('#10B981')
        color_texto = colors.HexColor('#065F46')
    else:
        dif = abs(tot_act - (tot_pas + tot_pat))
        ecuacion_txt = f"<b>⚠ Descuadre en Ecuación Contable:</b> Activo ({_fmt_money(tot_act)}) ≠ Pasivo + Patrimonio ({_fmt_money(tot_pas + tot_pat)}) &nbsp;|&nbsp; <b>Diferencia:</b> {_fmt_money(dif)}"
        bg_ecuacion = colors.HexColor('#FFF1F2')
        border_ecuacion = colors.HexColor('#F43F5E')
        color_texto = colors.HexColor('#9F1239')

    p_ecuacion = Paragraph(ecuacion_txt, ParagraphStyle('Ec', fontName='Helvetica', fontSize=8, leading=10, textColor=color_texto, alignment=TA_CENTER))
    t_ecuacion = Table([[p_ecuacion]], colWidths=[18.0 * cm])
    t_ecuacion.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg_ecuacion),
        ('BOX', (0, 0), (-1, -1), 1, border_ecuacion),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    elementos.append(t_ecuacion)
    elementos.append(Spacer(1, 0.4 * cm))

    # Helper para construir cada bloque contable
    def _crear_tabla_cuentas(titulo_grupo: str, cuentas: list, total_val: float, color_grupo: colors.Color):
        filas = [
            [
                Paragraph(f"<b>CÓDIGO</b>", estilo_th),
                Paragraph(f"<b>{titulo_grupo.upper()}</b>", estilo_th),
                Paragraph("<b>SALDO (USD)</b>", ParagraphStyle('THNum', parent=estilo_th, alignment=TA_RIGHT))
            ]
        ]
        
        if not cuentas:
            filas.append([
                Paragraph("-", estilo_td),
                Paragraph("<i>No se registran movimientos con saldo</i>", estilo_td),
                Paragraph("$0.00", estilo_td_num)
            ])
        else:
            for item in cuentas:
                filas.append([
                    Paragraph(item.get('code') or '-', estilo_td),
                    Paragraph(item.get('name') or '', estilo_td),
                    Paragraph(_fmt_money(item.get('balance', 0)), estilo_td_num)
                ])

        # Fila de Total
        filas.append([
            Paragraph("", estilo_tot_label),
            Paragraph(f"TOTAL {titulo_grupo.upper()}", estilo_tot_label),
            Paragraph(_fmt_money(total_val), estilo_tot_val)
        ])

        tabla = Table(filas, colWidths=[3.5 * cm, 10.5 * cm, 4.0 * cm])
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), color_grupo),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 4),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#F8FAFC')),
            ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor('#94A3B8')),
        ]))
        return tabla

    # 4. Tablas: Activos, Pasivos, Patrimonio
    elementos.append(_crear_tabla_cuentas("1. Activos", data.get('activos', []), tot_act, primary_color))
    elementos.append(Spacer(1, 0.35 * cm))

    elementos.append(_crear_tabla_cuentas("2. Pasivos", data.get('pasivos', []), tot_pas, colors.HexColor('#D97706')))
    elementos.append(Spacer(1, 0.35 * cm))

    elementos.append(_crear_tabla_cuentas("3. Patrimonio", data.get('patrimonio', []), tot_pat, colors.HexColor('#7C3AED')))
    elementos.append(Spacer(1, 0.35 * cm))

    # 5. Total Pasivo + Patrimonio
    tot_pas_pat = tot_pas + tot_pat
    tabla_total_final = Table([
        [
            Paragraph("", estilo_tot_label),
            Paragraph("TOTAL PASIVO + PATRIMONIO", ParagraphStyle('TotFin', fontName='Helvetica-Bold', fontSize=9.5, leading=12, textColor=colors.HexColor('#0F172A'))),
            Paragraph(_fmt_money(tot_pas_pat), ParagraphStyle('TotFinVal', fontName='Helvetica-Bold', fontSize=10, leading=12, textColor=colors.HexColor('#0F172A'), alignment=TA_RIGHT))
        ]
    ], colWidths=[3.5 * cm, 10.5 * cm, 4.0 * cm])
    tabla_total_final.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#E2E8F0')),
        ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor('#475569')),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    elementos.append(tabla_total_final)
    elementos.append(Spacer(1, 1.2 * cm))

    # 6. Firmas de Responsabilidad Oficial
    estilo_firma_nombre = ParagraphStyle('FN', fontName='Helvetica-Bold', fontSize=8.5, leading=11, alignment=TA_CENTER)
    estilo_firma_cargo = ParagraphStyle('FC', fontName='Helvetica', fontSize=7.5, leading=10, textColor=colors.HexColor('#475569'), alignment=TA_CENTER)
    estilo_linea = ParagraphStyle('FL', fontName='Helvetica', fontSize=8, leading=10, textColor=colors.HexColor('#94A3B8'), alignment=TA_CENTER)

    rep_nombre = ctx['empresa_representante']
    rep_ruc = ctx['empresa_rfc']
    cont_nombre = ctx['empresa_contador']
    cont_ruc = ctx['empresa_contador_ruc'] or 'Matrícula Profesional'

    col_rep = [
        Paragraph("________________________________________", estilo_linea),
        Spacer(1, 0.15 * cm),
        Paragraph(f"<b>{rep_nombre}</b>", estilo_firma_nombre),
        Paragraph("REPRESENTANTE LEGAL", estilo_firma_cargo),
        Paragraph(f"C.I. / R.U.C.: {rep_ruc}", estilo_firma_cargo),
    ]

    col_cont = [
        Paragraph("________________________________________", estilo_linea),
        Spacer(1, 0.15 * cm),
        Paragraph(f"<b>{cont_nombre}</b>", estilo_firma_nombre),
        Paragraph("CONTADOR GENERAL", estilo_firma_cargo),
        Paragraph(f"R.U.C. / Matrícula: {cont_ruc}", estilo_firma_cargo),
    ]

    tabla_firmas = Table([[col_rep, "", col_cont]], colWidths=[8.5 * cm, 1.0 * cm, 8.5 * cm])
    tabla_firmas.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 0),
    ]))
    elementos.append(KeepTogether([tabla_firmas]))

    # 7. Pie de Página Sistema
    elementos.append(Spacer(1, 0.8 * cm))
    ts_emision = datetime.now().strftime('%d/%m/%Y %H:%M')
    elementos.append(Paragraph(f"Documento contable oficial emitido por ERP Contable el {ts_emision}. Válido para entidades de control y financieras.", estilo_subtitulo))

    doc.build(elementos)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# EXPORTACIÓN: BALANCE GENERAL EN EXCEL
# ---------------------------------------------------------------------------

def generate_balance_sheet_excel(data: dict, tenant_id: int, date_up_to: str) -> bytes:
    """Genera el Excel corporativo oficial del Balance General."""
    ctx = get_company_context(tenant_id)
    color_hex = ctx['primary_color'].lstrip('#').upper()
    if len(color_hex) != 6:
        color_hex = '1E3A8A'

    wb = Workbook()
    ws = wb.active
    ws.title = "Balance General"
    ws.views.sheetView[0].showGridLines = True

    # Estilos
    font_titulo = Font(name='Segoe UI', size=14, bold=True, color='FFFFFF')
    font_subtitulo = Font(name='Segoe UI', size=9.5, italic=True, color='F0FDF4')
    fill_banner = PatternFill(start_color=color_hex, end_color=color_hex, fill_type='solid')
    align_center = Alignment(horizontal='center', vertical='center')
    align_left = Alignment(horizontal='left', vertical='center')
    align_right = Alignment(horizontal='right', vertical='center')

    borde_delgado = Border(
        left=Side(style='thin', color='E2E8F0'),
        right=Side(style='thin', color='E2E8F0'),
        top=Side(style='thin', color='E2E8F0'),
        bottom=Side(style='thin', color='E2E8F0'),
    )
    borde_total = Border(
        top=Side(style='thin', color='94A3B8'),
        bottom=Side(style='double', color='0F172A'),
    )

    # 1. Banner Superior
    ws.merge_cells('A1:C1')
    ws.merge_cells('A2:C2')
    ws.merge_cells('A3:C3')

    ws['A1'] = ctx['empresa_nombre'].upper()
    ws['A1'].font = font_titulo
    ws['A1'].alignment = align_center

    ws['A2'] = f"R.U.C.: {ctx['empresa_rfc']}  ·  {ctx['empresa_direccion']}"
    ws['A2'].font = font_subtitulo
    ws['A2'].alignment = align_center

    fecha_corte = date_up_to or data.get('date_up_to', '')
    ws['A3'] = f"ESTADO DE SITUACIÓN FINANCIERA AL {fecha_corte} (EN USD)"
    ws['A3'].font = Font(name='Segoe UI', size=10, bold=True, color='FFFFFF')
    ws['A3'].alignment = align_center

    for r in range(1, 4):
        for c in range(1, 4):
            ws.cell(row=r, column=c).fill = fill_banner

    ws.row_dimensions[1].height = 24
    ws.row_dimensions[2].height = 18
    ws.row_dimensions[3].height = 18

    # Fila vacía
    row_idx = 5

    def _render_grupo(nombre_grupo: str, cuentas: list, total_val: float, bg_color: str):
        nonlocal row_idx
        # Encabezado del Grupo
        fill_hdr = PatternFill(start_color=bg_color, end_color=bg_color, fill_type='solid')
        font_hdr = Font(name='Segoe UI', size=10, bold=True, color='FFFFFF')

        ws.cell(row=row_idx, column=1, value="CÓDIGO").font = font_hdr
        ws.cell(row=row_idx, column=2, value=nombre_grupo.upper()).font = font_hdr
        ws.cell(row=row_idx, column=3, value="SALDO (USD)").font = font_hdr
        ws.cell(row=row_idx, column=3).alignment = align_right

        for c in range(1, 4):
            ws.cell(row=row_idx, column=c).fill = fill_hdr
            ws.cell(row=row_idx, column=c).border = borde_delgado
        ws.row_dimensions[row_idx].height = 20
        row_idx += 1

        start_row = row_idx
        if not cuentas:
            ws.cell(row=row_idx, column=1, value="-")
            ws.cell(row=row_idx, column=2, value="Sin movimientos")
            ws.cell(row=row_idx, column=3, value=0.0)
            ws.cell(row=row_idx, column=3).number_format = '$#,##0.00'
            for c in range(1, 4):
                ws.cell(row=row_idx, column=c).border = borde_delgado
            row_idx += 1
        else:
            for item in cuentas:
                ws.cell(row=row_idx, column=1, value=item.get('code') or '-')
                ws.cell(row=row_idx, column=2, value=item.get('name') or '')
                c_val = ws.cell(row=row_idx, column=3, value=float(item.get('balance', 0)))
                c_val.number_format = '$#,##0.00'
                c_val.alignment = align_right
                for c in range(1, 4):
                    ws.cell(row=row_idx, column=c).border = borde_delgado
                row_idx += 1

        # Total Grupo
        ws.cell(row=row_idx, column=1, value="")
        ws.cell(row=row_idx, column=2, value=f"TOTAL {nombre_grupo.upper()}").font = Font(name='Segoe UI', size=10, bold=True)
        c_tot = ws.cell(row=row_idx, column=3, value=float(total_val))
        c_tot.font = Font(name='Segoe UI', size=10, bold=True)
        c_tot.number_format = '$#,##0.00'
        c_tot.alignment = align_right
        
        fill_tot = PatternFill(start_color='F8FAFC', end_color='F8FAFC', fill_type='solid')
        for c in range(1, 4):
            cell = ws.cell(row=row_idx, column=c)
            cell.fill = fill_tot
            cell.border = borde_total
        ws.row_dimensions[row_idx].height = 20
        row_idx += 2

    # Renderizar Activo, Pasivo, Patrimonio
    _render_grupo("1. Activos", data.get('activos', []), data.get('total_activos', 0), color_hex)
    _render_grupo("2. Pasivos", data.get('pasivos', []), data.get('total_pasivos', 0), "D97706")
    _render_grupo("3. Patrimonio", data.get('patrimonio', []), data.get('total_patrimonio', 0), "7C3AED")

    # Total Pasivo + Patrimonio
    tot_pas_pat = data.get('total_pasivos', 0) + data.get('total_patrimonio', 0)
    ws.cell(row=row_idx, column=2, value="TOTAL PASIVO + PATRIMONIO").font = Font(name='Segoe UI', size=11, bold=True)
    c_fin = ws.cell(row=row_idx, column=3, value=float(tot_pas_pat))
    c_fin.font = Font(name='Segoe UI', size=11, bold=True)
    c_fin.number_format = '$#,##0.00'
    c_fin.alignment = align_right
    fill_pas_pat = PatternFill(start_color='E2E8F0', end_color='E2E8F0', fill_type='solid')
    for c in range(1, 4):
        ws.cell(row=row_idx, column=c).fill = fill_pas_pat
        ws.cell(row=row_idx, column=c).border = borde_total
    ws.row_dimensions[row_idx].height = 22
    row_idx += 3

    # Firmas
    ws.cell(row=row_idx, column=1, value="________________________________________")
    ws.cell(row=row_idx, column=3, value="________________________________________")
    ws.cell(row=row_idx, column=1).alignment = align_center
    ws.cell(row=row_idx, column=3).alignment = align_center
    row_idx += 1

    ws.cell(row=row_idx, column=1, value=ctx['empresa_representante']).font = Font(name='Segoe UI', bold=True)
    ws.cell(row=row_idx, column=3, value=ctx['empresa_contador']).font = Font(name='Segoe UI', bold=True)
    ws.cell(row=row_idx, column=1).alignment = align_center
    ws.cell(row=row_idx, column=3).alignment = align_center
    row_idx += 1

    ws.cell(row=row_idx, column=1, value="REPRESENTANTE LEGAL").font = Font(name='Segoe UI', size=9, color='475569')
    ws.cell(row=row_idx, column=3, value="CONTADOR GENERAL").font = Font(name='Segoe UI', size=9, color='475569')
    ws.cell(row=row_idx, column=1).alignment = align_center
    ws.cell(row=row_idx, column=3).alignment = align_center
    row_idx += 1

    ws.cell(row=row_idx, column=1, value=f"C.I. / R.U.C.: {ctx['empresa_rfc']}").font = Font(name='Segoe UI', size=8.5, color='64748B')
    ws.cell(row=row_idx, column=3, value=f"R.U.C. / Matrícula: {ctx['empresa_contador_ruc'] or 'N/A'}").font = Font(name='Segoe UI', size=8.5, color='64748B')
    ws.cell(row=row_idx, column=1).alignment = align_center
    ws.cell(row=row_idx, column=3).alignment = align_center

    # Ajuste de ancho de columnas
    ws.column_dimensions['A'].width = 20
    ws.column_dimensions['B'].width = 50
    ws.column_dimensions['C'].width = 24

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# EXPORTACIÓN: ESTADO DE RESULTADOS (P&L) EN PDF
# ---------------------------------------------------------------------------

def generate_pnl_pdf(data: dict, tenant_id: int, start_date: str, end_date: str) -> bytes:
    """Genera el PDF oficial del Estado de Resultados (P&L)."""
    ctx = get_company_context(tenant_id)
    primary_color = _color_hex(ctx['primary_color'])

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm
    )

    elementos = []

    # Estilos
    estilo_empresa = ParagraphStyle('EmpresaHdr', fontName='Helvetica-Bold', fontSize=14, leading=17, textColor=primary_color)
    estilo_empresa_sub = ParagraphStyle('EmpresaSub', fontName='Helvetica', fontSize=8.5, leading=12, textColor=colors.HexColor('#475569'))
    estilo_titulo = ParagraphStyle('TituloDoc', fontName='Helvetica-Bold', fontSize=12, leading=15, textColor=colors.HexColor('#0F172A'), alignment=TA_CENTER)
    estilo_subtitulo = ParagraphStyle('SubDoc', fontName='Helvetica', fontSize=8.5, leading=11, textColor=colors.HexColor('#64748B'), alignment=TA_CENTER)
    
    estilo_th = ParagraphStyle('TH', fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.white)
    estilo_td = ParagraphStyle('TD', fontName='Helvetica', fontSize=8, leading=10, textColor=colors.HexColor('#1E293B'))
    estilo_td_num = ParagraphStyle('TDNum', fontName='Helvetica', fontSize=8, leading=10, textColor=colors.HexColor('#1E293B'), alignment=TA_RIGHT)
    estilo_tot_label = ParagraphStyle('TotLbl', fontName='Helvetica-Bold', fontSize=8.5, leading=11, textColor=colors.HexColor('#0F172A'))
    estilo_tot_val = ParagraphStyle('TotVal', fontName='Helvetica-Bold', fontSize=8.5, leading=11, textColor=colors.HexColor('#0F172A'), alignment=TA_RIGHT)

    # 1. Cabecera Corporativa
    col_logo = []
    logo_el = _obtener_logo_element(ctx['logo_url'])
    if logo_el:
        col_logo.append(logo_el)
    else:
        col_logo.append(Paragraph(f"<b>{ctx['empresa_nombre']}</b>", estilo_empresa))

    col_info = [
        Paragraph(f"<b>{ctx['empresa_nombre']}</b>", estilo_empresa),
        Paragraph(f"<b>R.U.C.:</b> {ctx['empresa_rfc']}", estilo_empresa_sub),
        Paragraph(f"<b>Dirección:</b> {ctx['empresa_direccion']}", estilo_empresa_sub),
        Paragraph(f"<b>Teléfono:</b> {ctx['empresa_telefono']} &nbsp;|&nbsp; <b>Email:</b> {ctx['empresa_email']}", estilo_empresa_sub),
    ]

    tabla_cabecera = Table([[col_logo, col_info]], colWidths=[5.5 * cm, 12.5 * cm])
    tabla_cabecera.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    elementos.append(tabla_cabecera)
    elementos.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceAfter=8))

    # 2. Título del Reporte
    s_date = start_date or data.get('start_date', '')
    e_date = end_date or data.get('end_date', '')
    elementos.append(Paragraph("ESTADO DE RESULTADOS INTEGRAL (P&L)", estilo_titulo))
    elementos.append(Paragraph(f"Periodo: Del {s_date} al {e_date} &nbsp;·&nbsp; Expresado en Dólares Americanos (USD)", estilo_subtitulo))
    elementos.append(Spacer(1, 0.3 * cm))

    # Helper para tablas contables
    def _crear_tabla_seccion(titulo: str, items: list, total_val: float, color_banner: colors.Color):
        filas = [
            [
                Paragraph("<b>CÓDIGO</b>", estilo_th),
                Paragraph(f"<b>{titulo.upper()}</b>", estilo_th),
                Paragraph("<b>VALOR (USD)</b>", ParagraphStyle('THNum', parent=estilo_th, alignment=TA_RIGHT))
            ]
        ]
        if not items:
            filas.append([
                Paragraph("-", estilo_td),
                Paragraph("<i>No se registran movimientos en el periodo</i>", estilo_td),
                Paragraph("$0.00", estilo_td_num)
            ])
        else:
            for item in items:
                filas.append([
                    Paragraph(item.get('code') or '-', estilo_td),
                    Paragraph(item.get('name') or '', estilo_td),
                    Paragraph(_fmt_money(item.get('balance', 0)), estilo_td_num)
                ])

        filas.append([
            Paragraph("", estilo_tot_label),
            Paragraph(f"TOTAL {titulo.upper()}", estilo_tot_label),
            Paragraph(_fmt_money(total_val), estilo_tot_val)
        ])

        t = Table(filas, colWidths=[3.5 * cm, 10.5 * cm, 4.0 * cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), color_banner),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 4),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#F8FAFC')),
            ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor('#94A3B8')),
        ]))
        return t

    # 3. Secciones: Ingresos y Egresos
    tot_ing = data.get('total_ingresos', 0)
    tot_egr = data.get('total_egresos', 0)
    utilidad = data.get('utilidad_neta', 0)

    elementos.append(_crear_tabla_seccion("4. Ingresos Operacionales", data.get('ingresos', []), tot_ing, colors.HexColor('#059669')))
    elementos.append(Spacer(1, 0.4 * cm))

    elementos.append(_crear_tabla_seccion("5. Costos y Gastos (Egresos)", data.get('egresos', []), tot_egr, colors.HexColor('#E11D48')))
    elementos.append(Spacer(1, 0.4 * cm))

    # 4. Cuadro de Utilidad / Pérdida Neta
    es_ganancia = utilidad >= 0
    titulo_resultado = "UTILIDAD NETA DEL EJERCICIO" if es_ganancia else "PÉRDIDA NETA DEL EJERCICIO"
    bg_resultado = colors.HexColor('#ECFDF5') if es_ganancia else colors.HexColor('#FFF1F2')
    border_resultado = colors.HexColor('#059669') if es_ganancia else colors.HexColor('#E11D48')
    txt_resultado_color = colors.HexColor('#065F46') if es_ganancia else colors.HexColor('#9F1239')

    p_res_title = Paragraph(f"<b>{titulo_resultado}</b>", ParagraphStyle('RT', fontName='Helvetica-Bold', fontSize=10, leading=12, textColor=txt_resultado_color))
    p_res_val = Paragraph(f"<b>{_fmt_money(utilidad)}</b>", ParagraphStyle('RV', fontName='Helvetica-Bold', fontSize=11, leading=13, textColor=txt_resultado_color, alignment=TA_RIGHT))

    tabla_resultado = Table([[Paragraph("", estilo_td), p_res_title, p_res_val]], colWidths=[3.5 * cm, 10.5 * cm, 4.0 * cm])
    tabla_resultado.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg_resultado),
        ('BOX', (0, 0), (-1, -1), 1.5, border_resultado),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    elementos.append(tabla_resultado)
    elementos.append(Spacer(1, 1.2 * cm))

    # 5. Firmas Oficiales
    estilo_firma_nombre = ParagraphStyle('FN', fontName='Helvetica-Bold', fontSize=8.5, leading=11, alignment=TA_CENTER)
    estilo_firma_cargo = ParagraphStyle('FC', fontName='Helvetica', fontSize=7.5, leading=10, textColor=colors.HexColor('#475569'), alignment=TA_CENTER)
    estilo_linea = ParagraphStyle('FL', fontName='Helvetica', fontSize=8, leading=10, textColor=colors.HexColor('#94A3B8'), alignment=TA_CENTER)

    rep_nombre = ctx['empresa_representante']
    rep_ruc = ctx['empresa_rfc']
    cont_nombre = ctx['empresa_contador']
    cont_ruc = ctx['empresa_contador_ruc'] or 'Matrícula Profesional'

    col_rep = [
        Paragraph("________________________________________", estilo_linea),
        Spacer(1, 0.15 * cm),
        Paragraph(f"<b>{rep_nombre}</b>", estilo_firma_nombre),
        Paragraph("REPRESENTANTE LEGAL", estilo_firma_cargo),
        Paragraph(f"C.I. / R.U.C.: {rep_ruc}", estilo_firma_cargo),
    ]

    col_cont = [
        Paragraph("________________________________________", estilo_linea),
        Spacer(1, 0.15 * cm),
        Paragraph(f"<b>{cont_nombre}</b>", estilo_firma_nombre),
        Paragraph("CONTADOR GENERAL", estilo_firma_cargo),
        Paragraph(f"R.U.C. / Matrícula: {cont_ruc}", estilo_firma_cargo),
    ]

    tabla_firmas = Table([[col_rep, "", col_cont]], colWidths=[8.5 * cm, 1.0 * cm, 8.5 * cm])
    tabla_firmas.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 0),
    ]))
    elementos.append(KeepTogether([tabla_firmas]))

    # 6. Pie de Página Sistema
    elementos.append(Spacer(1, 0.8 * cm))
    ts_emision = datetime.now().strftime('%d/%m/%Y %H:%M')
    elementos.append(Paragraph(f"Documento contable oficial emitido por ERP Contable el {ts_emision}. Válido para entidades de control y financieras.", estilo_subtitulo))

    doc.build(elementos)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# EXPORTACIÓN: ESTADO DE RESULTADOS (P&L) EN EXCEL
# ---------------------------------------------------------------------------

def generate_pnl_excel(data: dict, tenant_id: int, start_date: str, end_date: str) -> bytes:
    """Genera el Excel corporativo oficial del Estado de Resultados (P&L)."""
    ctx = get_company_context(tenant_id)
    color_hex = ctx['primary_color'].lstrip('#').upper()
    if len(color_hex) != 6:
        color_hex = '1E3A8A'

    wb = Workbook()
    ws = wb.active
    ws.title = "Estado de Resultados"
    ws.views.sheetView[0].showGridLines = True

    font_titulo = Font(name='Segoe UI', size=14, bold=True, color='FFFFFF')
    font_subtitulo = Font(name='Segoe UI', size=9.5, italic=True, color='F0FDF4')
    fill_banner = PatternFill(start_color=color_hex, end_color=color_hex, fill_type='solid')
    align_center = Alignment(horizontal='center', vertical='center')
    align_right = Alignment(horizontal='right', vertical='center')

    borde_delgado = Border(
        left=Side(style='thin', color='E2E8F0'),
        right=Side(style='thin', color='E2E8F0'),
        top=Side(style='thin', color='E2E8F0'),
        bottom=Side(style='thin', color='E2E8F0'),
    )
    borde_total = Border(
        top=Side(style='thin', color='94A3B8'),
        bottom=Side(style='double', color='0F172A'),
    )

    # 1. Banner Superior
    ws.merge_cells('A1:C1')
    ws.merge_cells('A2:C2')
    ws.merge_cells('A3:C3')

    ws['A1'] = ctx['empresa_nombre'].upper()
    ws['A1'].font = font_titulo
    ws['A1'].alignment = align_center

    ws['A2'] = f"R.U.C.: {ctx['empresa_rfc']}  ·  {ctx['empresa_direccion']}"
    ws['A2'].font = font_subtitulo
    ws['A2'].alignment = align_center

    s_date = start_date or data.get('start_date', '')
    e_date = end_date or data.get('end_date', '')
    ws['A3'] = f"ESTADO DE RESULTADOS INTEGRAL (DEL {s_date} AL {e_date}) - USD"
    ws['A3'].font = Font(name='Segoe UI', size=10, bold=True, color='FFFFFF')
    ws['A3'].alignment = align_center

    for r in range(1, 4):
        for c in range(1, 4):
            ws.cell(row=r, column=c).fill = fill_banner

    ws.row_dimensions[1].height = 24
    ws.row_dimensions[2].height = 18
    ws.row_dimensions[3].height = 18

    row_idx = 5

    def _render_grupo(nombre_grupo: str, cuentas: list, total_val: float, bg_color: str):
        nonlocal row_idx
        fill_hdr = PatternFill(start_color=bg_color, end_color=bg_color, fill_type='solid')
        font_hdr = Font(name='Segoe UI', size=10, bold=True, color='FFFFFF')

        ws.cell(row=row_idx, column=1, value="CÓDIGO").font = font_hdr
        ws.cell(row=row_idx, column=2, value=nombre_grupo.upper()).font = font_hdr
        ws.cell(row=row_idx, column=3, value="VALOR (USD)").font = font_hdr
        ws.cell(row=row_idx, column=3).alignment = align_right

        for c in range(1, 4):
            ws.cell(row=row_idx, column=c).fill = fill_hdr
            ws.cell(row=row_idx, column=c).border = borde_delgado
        ws.row_dimensions[row_idx].height = 20
        row_idx += 1

        if not cuentas:
            ws.cell(row=row_idx, column=1, value="-")
            ws.cell(row=row_idx, column=2, value="Sin movimientos")
            ws.cell(row=row_idx, column=3, value=0.0)
            ws.cell(row=row_idx, column=3).number_format = '$#,##0.00'
            for c in range(1, 4):
                ws.cell(row=row_idx, column=c).border = borde_delgado
            row_idx += 1
        else:
            for item in cuentas:
                ws.cell(row=row_idx, column=1, value=item.get('code') or '-')
                ws.cell(row=row_idx, column=2, value=item.get('name') or '')
                c_val = ws.cell(row=row_idx, column=3, value=float(item.get('balance', 0)))
                c_val.number_format = '$#,##0.00'
                c_val.alignment = align_right
                for c in range(1, 4):
                    ws.cell(row=row_idx, column=c).border = borde_delgado
                row_idx += 1

        ws.cell(row=row_idx, column=1, value="")
        ws.cell(row=row_idx, column=2, value=f"TOTAL {nombre_grupo.upper()}").font = Font(name='Segoe UI', size=10, bold=True)
        c_tot = ws.cell(row=row_idx, column=3, value=float(total_val))
        c_tot.font = Font(name='Segoe UI', size=10, bold=True)
        c_tot.number_format = '$#,##0.00'
        c_tot.alignment = align_right

        fill_tot = PatternFill(start_color='F8FAFC', end_color='F8FAFC', fill_type='solid')
        for c in range(1, 4):
            cell = ws.cell(row=row_idx, column=c)
            cell.fill = fill_tot
            cell.border = borde_total
        ws.row_dimensions[row_idx].height = 20
        row_idx += 2

    # Render Ingresos y Egresos
    _render_grupo("4. Ingresos Operacionales", data.get('ingresos', []), data.get('total_ingresos', 0), "059669")
    _render_grupo("5. Costos y Gastos (Egresos)", data.get('egresos', []), data.get('total_egresos', 0), "E11D48")

    # Resultado Final
    utilidad = data.get('utilidad_neta', 0)
    label_res = "UTILIDAD NETA DEL EJERCICIO" if utilidad >= 0 else "PÉRDIDA NETA DEL EJERCICIO"
    ws.cell(row=row_idx, column=2, value=label_res).font = Font(name='Segoe UI', size=11, bold=True)
    c_res = ws.cell(row=row_idx, column=3, value=float(utilidad))
    c_res.font = Font(name='Segoe UI', size=11, bold=True)
    c_res.number_format = '$#,##0.00'
    c_res.alignment = align_right

    bg_res = 'ECFDF5' if utilidad >= 0 else 'FFF1F2'
    fill_res = PatternFill(start_color=bg_res, end_color=bg_res, fill_type='solid')
    for c in range(1, 4):
        ws.cell(row=row_idx, column=c).fill = fill_res
        ws.cell(row=row_idx, column=c).border = borde_total
    ws.row_dimensions[row_idx].height = 22
    row_idx += 3

    # Firmas
    ws.cell(row=row_idx, column=1, value="________________________________________")
    ws.cell(row=row_idx, column=3, value="________________________________________")
    ws.cell(row=row_idx, column=1).alignment = align_center
    ws.cell(row=row_idx, column=3).alignment = align_center
    row_idx += 1

    ws.cell(row=row_idx, column=1, value=ctx['empresa_representante']).font = Font(name='Segoe UI', bold=True)
    ws.cell(row=row_idx, column=3, value=ctx['empresa_contador']).font = Font(name='Segoe UI', bold=True)
    ws.cell(row=row_idx, column=1).alignment = align_center
    ws.cell(row=row_idx, column=3).alignment = align_center
    row_idx += 1

    ws.cell(row=row_idx, column=1, value="REPRESENTANTE LEGAL").font = Font(name='Segoe UI', size=9, color='475569')
    ws.cell(row=row_idx, column=3, value="CONTADOR GENERAL").font = Font(name='Segoe UI', size=9, color='475569')
    ws.cell(row=row_idx, column=1).alignment = align_center
    ws.cell(row=row_idx, column=3).alignment = align_center
    row_idx += 1

    ws.cell(row=row_idx, column=1, value=f"C.I. / R.U.C.: {ctx['empresa_rfc']}").font = Font(name='Segoe UI', size=8.5, color='64748B')
    ws.cell(row=row_idx, column=3, value=f"R.U.C. / Matrícula: {ctx['empresa_contador_ruc'] or 'N/A'}").font = Font(name='Segoe UI', size=8.5, color='64748B')
    ws.cell(row=row_idx, column=1).alignment = align_center
    ws.cell(row=row_idx, column=3).alignment = align_center

    # Ajuste columnas
    ws.column_dimensions['A'].width = 20
    ws.column_dimensions['B'].width = 50
    ws.column_dimensions['C'].width = 24

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
