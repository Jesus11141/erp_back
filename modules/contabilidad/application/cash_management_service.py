"""
Servicio de Aplicación: Cash Management Bancario Ecuador.
Genera archivos planos (.txt) oficiales para pagos masivos a proveedores y nómina:
- Banco Pichincha (Cash Management tab-delimited)
- Banco Guayaquil (Multicash / Pagos masivos)
- Produbanco (Pagos masivos a terceros)
Permite validar la información antes de emitir el archivo y asentar los pagos
con generación automática de asientos contables enlazados a la cuenta bancaria.
"""

import re
import unicodedata
from decimal import Decimal
from datetime import date, datetime
from typing import List, Dict, Any, Optional

from django.db import transaction
from django.utils import timezone

from ..infrastructure.django_models import (
    BankAccountModel, AccountModel, JournalEntryModel, JournalEntryLineModel
)
from modules.compras.infrastructure.django_models import (
    AccountPayableModel, PayablePaymentModel, ProveedorModel
)


def _sanitizar_texto(texto: str, max_len: int = 40) -> str:
    """Elimina tildes, caracteres especiales y recorta al tamaño permitido por los bancos."""
    if not texto:
        return ''
    # Normalizar Unicode a ASCII
    t = unicodedata.normalize('NFKD', str(texto)).encode('ASCII', 'ignore').decode('ASCII')
    # Reemplazar caracteres no alfanuméricos permitidos
    t = re.sub(r'[^A-Za-z0-9\s\.\-_]', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t[:max_len]


def _tipo_id_banco(tipo_id_erp: str, identificacion: str) -> str:
    """Retorna 'C' para Cédula, 'R' para RUC, 'P' para Pasaporte según estándar bancario."""
    tid = str(tipo_id_erp or '').upper()
    ident = str(identificacion or '').strip()
    if tid in ['04', 'RUC', 'R'] or len(ident) == 13:
        return 'R'
    if tid in ['05', 'CEDULA', 'C'] or len(ident) == 10:
        return 'C'
    return 'P'


def _tipo_cuenta_banco(tipo_cuenta: str) -> str:
    """Retorna 'AHO' o 'CTE'."""
    tc = str(tipo_cuenta or '').upper().strip()
    if 'CORR' in tc or tc == 'CTE':
        return 'CTE'
    return 'AHO'


class CashManagementService:

    @staticmethod
    def get_pending_payables(tenant_id: int) -> List[Dict[str, Any]]:
        """
        Obtiene las cuentas por pagar pendientes con el estado de sus datos bancarios.
        """
        qs = AccountPayableModel.objects.filter(
            tenant_id=tenant_id
        ).exclude(
            status='PAID'
        ).select_related('supplier', 'invoice').order_by('due_date', '-created_at')

        results = []
        for ap in qs:
            supp = ap.supplier
            bank_name = supp.bank_name if supp else ''
            account_type = supp.bank_account_type if supp else 'AHO'
            account_number = supp.bank_account_number if supp else ''
            beneficiary_name = (supp.beneficiary_name if supp and supp.beneficiary_name else supp.business_name) if supp else ''
            beneficiary_id = (supp.beneficiary_id if supp and supp.beneficiary_id else supp.identification) if supp else ''

            is_ready = bool(account_number and beneficiary_name and beneficiary_id)

            results.append({
                'id': ap.id,
                'invoice_id': ap.invoice_id,
                'invoice_number': ap.invoice_number,
                'supplier_id': ap.supplier_id,
                'supplier_name': ap.supplier_name,
                'supplier_identification': supp.identification if supp else '',
                'total_amount': float(ap.total_amount),
                'balance_due': float(ap.balance_due),
                'due_date': ap.due_date.strftime('%Y-%m-%d') if ap.due_date else None,
                'status': ap.status,
                # Datos bancarios del proveedor
                'bank_name': bank_name,
                'bank_account_type': _tipo_cuenta_banco(account_type),
                'bank_account_number': account_number,
                'beneficiary_name': beneficiary_name,
                'beneficiary_id': beneficiary_id,
                'is_ready': is_ready,
                'error_msg': '' if is_ready else 'Falta registrar cuenta bancaria o titular del proveedor'
            })

        return results

    @staticmethod
    def generate_file(
        tenant_id: int,
        bank_account_id: int,
        bank_format: str,
        payable_ids: List[int]
    ) -> Dict[str, Any]:
        """
        Genera el archivo plano estructurado según el formato bancario seleccionado.
        Formatos soportados:
        - 'pichincha': Cash Management Banco Pichincha (.txt)
        - 'guayaquil': Multicash / Pagos Masivos Banco Guayaquil (.txt)
        - 'produbanco': Pagos Masivos Produbanco (.txt)
        """
        bank_account = BankAccountModel.objects.filter(id=bank_account_id, tenant_id=tenant_id).first()
        if not bank_account:
            raise ValueError("Cuenta bancaria de la empresa no encontrada.")

        payables = AccountPayableModel.objects.filter(
            id__in=payable_ids, tenant_id=tenant_id
        ).select_related('supplier', 'invoice').order_by('id')

        if not payables.exists():
            raise ValueError("No se seleccionaron cuentas por pagar válidas.")

        # Validaciones de integridad
        items_data = []
        errores = []
        total_monto = Decimal('0.00')

        for idx, ap in enumerate(payables, start=1):
            supp = ap.supplier
            acc_num = supp.bank_account_number.strip() if supp and supp.bank_account_number else ''
            ben_name = (supp.beneficiary_name.strip() if supp and supp.beneficiary_name else supp.business_name.strip()) if supp else ''
            ben_id = (supp.beneficiary_id.strip() if supp and supp.beneficiary_id else supp.identification.strip()) if supp else ''
            ben_email = supp.email.strip() if supp and supp.email else ''
            acc_type = _tipo_cuenta_banco(supp.bank_account_type if supp else 'AHO')
            b_name = supp.bank_name.strip() if supp and supp.bank_name else bank_account.bank_name

            if not acc_num:
                errores.append(f"Factura {ap.invoice_number} ({ap.supplier_name}): No tiene número de cuenta bancaria.")
            if not ben_id:
                errores.append(f"Factura {ap.invoice_number} ({ap.supplier_name}): No tiene número de identificación/RUC del titular.")

            monto = ap.balance_due
            total_monto += monto

            items_data.append({
                'secuencia': idx,
                'ap_id': ap.id,
                'invoice_number': ap.invoice_number,
                'amount': monto,
                'bank_name': b_name,
                'account_type': acc_type,
                'account_number': acc_num,
                'beneficiary_name': ben_name,
                'beneficiary_id': ben_id,
                'beneficiary_id_type': _tipo_id_banco(supp.id_type if supp else '', ben_id),
                'email': ben_email,
            })

        if errores:
            raise ValueError("Errores en datos de pago: " + "; ".join(errores[:5]))

        # Generación del archivo según formato
        bank_format = bank_format.lower()
        if bank_format == 'pichincha':
            contenido, filename = CashManagementService._build_pichincha(bank_account, items_data)
        elif bank_format == 'guayaquil':
            contenido, filename = CashManagementService._build_guayaquil(bank_account, items_data)
        elif bank_format == 'produbanco':
            contenido, filename = CashManagementService._build_produbanco(bank_account, items_data)
        else:
            # Formato estándar delimitado por tabulaciones
            contenido, filename = CashManagementService._build_pichincha(bank_account, items_data)

        return {
            'filename': filename,
            'content': contenido,
            'total_items': len(items_data),
            'total_amount': float(total_monto),
            'bank_account_id': bank_account.id,
            'bank_name': bank_account.bank_name,
            'account_number': bank_account.account_number,
        }

    # -----------------------------------------------------------------------
    # CONSTRUCTORES DE FORMATOS OFICIALES
    # -----------------------------------------------------------------------

    @staticmethod
    def _build_pichincha(bank_account: BankAccountModel, items: List[Dict[str, Any]]) -> tuple[str, str]:
        """
        Formato Oficial Cash Management Banco Pichincha (Delimitado por TAB \t).
        Columnas estándar:
        1. PA (Tipo Operación Pago)
        2. Contrapartida / Código interno
        3. Moneda (USD)
        4. Valor con 2 decimales (ej: 125.50)
        5. Forma de Pago (CTA)
        6. Tipo de Cuenta (AHO o CTE)
        7. Número de Cuenta Destino
        8. Tipo Identificación (C, R, P)
        9. Número Identificación
        10. Nombre Beneficiario
        11. Dirección (opcional)
        12. Referencia / Factura
        13. Descripción / Glosa
        14. Email
        """
        lineas = []
        fecha_str = date.today().strftime('%Y%m%d')

        for item in items:
            col_op = "PA"
            col_contrapartida = str(item['ap_id'])
            col_moneda = "USD"
            col_valor = f"{item['amount']:.2f}"
            col_forma = "CTA"
            col_tipo_cta = item['account_type']
            col_num_cta = re.sub(r'\D', '', item['account_number'])
            col_tipo_id = item['beneficiary_id_type']
            col_id = re.sub(r'[^A-Za-z0-9]', '', item['beneficiary_id'])
            col_nombre = _sanitizar_texto(item['beneficiary_name'], 40)
            col_dir = ""
            col_ref = _sanitizar_texto(f"FAC {item['invoice_number']}", 20)
            col_desc = _sanitizar_texto(f"PAGO FACTURA {item['invoice_number']}", 30)
            col_email = item['email'] or ""

            linea = f"{col_op}\t{col_contrapartida}\t{col_moneda}\t{col_valor}\t{col_forma}\t{col_tipo_cta}\t{col_num_cta}\t{col_tipo_id}\t{col_id}\t{col_nombre}\t{col_dir}\t{col_ref}\t{col_desc}\t{col_email}"
            lineas.append(linea)

        contenido = "\r\n".join(lineas) + "\r\n"
        filename = f"CASH_PICHINCHA_{bank_account.account_number}_{fecha_str}.txt"
        return contenido, filename

    @staticmethod
    def _build_guayaquil(bank_account: BankAccountModel, items: List[Dict[str, Any]]) -> tuple[str, str]:
        """
        Formato Banco Guayaquil Multicash / Pagos Masivos (Tabulado).
        Estructura:
        CuentaOrigen \t Secuencia \t Beneficiario \t TipoId \t Id \t TipoCta \t NumCta \t Monto \t Referencia \t Email
        """
        lineas = []
        fecha_str = date.today().strftime('%Y%m%d')
        cta_origen = re.sub(r'\D', '', bank_account.account_number)

        for item in items:
            sec = str(item['secuencia'])
            nombre = _sanitizar_texto(item['beneficiary_name'], 40)
            tipo_id = item['beneficiary_id_type']
            ident = re.sub(r'[^A-Za-z0-9]', '', item['beneficiary_id'])
            tipo_cta = item['account_type']
            num_cta = re.sub(r'\D', '', item['account_number'])
            monto = f"{item['amount']:.2f}"
            ref = _sanitizar_texto(f"FAC_{item['invoice_number']}", 25)
            email = item['email'] or ""

            linea = f"{cta_origen}\t{sec}\t{nombre}\t{tipo_id}\t{ident}\t{tipo_cta}\t{num_cta}\t{monto}\t{ref}\t{email}"
            lineas.append(linea)

        contenido = "\r\n".join(lineas) + "\r\n"
        filename = f"MULTICASH_GUAYAQUIL_{cta_origen}_{fecha_str}.txt"
        return contenido, filename

    @staticmethod
    def _build_produbanco(bank_account: BankAccountModel, items: List[Dict[str, Any]]) -> tuple[str, str]:
        """
        Formato Produbanco Pagos Masivos a Proveedores (Delimitado por punto y coma ;).
        """
        lineas = []
        fecha_str = date.today().strftime('%Y%m%d')
        cta_origen = re.sub(r'\D', '', bank_account.account_number)

        for item in items:
            tipo_op = "PA"
            num_cta = re.sub(r'\D', '', item['account_number'])
            tipo_cta = item['account_type']
            monto = f"{item['amount']:.2f}"
            tipo_id = item['beneficiary_id_type']
            ident = re.sub(r'[^A-Za-z0-9]', '', item['beneficiary_id'])
            nombre = _sanitizar_texto(item['beneficiary_name'], 40)
            ref = _sanitizar_texto(f"PAGO FAC {item['invoice_number']}", 30)
            email = item['email'] or ""

            linea = f"{tipo_op};{cta_origen};{num_cta};{tipo_cta};{monto};{tipo_id};{ident};{nombre};{ref};{email}"
            lineas.append(linea)

        contenido = "\r\n".join(lineas) + "\r\n"
        filename = f"PRODUBANCO_{cta_origen}_{fecha_str}.txt"
        return contenido, filename

    # -----------------------------------------------------------------------
    # APLICACIÓN DE PAGOS Y CONTABILIZACIÓN AUTOMÁTICA
    # -----------------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def apply_batch_payments(
        tenant_id: int,
        bank_account_id: int,
        payable_ids: List[int],
        payment_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Asienta los pagos de las cuentas por pagar seleccionadas:
        1. Registra el abono (PayablePaymentModel) por el total del saldo.
        2. Actualiza la cuenta por pagar a estado 'PAID' (saldo 0).
        3. Genera el asiento contable en el Libro Diario:
           - Debe: Cuenta contable de Proveedores (Pasivo)
           - Haber: Cuenta contable del Banco origen (Activo)
        """
        bank_account = BankAccountModel.objects.filter(id=bank_account_id, tenant_id=tenant_id).select_related('account').first()
        if not bank_account:
            raise ValueError("Cuenta bancaria de origen no válida.")

        p_date = datetime.strptime(payment_date, '%Y-%m-%d').date() if payment_date else date.today()

        payables = AccountPayableModel.objects.filter(
            id__in=payable_ids, tenant_id=tenant_id
        ).exclude(status='PAID').select_related('supplier', 'invoice')

        if not payables.exists():
            raise ValueError("No hay cuentas por pagar pendientes seleccionadas para asentar.")

        # Buscar cuenta de Cuentas por Pagar Proveedores en el plan de cuentas
        cxp_account = AccountModel.objects.filter(
            tenant_id=tenant_id,
            type='pasivo',
            code__startswith='2'
        ).first()

        if not cxp_account:
            # Fallback o crear cuenta transaccional
            cxp_account = AccountModel.objects.filter(tenant_id=tenant_id, type='pasivo').first()

        applied_count = 0
        total_applied = Decimal('0.00')
        lines_data = []

        batch_ref = f"CASH_MGMT_{bank_account.bank_name[:4].upper()}_{date.today().strftime('%Y%m%d%H%M')}"

        for ap in payables:
            monto_abono = ap.balance_due
            if monto_abono <= 0:
                continue

            # 1. Registrar abono en compras_abonos_pagar
            PayablePaymentModel.objects.create(
                tenant_id=tenant_id,
                account_payable=ap,
                amount=monto_abono,
                payment_date=p_date,
                payment_method='transferencia',
                reference=f"{bank_account.bank_name} - {bank_account.account_number}",
                notes=f"Pago masivo Cash Management a {ap.supplier_name}"
            )

            # 2. Actualizar CxP a Pagada
            ap.balance_due = Decimal('0.00')
            ap.status = 'PAID'
            ap.save(update_fields=['balance_due', 'status'])

            total_applied += monto_abono
            applied_count += 1

        # 3. Generar Asiento Contable Automático en Partida Doble
        # Debe: Proveedores CxP (disminuye pasivo)
        # Haber: Banco seleccionado (disminuye activo)
        if total_applied > 0 and cxp_account and bank_account.account:
            entry = JournalEntryModel.objects.create(
                tenant_id=tenant_id,
                date=p_date,
                description=f"Pago masivo Cash Management {bank_account.bank_name} ({applied_count} facturas)",
                type='egreso',
                reference=batch_ref
            )

            # Línea Debe (CxP)
            JournalEntryLineModel.objects.create(
                entry=entry,
                account=cxp_account,
                debit=total_applied,
                credit=Decimal('0.00'),
            )

            # Línea Haber (Banco)
            JournalEntryLineModel.objects.create(
                entry=entry,
                account=bank_account.account,
                debit=Decimal('0.00'),
                credit=total_applied,
            )

        return {
            'status': 'success',
            'applied_count': applied_count,
            'total_applied': float(total_applied),
            'bank_account': str(bank_account),
            'batch_reference': batch_ref
        }
