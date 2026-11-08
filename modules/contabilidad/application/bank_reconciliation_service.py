"""
Servicio de Aplicación: Conciliación Bancaria Automática.
- Lector de extractos bancarios en Excel (.xlsx) y CSV.
- Algoritmo de auto-matching inteligente contra el Libro Mayor Contable.
- Conciliación manual de partidas.
- Generador de Acta Oficial de Conciliación Bancaria en PDF y Excel con firmas.
"""

import io
import csv
from decimal import Decimal
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional

from django.db import transaction
from django.db.models import Sum, Q
from django.conf import settings

from openpyxl import load_workbook, Workbook
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

from .financial_reports_exporter import get_company_context, _obtener_logo_element, _color_hex, _fmt_money
from ..infrastructure.django_models import (
    BankAccountModel, AccountModel, JournalEntryModel, JournalEntryLineModel,
    BankReconciliationModel, BankReconciliationItemModel
)


class BankReconciliationService:

    @staticmethod
    def parse_statement_file(file_obj, filename: str) -> List[Dict[str, Any]]:
        """
        Lee el extracto bancario en Excel (.xlsx) o CSV e identifica automáticamente
        las columnas: Fecha, Referencia, Descripción, Débito (Retiro), Crédito (Depósito), Saldo.
        """
        fn_lower = filename.lower()
        if fn_lower.endswith('.xlsx') or fn_lower.endswith('.xls'):
            return BankReconciliationService._parse_excel(file_obj)
        elif fn_lower.endswith('.csv') or fn_lower.endswith('.txt'):
            return BankReconciliationService._parse_csv(file_obj)
        else:
            raise ValueError("Formato de archivo no soportado. Suba un archivo Excel (.xlsx) o .csv")

    @staticmethod
    def _parse_excel(file_obj) -> List[Dict[str, Any]]:
        wb = load_workbook(filename=file_obj, data_only=True)
        sheet = wb.active
        rows = list(sheet.iter_rows(values_only=True))

        if not rows:
            return []

        # Localizar la fila de encabezados
        header_row_idx = -1
        col_map = {}

        for idx, row in enumerate(rows[:15]): # buscar en las primeras 15 filas
            row_str = [str(c or '').lower().strip() for c in row]
            has_date = any('fech' in c for c in row_str)
            has_money = any(any(m in c for m in ['monto', 'valor', 'debit', 'credit', 'retiro', 'deposito', 'saldo']) for c in row_str)
            if has_date and has_money:
                header_row_idx = idx
                for c_idx, cell_val in enumerate(row_str):
                    if 'fech' in cell_val and 'date' not in col_map:
                        col_map['date'] = c_idx
                    elif any(r in cell_val for r in ['ref', 'doc', 'comprobante', 'cheque']) and 'ref' not in col_map:
                        col_map['ref'] = c_idx
                    elif any(d in cell_val for d in ['descrip', 'concep', 'detalle']) and 'desc' not in col_map:
                        col_map['desc'] = c_idx
                    elif any(deb in cell_val for deb in ['debit', 'retiro', 'egreso', 'cargo']) and 'debit' not in col_map:
                        col_map['debit'] = c_idx
                    elif any(cred in cell_val for cred in ['credit', 'deposito', 'ingreso', 'abono']) and 'credit' not in col_map:
                        col_map['credit'] = c_idx
                    elif any(v in cell_val for v in ['valor', 'monto', 'importe']) and 'amount' not in col_map:
                        col_map['amount'] = c_idx
                    elif 'saldo' in cell_val and 'balance' not in col_map:
                        col_map['balance'] = c_idx
                break

        # Si no encontró encabezados claros, asumir mapeo posicional estándar
        if header_row_idx == -1:
            header_row_idx = 0
            col_map = {'date': 0, 'desc': 1, 'ref': 2, 'debit': 3, 'credit': 4, 'balance': 5}

        parsed_items = []
        for row in rows[header_row_idx + 1:]:
            if not row or all(c is None for c in row):
                continue

            raw_date = row[col_map.get('date', 0)] if 'date' in col_map else None
            parsed_date = BankReconciliationService._normalize_date(raw_date)
            if not parsed_date:
                continue

            desc = str(row[col_map['desc']] or '').strip() if 'desc' in col_map and col_map['desc'] < len(row) else 'Movimiento bancario'
            ref = str(row[col_map['ref']] or '').strip() if 'ref' in col_map and col_map['ref'] < len(row) else ''

            # Extraer montos
            debit_val = Decimal('0.00')
            credit_val = Decimal('0.00')

            if 'debit' in col_map and col_map['debit'] < len(row):
                debit_val = BankReconciliationService._to_decimal(row[col_map['debit']])
            if 'credit' in col_map and col_map['credit'] < len(row):
                credit_val = BankReconciliationService._to_decimal(row[col_map['credit']])

            # Si viene en una sola columna 'amount' con signo (+ / -)
            if debit_val == 0 and credit_val == 0 and 'amount' in col_map and col_map['amount'] < len(row):
                amt = BankReconciliationService._to_decimal(row[col_map['amount']])
                if amt < 0:
                    debit_val = abs(amt)
                else:
                    credit_val = amt

            if debit_val > 0:
                amount = debit_val
                movement_type = 'debit' # Retiro de banco
            elif credit_val > 0:
                amount = credit_val
                movement_type = 'credit' # Depósito en banco
            else:
                continue

            parsed_items.append({
                'date': parsed_date.strftime('%Y-%m-%d'),
                'reference': ref,
                'description': desc,
                'amount': float(amount),
                'movement_type': movement_type,
            })

        return parsed_items

    @staticmethod
    def _parse_csv(file_obj) -> List[Dict[str, Any]]:
        file_obj.seek(0)
        raw_text = file_obj.read().decode('utf-8', errors='ignore')
        lines = [l for l in raw_text.splitlines() if l.strip()]
        if not lines:
            return []

        delimiter = ';' if ';' in lines[0] else ','
        reader = csv.reader(lines, delimiter=delimiter)
        rows = list(reader)

        # Usar la misma lógica de mapeo
        header_row_idx = 0
        col_map = {'date': 0, 'desc': 1, 'ref': 2, 'debit': 3, 'credit': 4}

        for idx, row in enumerate(rows[:10]):
            r_lower = [c.lower() for c in row]
            if any('fech' in c for c in r_lower):
                header_row_idx = idx
                for c_idx, cell_val in enumerate(r_lower):
                    if 'fech' in cell_val: col_map['date'] = c_idx
                    elif any(r in cell_val for r in ['ref', 'doc', 'cheque']): col_map['ref'] = c_idx
                    elif any(d in cell_val for d in ['desc', 'detal', 'concep']): col_map['desc'] = c_idx
                    elif any(deb in cell_val for deb in ['deb', 'retir', 'egres']): col_map['debit'] = c_idx
                    elif any(cr in cell_val for cr in ['cred', 'depo', 'ingres']): col_map['credit'] = c_idx
                break

        parsed = []
        for row in rows[header_row_idx + 1:]:
            if not row or len(row) < 2: continue
            parsed_date = BankReconciliationService._normalize_date(row[col_map.get('date', 0)])
            if not parsed_date: continue

            desc = row[col_map['desc']].strip() if 'desc' in col_map and col_map['desc'] < len(row) else ''
            ref = row[col_map['ref']].strip() if 'ref' in col_map and col_map['ref'] < len(row) else ''
            deb = BankReconciliationService._to_decimal(row[col_map['debit']]) if 'debit' in col_map and col_map['debit'] < len(row) else Decimal('0')
            cred = BankReconciliationService._to_decimal(row[col_map['credit']]) if 'credit' in col_map and col_map['credit'] < len(row) else Decimal('0')

            if deb > 0:
                m_type = 'debit'
                amt = deb
            elif cred > 0:
                m_type = 'credit'
                amt = cred
            else:
                continue

            parsed.append({
                'date': parsed_date.strftime('%Y-%m-%d'),
                'reference': ref,
                'description': desc,
                'amount': float(amt),
                'movement_type': m_type,
            })
        return parsed

    @staticmethod
    def _normalize_date(val) -> Optional[date]:
        if not val:
            return None
        if isinstance(val, (date, datetime)):
            return val.date() if isinstance(val, datetime) else val
        s = str(val).strip()
        # Formatos comunes: YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d', '%d.%m.%Y'):
            try:
                return datetime.strptime(s[:10], fmt).date()
            except ValueError:
                pass
        return None

    @staticmethod
    def _to_decimal(val) -> Decimal:
        if val is None:
            return Decimal('0.00')
        s = str(val).strip().replace('$', '').replace(' ', '')
        if ',' in s and '.' in s:
            s = s.replace(',', '') # 1,250.50
        elif ',' in s and '.' not in s:
            s = s.replace(',', '.') # 1250,50
        try:
            return Decimal(s)
        except Exception:
            return Decimal('0.00')

    # -----------------------------------------------------------------------
    # PROCESO COMPLETO DE CONCILIACIÓN
    # -----------------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def create_and_automatch_reconciliation(
        tenant_id: int,
        bank_account_id: int,
        period_start: str,
        period_end: str,
        statement_balance: float,
        statement_items: List[Dict[str, Any]],
        notes: str = ''
    ) -> BankReconciliationModel:
        """
        Crea la cabecera de conciliación, guarda las partidas del extracto,
        extrae los asientos del Libro Mayor para esa cuenta bancaria y ejecuta
        el motor de auto-cruce inteligente.
        """
        bank_acc = BankAccountModel.objects.filter(id=bank_account_id, tenant_id=tenant_id).select_related('account').first()
        if not bank_acc:
            raise ValueError("Cuenta bancaria no encontrada.")

        p_start = datetime.strptime(period_start, '%Y-%m-%d').date()
        p_end = datetime.strptime(period_end, '%Y-%m-%d').date()

        # 1. Obtener saldo contable acumulado a la fecha de fin (Libro Mayor)
        # Saldo Banco en Contabilidad = Total Débitos - Total Créditos (Activo)
        qs_ledger = JournalEntryLineModel.objects.filter(
            entry__tenant_id=tenant_id,
            account_id=bank_acc.account_id,
            entry__date__lte=p_end
        )
        agg_ledger = qs_ledger.aggregate(tot_debit=Sum('debit'), tot_credit=Sum('credit'))
        book_balance = (agg_ledger['tot_debit'] or Decimal('0')) - (agg_ledger['tot_credit'] or Decimal('0'))

        # Crear la cabecera
        recon = BankReconciliationModel.objects.create(
            tenant_id=tenant_id,
            bank_account=bank_acc,
            period_start=p_start,
            period_end=p_end,
            statement_balance=Decimal(str(statement_balance)),
            book_balance=book_balance,
            notes=notes
        )

        # 2. Insertar partidas del Extracto Bancario
        created_stmt_items = []
        for s in statement_items:
            item = BankReconciliationItemModel.objects.create(
                reconciliation=recon,
                source='statement',
                date=datetime.strptime(s['date'], '%Y-%m-%d').date(),
                reference=s.get('reference', ''),
                description=s.get('description', ''),
                amount=Decimal(str(s['amount'])),
                movement_type=s['movement_type']
            )
            created_stmt_items.append(item)

        # 3. Insertar partidas de los Libros Contables del período
        qs_period_ledger = JournalEntryLineModel.objects.filter(
            entry__tenant_id=tenant_id,
            account_id=bank_acc.account_id,
            entry__date__gte=p_start,
            entry__date__lte=p_end
        ).select_related('entry').order_by('entry__date', 'id')

        created_book_items = []
        for line in qs_period_ledger:
            # En libros contables:
            # Débito = Ingreso/Depósito (equivale a 'credit' en banco)
            # Crédito = Egreso/Cheque/Transferencia (equivale a 'debit' en banco)
            if line.debit > 0:
                amt = line.debit
                m_type = 'credit' # Ingreso contable
            elif line.credit > 0:
                amt = line.credit
                m_type = 'debit' # Egreso contable
            else:
                continue

            b_item = BankReconciliationItemModel.objects.create(
                reconciliation=recon,
                source='book',
                date=line.entry.date,
                reference=line.entry.reference,
                description=line.entry.description,
                amount=amt,
                movement_type=m_type,
                journal_entry_line=line
            )
            created_book_items.append(b_item)

        # 4. MOTOR DE AUTO-MATCHING (Cruce Automático)
        BankReconciliationService._execute_automatch(created_stmt_items, created_book_items)

        # 5. Calcular cifras de cierre
        BankReconciliationService.recalculate_totals(recon)

        return recon

    @staticmethod
    def _execute_automatch(stmt_items: List[BankReconciliationItemModel], book_items: List[BankReconciliationItemModel]):
        """
        Ejecuta el cruce automático:
        Paso 1: Monto idéntico y Referencia coincidente (Exacto)
        Paso 2: Monto idéntico y Fecha con diferencia <= 3 días (Cruce por fecha)
        """
        # Paso 1: Match Exacto (Monto + Referencia)
        for s in stmt_items:
            if s.is_matched or not s.reference:
                continue
            for b in book_items:
                if b.is_matched or not b.reference:
                    continue
                if s.amount == b.amount and s.movement_type == b.movement_type:
                    # Comparar si las referencias coinciden o se contienen
                    if s.reference.lower() in b.reference.lower() or b.reference.lower() in s.reference.lower():
                        s.is_matched = True
                        s.matched_with_id = b.id
                        s.match_method = 'exact'
                        s.save(update_fields=['is_matched', 'matched_with_id', 'match_method'])

                        b.is_matched = True
                        b.matched_with_id = s.id
                        b.match_method = 'exact'
                        b.save(update_fields=['is_matched', 'matched_with_id', 'match_method'])
                        break

        # Paso 2: Match por Monto y Fecha cercana (+/- 3 días)
        for s in stmt_items:
            if s.is_matched:
                continue
            for b in book_items:
                if b.is_matched:
                    continue
                if s.amount == b.amount and s.movement_type == b.movement_type:
                    dias_dif = abs((s.date - b.date).days)
                    if dias_dif <= 3:
                        s.is_matched = True
                        s.matched_with_id = b.id
                        s.match_method = 'amount_date'
                        s.save(update_fields=['is_matched', 'matched_with_id', 'match_method'])

                        b.is_matched = True
                        b.matched_with_id = s.id
                        b.match_method = 'amount_date'
                        b.save(update_fields=['is_matched', 'matched_with_id', 'match_method'])
                        break

    @staticmethod
    def recalculate_totals(recon: BankReconciliationModel):
        """
        Calcula la ecuación contable de conciliación:
        Saldo según Extracto
        (+) Depósitos en tránsito (Libros no conciliados tipo crédito)
        (-) Cheques/Transferencias en tránsito (Libros no conciliados tipo débito)
        (=) Saldo Conciliado
        Diferencia = Saldo Conciliado - Saldo según Libros
        """
        unmatched_books = recon.items.filter(source='book', is_matched=False)
        dep_transito = unmatched_books.filter(movement_type='credit').aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
        cheq_transito = unmatched_books.filter(movement_type='debit').aggregate(s=Sum('amount'))['s'] or Decimal('0.00')

        saldo_conciliado = recon.statement_balance + dep_transito - cheq_transito
        diferencia = saldo_conciliado - recon.book_balance

        recon.reconciled_balance = saldo_conciliado
        recon.difference = diferencia

        if abs(diferencia) < Decimal('0.01'):
            recon.status = 'reconciled'
        else:
            recon.status = 'draft'

        recon.save(update_fields=['reconciled_balance', 'difference', 'status'])

    # -----------------------------------------------------------------------
    # EXPORTACIÓN OFICIAL: ACTA DE CONCILIACIÓN BANCARIA (PDF)
    # -----------------------------------------------------------------------

    @staticmethod
    def generate_pdf_report(recon_id: int, tenant_id: int) -> bytes:
        recon = BankReconciliationModel.objects.filter(id=recon_id, tenant_id=tenant_id).select_related('bank_account').first()
        if not recon:
            raise ValueError("Conciliación bancaria no encontrada.")

        ctx = get_company_context(tenant_id)
        primary_color = _color_hex(ctx['primary_color'])

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=1.5 * cm,
            leftMargin=1.5 * cm,
            topMargin=1.5 * cm,
            bottomMargin=1.5 * cm
        )

        elementos = []
        styles = getSampleStyleSheet()

        estilo_empresa = ParagraphStyle('EmpresaHdr', fontName='Helvetica-Bold', fontSize=14, leading=17, textColor=primary_color)
        estilo_empresa_sub = ParagraphStyle('EmpresaSub', fontName='Helvetica', fontSize=8.5, leading=12, textColor=colors.HexColor('#475569'))
        estilo_titulo = ParagraphStyle('TituloDoc', fontName='Helvetica-Bold', fontSize=12, leading=15, textColor=colors.HexColor('#0F172A'), alignment=TA_CENTER)
        estilo_subtitulo = ParagraphStyle('SubDoc', fontName='Helvetica', fontSize=8.5, leading=11, textColor=colors.HexColor('#64748B'), alignment=TA_CENTER)

        estilo_th = ParagraphStyle('TH', fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.white)
        estilo_td = ParagraphStyle('TD', fontName='Helvetica', fontSize=8, leading=10, textColor=colors.HexColor('#1E293B'))
        estilo_td_num = ParagraphStyle('TDNum', fontName='Helvetica', fontSize=8, leading=10, textColor=colors.HexColor('#1E293B'), alignment=TA_RIGHT)

        # 1. Cabecera
        col_logo = []
        logo_el = _obtener_logo_element(ctx['logo_url'])
        if logo_el:
            col_logo.append(logo_el)
        else:
            col_logo.append(Paragraph(f"<b>{ctx['empresa_nombre']}</b>", estilo_empresa))

        col_info = [
            Paragraph(f"<b>{ctx['empresa_nombre']}</b>", estilo_empresa),
            Paragraph(f"<b>R.U.C.:</b> {ctx['empresa_rfc']}  ·  <b>Cuenta:</b> {recon.bank_account.bank_name} {recon.bank_account.account_number}", estilo_empresa_sub),
            Paragraph(f"<b>Período:</b> Del {recon.period_start.strftime('%d/%m/%Y')} al {recon.period_end.strftime('%d/%m/%Y')}", estilo_empresa_sub),
        ]

        tabla_cabecera = Table([[col_logo, col_info]], colWidths=[5.5 * cm, 12.5 * cm])
        tabla_cabecera.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elementos.append(tabla_cabecera)
        elementos.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceAfter=8))

        # 2. Título
        elementos.append(Paragraph("ACTA OFICIAL DE CONCILIACIÓN BANCARIA", estilo_titulo))
        elementos.append(Paragraph(f"Cuenta {recon.bank_account.get_account_type_display()} Nro. {recon.bank_account.account_number} · Moneda: USD", estilo_subtitulo))
        elementos.append(Spacer(1, 0.4 * cm))

        # 3. Cuadro de Resumen Contable (Fórmula de Conciliación)
        unmatched_books = recon.items.filter(source='book', is_matched=False)
        dep_transito = unmatched_books.filter(movement_type='credit').aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
        cheq_transito = unmatched_books.filter(movement_type='debit').aggregate(s=Sum('amount'))['s'] or Decimal('0.00')

        cuadrado = abs(recon.difference) < Decimal('0.01')
        color_res = colors.HexColor('#065F46') if cuadrado else colors.HexColor('#9F1239')
        bg_res = colors.HexColor('#ECFDF5') if cuadrado else colors.HexColor('#FFF1F2')

        filas_resumen = [
            [Paragraph("<b>SALDO SEGÚN EXTRACTO BANCARIO:</b>", estilo_td), Paragraph(f"<b>{_fmt_money(recon.statement_balance)}</b>", estilo_td_num)],
            [Paragraph("(+) Depósitos en tránsito (registrados en libros, pendientes en banco)", estilo_td), Paragraph(_fmt_money(dep_transito), estilo_td_num)],
            [Paragraph("(-) Cheques y transferencias en tránsito (girados en libros, no cobrados)", estilo_td), Paragraph(f"({_fmt_money(cheq_transito)})", estilo_td_num)],
            [Paragraph("<b>(=) SALDO CONCILIADO:</b>", estilo_td), Paragraph(f"<b>{_fmt_money(recon.reconciled_balance)}</b>", estilo_td_num)],
            [Paragraph("<b>SALDO SEGÚN LIBRO MAYOR CONTABLE:</b>", estilo_td), Paragraph(f"<b>{_fmt_money(recon.book_balance)}</b>", estilo_td_num)],
            [Paragraph("<b>DIFERENCIA DE CONCILIACIÓN:</b>", ParagraphStyle('D', fontName='Helvetica-Bold', fontSize=8.5, textColor=color_res)), Paragraph(f"<b>{_fmt_money(recon.difference)}</b>", ParagraphStyle('DV', fontName='Helvetica-Bold', fontSize=8.5, textColor=color_res, alignment=TA_RIGHT))],
        ]

        t_resumen = Table(filas_resumen, colWidths=[13.5 * cm, 4.5 * cm])
        t_resumen.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('PADDING', (0, 0), (-1, -1), 5),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F8FAFC')),
            ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#F1F5F9')),
            ('BACKGROUND', (0, -1), (-1, -1), bg_res),
        ]))
        elementos.append(t_resumen)
        elementos.append(Spacer(1, 0.5 * cm))

        # 4. Tabla de Partidas Pendientes
        elementos.append(Paragraph("<b>Detalle de Partidas en Tránsito y Pendientes:</b>", ParagraphStyle('Sec', fontName='Helvetica-Bold', fontSize=9, textColor=primary_color)))
        elementos.append(Spacer(1, 0.15 * cm))

        filas_detalles = [
            [Paragraph("<b>FECHA</b>", estilo_th), Paragraph("<b>TIPO / ORIGEN</b>", estilo_th), Paragraph("<b>DESCRIPCIÓN / REFERENCIA</b>", estilo_th), Paragraph("<b>MONTO (USD)</b>", ParagraphStyle('THNum', parent=estilo_th, alignment=TA_RIGHT))]
        ]

        items_pendientes = recon.items.filter(is_matched=False).order_by('date')[:25]
        if not items_pendientes.exists():
            filas_detalles.append([
                Paragraph("-", estilo_td),
                Paragraph("Sin partidas pendientes", estilo_td),
                Paragraph("Todas las transacciones se encuentran debidamente conciliadas.", estilo_td),
                Paragraph("$0.00", estilo_td_num)
            ])
        else:
            for p in items_pendientes:
                origen_lbl = "Libros (Depósito Tránsito)" if p.source == 'book' and p.movement_type == 'credit' else ("Libros (Cheque Tránsito)" if p.source == 'book' else "Extracto (Pendiente Contabilizar)")
                filas_detalles.append([
                    Paragraph(p.date.strftime('%d/%m/%Y'), estilo_td),
                    Paragraph(origen_lbl, estilo_td),
                    Paragraph(f"{p.reference} - {p.description}"[:45], estilo_td),
                    Paragraph(_fmt_money(p.amount), estilo_td_num)
                ])

        t_detalles = Table(filas_detalles, colWidths=[2.5 * cm, 5.0 * cm, 7.5 * cm, 3.0 * cm])
        t_detalles.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), primary_color),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        elementos.append(t_detalles)
        elementos.append(Spacer(1, 1.2 * cm))

        # 5. Firmas Oficiales
        rep_nombre = ctx['empresa_representante']
        rep_ruc = ctx['empresa_rfc']
        cont_nombre = ctx['empresa_contador']
        cont_ruc = ctx['empresa_contador_ruc'] or 'Matrícula Profesional'

        estilo_firma_nombre = ParagraphStyle('FN', fontName='Helvetica-Bold', fontSize=8.5, leading=11, alignment=TA_CENTER)
        estilo_firma_cargo = ParagraphStyle('FC', fontName='Helvetica', fontSize=7.5, leading=10, textColor=colors.HexColor('#475569'), alignment=TA_CENTER)
        estilo_linea = ParagraphStyle('FL', fontName='Helvetica', fontSize=8, leading=10, textColor=colors.HexColor('#94A3B8'), alignment=TA_CENTER)

        col_rep = [
            Paragraph("________________________________________", estilo_linea),
            Spacer(1, 0.15 * cm),
            Paragraph(f"<b>{rep_nombre}</b>", estilo_firma_nombre),
            Paragraph("REPRESENTANTE LEGAL / GERENTE", estilo_firma_cargo),
            Paragraph(f"C.I. / R.U.C.: {rep_ruc}", estilo_firma_cargo),
        ]

        col_cont = [
            Paragraph("________________________________________", estilo_linea),
            Spacer(1, 0.15 * cm),
            Paragraph(f"<b>{cont_nombre}</b>", estilo_firma_nombre),
            Paragraph("CONTADOR GENERAL / AUDITOR", estilo_firma_cargo),
            Paragraph(f"R.U.C. / Matrícula: {cont_ruc}", estilo_firma_cargo),
        ]

        tabla_firmas = Table([[col_rep, "", col_cont]], colWidths=[8.5 * cm, 1.0 * cm, 8.5 * cm])
        tabla_firmas.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('PADDING', (0, 0), (-1, -1), 0),
        ]))
        elementos.append(KeepTogether([tabla_firmas]))

        doc.build(elementos)
        return buffer.getvalue()

    # -----------------------------------------------------------------------
    # EXPORTACIÓN OFICIAL: ACTA DE CONCILIACIÓN EN EXCEL
    # -----------------------------------------------------------------------

    @staticmethod
    def generate_excel_report(recon_id: int, tenant_id: int) -> bytes:
        recon = BankReconciliationModel.objects.filter(id=recon_id, tenant_id=tenant_id).select_related('bank_account').first()
        if not recon:
            raise ValueError("Conciliación no encontrada.")

        ctx = get_company_context(tenant_id)
        color_hex = ctx['primary_color'].lstrip('#').upper()
        if len(color_hex) != 6: color_hex = '1E3A8A'

        wb = Workbook()
        ws = wb.active
        ws.title = "Conciliación Bancaria"
        ws.views.sheetView[0].showGridLines = True

        font_titulo = Font(name='Segoe UI', size=13, bold=True, color='FFFFFF')
        fill_banner = PatternFill(start_color=color_hex, end_color=color_hex, fill_type='solid')
        align_center = Alignment(horizontal='center', vertical='center')
        align_right = Alignment(horizontal='right', vertical='center')

        ws.merge_cells('A1:D1')
        ws.merge_cells('A2:D2')
        ws.merge_cells('A3:D3')

        ws['A1'] = ctx['empresa_nombre'].upper()
        ws['A1'].font = font_titulo
        ws['A1'].alignment = align_center

        ws['A2'] = f"ACTA DE CONCILIACIÓN BANCARIA - {recon.bank_account.bank_name.upper()} {recon.bank_account.account_number}"
        ws['A2'].font = Font(name='Segoe UI', size=10, bold=True, color='FFFFFF')
        ws['A2'].alignment = align_center

        ws['A3'] = f"Período: Del {recon.period_start.strftime('%d/%m/%Y')} al {recon.period_end.strftime('%d/%m/%Y')} · Moneda: USD"
        ws['A3'].font = Font(name='Segoe UI', size=9, italic=True, color='FFFFFF')
        ws['A3'].alignment = align_center

        for r in range(1, 4):
            for c in range(1, 5):
                ws.cell(row=r, column=c).fill = fill_banner

        # Cuadro de Resumen
        unmatched_books = recon.items.filter(source='book', is_matched=False)
        dep_transito = float(unmatched_books.filter(movement_type='credit').aggregate(s=Sum('amount'))['s'] or 0)
        cheq_transito = float(unmatched_books.filter(movement_type='debit').aggregate(s=Sum('amount'))['s'] or 0)

        row = 5
        resumen = [
            ("Saldo según Extracto Bancario", float(recon.statement_balance)),
            ("(+) Depósitos en Tránsito", dep_transito),
            ("(-) Cheques y Transferencias en Tránsito", -cheq_transito),
            ("(=) Saldo Conciliado", float(recon.reconciled_balance)),
            ("Saldo según Libro Mayor Contable", float(recon.book_balance)),
            ("Diferencia de Conciliación", float(recon.difference)),
        ]

        for concepto, valor in resumen:
            ws.cell(row=row, column=2, value=concepto).font = Font(name='Segoe UI', bold=True if 'Saldo' in concepto or 'Diferencia' in concepto else False)
            c_val = ws.cell(row=row, column=3, value=valor)
            c_val.number_format = '$#,##0.00'
            c_val.alignment = align_right
            c_val.font = Font(name='Segoe UI', bold=True if 'Saldo' in concepto or 'Diferencia' in concepto else False)
            row += 1

        row += 2
        # Detalle de Partidas
        headers = ["FECHA", "ORIGEN / CONCEPTO", "REFERENCIA / DETALLE", "MONTO (USD)"]
        for c_idx, h in enumerate(headers, start=1):
            cell = ws.cell(row=row, column=c_idx, value=h)
            cell.font = Font(name='Segoe UI', bold=True, color='FFFFFF')
            cell.fill = fill_banner
        row += 1

        for it in recon.items.order_by('date')[:50]:
            ws.cell(row=row, column=1, value=it.date.strftime('%d/%m/%Y'))
            ws.cell(row=row, column=2, value="Extracto" if it.source == 'statement' else "Libros")
            ws.cell(row=row, column=3, value=f"{it.reference} - {it.description}"[:45])
            c_amt = ws.cell(row=row, column=4, value=float(it.amount))
            c_amt.number_format = '$#,##0.00'
            c_amt.alignment = align_right
            row += 1

        ws.column_dimensions['A'].width = 15
        ws.column_dimensions['B'].width = 30
        ws.column_dimensions['C'].width = 45
        ws.column_dimensions['D'].width = 20

        buffer = io.BytesIO()
        wb.save(buffer)
        return buffer.getvalue()
