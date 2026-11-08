"""
Vistas REST API para Cuentas Bancarias de la Empresa, Cash Management y Conciliación Bancaria.
"""

from decimal import Decimal
from django.http import HttpResponse
from django.db.models import Sum

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from ..django_models import (
    BankAccountModel, AccountModel, JournalEntryLineModel,
    BankReconciliationModel, BankReconciliationItemModel
)
from ...application.cash_management_service import CashManagementService
from ...application.bank_reconciliation_service import BankReconciliationService


def _check_tenant(request):
    if not getattr(request, 'tenant', None):
        return Response({'error': 'Empresa / Tenant no autenticado'}, status=status.HTTP_404_NOT_FOUND)
    return None


# ───────────────────────────────────────────────────────────────────────────
# 1. CUENTAS BANCARIAS DE LA EMPRESA (Cero datos quemados)
# ───────────────────────────────────────────────────────────────────────────

class BankAccountsView(APIView):
    """
    CRUD de cuentas bancarias reales de la empresa.
    Cada cuenta se vincula a una cuenta contable del catálogo (Activo/Bancos).
    """
    def get(self, request):
        if err := _check_tenant(request): return err
        tenant_id = request.tenant.id

        accounts = BankAccountModel.objects.filter(
            tenant_id=tenant_id
        ).select_related('account').order_by('bank_name', 'account_number')

        results = []
        for b in accounts:
            # Calcular saldo contable actual desde el Libro Mayor
            # Activo: Saldo = Débitos - Créditos
            qs_lines = JournalEntryLineModel.objects.filter(
                entry__tenant_id=tenant_id,
                account_id=b.account_id
            ).aggregate(tot_debit=Sum('debit'), tot_credit=Sum('credit'))

            saldo_contable = float((qs_lines['tot_debit'] or Decimal('0')) - (qs_lines['tot_credit'] or Decimal('0')))

            results.append({
                'id': b.id,
                'bank_name': b.bank_name,
                'bank_code': b.bank_code,
                'account_number': b.account_number,
                'account_type': b.account_type,
                'account_type_label': b.get_account_type_display(),
                'currency': b.currency,
                'company_code': b.company_code,
                'description': b.description,
                'is_active': b.is_active,
                'account_id': b.account_id,
                'account_code': b.account.code if b.account else '',
                'account_name': b.account.name if b.account else '',
                'current_balance': saldo_contable,
                'created_at': b.created_at.strftime('%Y-%m-%d %H:%M') if b.created_at else None,
            })

        return Response(results)

    def post(self, request):
        if err := _check_tenant(request): return err
        tenant_id = request.tenant.id
        data = request.data

        bank_name = str(data.get('bank_name') or '').strip()
        account_number = str(data.get('account_number') or '').strip()
        account_id = data.get('account_id')

        if not bank_name:
            return Response({'error': 'El nombre del banco es obligatorio.'}, status=status.HTTP_400_BAD_REQUEST)
        if not account_number:
            return Response({'error': 'El número de cuenta bancaria es obligatorio.'}, status=status.HTTP_400_BAD_REQUEST)
        if not account_id:
            return Response({'error': 'Debe vincular una cuenta contable del Plan de Cuentas.'}, status=status.HTTP_400_BAD_REQUEST)

        # Validar que la cuenta contable exista y pertenezca al tenant
        acc = AccountModel.objects.filter(id=account_id, tenant_id=tenant_id).first()
        if not acc:
            return Response({'error': 'La cuenta contable seleccionada no existe en el catálogo.'}, status=status.HTTP_400_BAD_REQUEST)

        # Evitar duplicados de número de cuenta dentro del mismo tenant
        if BankAccountModel.objects.filter(tenant_id=tenant_id, account_number=account_number).exists():
            return Response({'error': f'Ya existe una cuenta registrada con el número {account_number}.'}, status=status.HTTP_400_BAD_REQUEST)

        bank_acc = BankAccountModel.objects.create(
            tenant_id=tenant_id,
            bank_name=bank_name,
            bank_code=str(data.get('bank_code') or '').strip(),
            account_number=account_number,
            account_type=data.get('account_type', 'corriente'),
            currency=data.get('currency', 'USD'),
            account=acc,
            company_code=str(data.get('company_code') or '').strip(),
            description=str(data.get('description') or '').strip(),
            is_active=data.get('is_active', True)
        )

        return Response({
            'id': bank_acc.id,
            'bank_name': bank_acc.bank_name,
            'account_number': bank_acc.account_number,
            'message': 'Cuenta bancaria creada exitosamente'
        }, status=status.HTTP_201_CREATED)


class BankAccountDetailView(APIView):
    def get(self, request, pk):
        if err := _check_tenant(request): return err
        b = BankAccountModel.objects.filter(id=pk, tenant_id=request.tenant.id).select_related('account').first()
        if not b:
            return Response({'error': 'Cuenta bancaria no encontrada'}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'id': b.id,
            'bank_name': b.bank_name,
            'bank_code': b.bank_code,
            'account_number': b.account_number,
            'account_type': b.account_type,
            'currency': b.currency,
            'company_code': b.company_code,
            'description': b.description,
            'is_active': b.is_active,
            'account_id': b.account_id,
            'account_code': b.account.code if b.account else '',
            'account_name': b.account.name if b.account else '',
        })

    def put(self, request, pk):
        if err := _check_tenant(request): return err
        b = BankAccountModel.objects.filter(id=pk, tenant_id=request.tenant.id).first()
        if not b:
            return Response({'error': 'Cuenta bancaria no encontrada'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data
        if 'bank_name' in data: b.bank_name = str(data['bank_name']).strip()
        if 'bank_code' in data: b.bank_code = str(data['bank_code']).strip()
        if 'account_number' in data: b.account_number = str(data['account_number']).strip()
        if 'account_type' in data: b.account_type = data['account_type']
        if 'company_code' in data: b.company_code = str(data['company_code']).strip()
        if 'description' in data: b.description = str(data['description']).strip()
        if 'is_active' in data: b.is_active = bool(data['is_active'])

        if 'account_id' in data:
            acc = AccountModel.objects.filter(id=data['account_id'], tenant_id=request.tenant.id).first()
            if acc:
                b.account = acc

        b.save()
        return Response({'id': b.id, 'bank_name': b.bank_name, 'message': 'Cuenta actualizada con éxito'})

    def delete(self, request, pk):
        if err := _check_tenant(request): return err
        b = BankAccountModel.objects.filter(id=pk, tenant_id=request.tenant.id).first()
        if not b:
            return Response({'error': 'Cuenta bancaria no encontrada'}, status=status.HTTP_404_NOT_FOUND)

        # Soft delete para preservar integridad referencial
        b.is_active = False
        b.save(update_fields=['is_active'])
        return Response({'message': 'Cuenta bancaria desactivada exitosamente'})


# ───────────────────────────────────────────────────────────────────────────
# 2. CASH MANAGEMENT BANCARIO (Pichincha, Guayaquil, Produbanco)
# ───────────────────────────────────────────────────────────────────────────

class CashManagementItemsView(APIView):
    """
    Lista las cuentas por pagar pendientes con el estado de sus datos bancarios.
    """
    def get(self, request):
        if err := _check_tenant(request): return err
        items = CashManagementService.get_pending_payables(request.tenant.id)
        return Response(items)


class CashManagementGenerateView(APIView):
    """
    Genera y descarga el archivo plano oficial (.txt) según el banco seleccionado.
    """
    def post(self, request):
        if err := _check_tenant(request): return err
        data = request.data

        bank_account_id = data.get('bank_account_id')
        bank_format = str(data.get('bank_format') or 'pichincha').lower()
        payable_ids = data.get('payable_ids', [])

        if not bank_account_id:
            return Response({'error': 'Seleccione la cuenta bancaria de origen.'}, status=status.HTTP_400_BAD_REQUEST)
        if not payable_ids or not isinstance(payable_ids, list):
            return Response({'error': 'Debe seleccionar al menos una cuenta por pagar.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = CashManagementService.generate_file(
                tenant_id=request.tenant.id,
                bank_account_id=bank_account_id,
                bank_format=bank_format,
                payable_ids=payable_ids
            )

            # Si el cliente pide JSON de confirmación o descarga directa
            download = request.query_params.get('download', 'true').lower() == 'true'
            if download:
                response = HttpResponse(result['content'], content_type='text/plain; charset=utf-8')
                response['Content-Disposition'] = f'attachment; filename="{result["filename"]}"'
                response['X-Total-Items'] = str(result['total_items'])
                response['X-Total-Amount'] = str(result['total_amount'])
                return response
            else:
                return Response(result)

        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f'Error generando archivo de pago: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CashManagementApplyPaymentsView(APIView):
    """
    Asienta en el sistema los pagos de las facturas enviadas al banco,
    generando los abonos y los asientos contables en el Libro Diario.
    """
    def post(self, request):
        if err := _check_tenant(request): return err
        data = request.data

        bank_account_id = data.get('bank_account_id')
        payable_ids = data.get('payable_ids', [])
        payment_date = data.get('payment_date')

        if not bank_account_id or not payable_ids:
            return Response({'error': 'Faltan parámetros requeridos (cuenta bancaria o facturas).'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            res = CashManagementService.apply_batch_payments(
                tenant_id=request.tenant.id,
                bank_account_id=bank_account_id,
                payable_ids=payable_ids,
                payment_date=payment_date
            )
            return Response(res)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ───────────────────────────────────────────────────────────────────────────
# 3. CONCILIACIÓN BANCARIA AUTOMÁTICA
# ───────────────────────────────────────────────────────────────────────────

class BankReconciliationsView(APIView):
    """
    Lista el historial de conciliaciones bancarias del tenant.
    """
    def get(self, request):
        if err := _check_tenant(request): return err
        tenant_id = request.tenant.id
        bank_account_id = request.query_params.get('bank_account_id')

        qs = BankReconciliationModel.objects.filter(tenant_id=tenant_id).select_related('bank_account')
        if bank_account_id:
            qs = qs.filter(bank_account_id=bank_account_id)

        results = []
        for r in qs:
            results.append({
                'id': r.id,
                'bank_account_id': r.bank_account_id,
                'bank_name': r.bank_account.bank_name,
                'account_number': r.bank_account.account_number,
                'period_start': r.period_start.strftime('%Y-%m-%d'),
                'period_end': r.period_end.strftime('%Y-%m-%d'),
                'statement_balance': float(r.statement_balance),
                'book_balance': float(r.book_balance),
                'reconciled_balance': float(r.reconciled_balance),
                'difference': float(r.difference),
                'status': r.status,
                'status_label': r.get_status_display(),
                'notes': r.notes,
                'created_at': r.created_at.strftime('%Y-%m-%d %H:%M'),
            })

        return Response(results)


class BankReconciliationUploadView(APIView):
    """
    Sube el extracto bancario en Excel (.xlsx) o CSV, analiza sus movimientos
    y ejecuta el auto-cruce contra el Libro Mayor Contable.
    """
    def post(self, request):
        if err := _check_tenant(request): return err
        tenant_id = request.tenant.id

        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'error': 'Debe subir un archivo de extracto bancario (.xlsx o .csv).'}, status=status.HTTP_400_BAD_REQUEST)

        bank_account_id = request.data.get('bank_account_id')
        period_start = request.data.get('period_start')
        period_end = request.data.get('period_end')
        statement_balance = request.data.get('statement_balance')

        if not bank_account_id or not period_start or not period_end or statement_balance is None:
            return Response({'error': 'Faltan datos requeridos: cuenta bancaria, período (inicio/fin) y saldo final del extracto.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 1. Parsear el archivo del banco
            statement_items = BankReconciliationService.parse_statement_file(file_obj, file_obj.name)
            if not statement_items:
                return Response({'error': 'No se pudieron extraer movimientos del archivo. Verifique el formato.'}, status=status.HTTP_400_BAD_REQUEST)

            # 2. Ejecutar conciliación y auto-matching
            recon = BankReconciliationService.create_and_automatch_reconciliation(
                tenant_id=tenant_id,
                bank_account_id=int(bank_account_id),
                period_start=period_start,
                period_end=period_end,
                statement_balance=float(statement_balance),
                statement_items=statement_items,
                notes=request.data.get('notes', '')
            )

            return Response({
                'id': recon.id,
                'status': recon.status,
                'statement_balance': float(recon.statement_balance),
                'book_balance': float(recon.book_balance),
                'reconciled_balance': float(recon.reconciled_balance),
                'difference': float(recon.difference),
                'total_statement_items': len(statement_items),
                'message': 'Extracto procesado y conciliación automática completada exitosamente.'
            }, status=status.HTTP_201_CREATED)

        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f'Error al procesar extracto: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BankReconciliationDetailView(APIView):
    """
    Obtiene el detalle completo de una conciliación bancaria con sus partidas.
    """
    def get(self, request, pk):
        if err := _check_tenant(request): return err
        recon = BankReconciliationModel.objects.filter(
            id=pk, tenant_id=request.tenant.id
        ).select_related('bank_account').first()

        if not recon:
            return Response({'error': 'Conciliación no encontrada'}, status=status.HTTP_404_NOT_FOUND)

        items = recon.items.all().order_by('date', 'id')
        statement_items = []
        book_items = []

        for it in items:
            it_data = {
                'id': it.id,
                'source': it.source,
                'date': it.date.strftime('%Y-%m-%d'),
                'reference': it.reference,
                'description': it.description,
                'amount': float(it.amount),
                'movement_type': it.movement_type,
                'is_matched': it.is_matched,
                'matched_with_id': it.matched_with_id,
                'match_method': it.match_method,
            }
            if it.source == 'statement':
                statement_items.append(it_data)
            else:
                book_items.append(it_data)

        return Response({
            'id': recon.id,
            'bank_account_id': recon.bank_account_id,
            'bank_name': recon.bank_account.bank_name,
            'account_number': recon.bank_account.account_number,
            'period_start': recon.period_start.strftime('%Y-%m-%d'),
            'period_end': recon.period_end.strftime('%Y-%m-%d'),
            'statement_balance': float(recon.statement_balance),
            'book_balance': float(recon.book_balance),
            'reconciled_balance': float(recon.reconciled_balance),
            'difference': float(recon.difference),
            'status': recon.status,
            'notes': recon.notes,
            'statement_items': statement_items,
            'book_items': book_items,
        })

    def delete(self, request, pk):
        if err := _check_tenant(request): return err
        recon = BankReconciliationModel.objects.filter(id=pk, tenant_id=request.tenant.id).first()
        if not recon:
            return Response({'error': 'Conciliación no encontrada'}, status=status.HTTP_404_NOT_FOUND)
        if recon.status == 'closed':
            return Response({'error': 'No se puede eliminar una conciliación cerrada y aprobada.'}, status=status.HTTP_400_BAD_REQUEST)

        recon.delete()
        return Response({'message': 'Conciliación eliminada exitosamente'})


class BankReconciliationMatchToggleView(APIView):
    """
    Conciliación manual de una o dos partidas.
    Permite marcar como conciliada o desmarcar.
    """
    def post(self, request, pk):
        if err := _check_tenant(request): return err
        recon = BankReconciliationModel.objects.filter(id=pk, tenant_id=request.tenant.id).first()
        if not recon:
            return Response({'error': 'Conciliación no encontrada'}, status=status.HTTP_404_NOT_FOUND)

        item_id = request.data.get('item_id')
        matched = request.data.get('matched', True)
        matched_with_id = request.data.get('matched_with_id')

        item = recon.items.filter(id=item_id).first()
        if not item:
            return Response({'error': 'Partida no encontrada'}, status=status.HTTP_404_NOT_FOUND)

        item.is_matched = matched
        item.match_method = 'manual' if matched else ''
        item.matched_with_id = matched_with_id if matched else None
        item.save()

        # Si se vinculó con otra partida, actualizarla también
        if matched_with_id:
            other = recon.items.filter(id=matched_with_id).first()
            if other:
                other.is_matched = matched
                other.match_method = 'manual' if matched else ''
                other.matched_with_id = item.id if matched else None
                other.save()

        # Recalcular totales de la conciliación
        BankReconciliationService.recalculate_totals(recon)

        return Response({
            'status': recon.status,
            'reconciled_balance': float(recon.reconciled_balance),
            'difference': float(recon.difference)
        })


class BankReconciliationFinalizeView(APIView):
    """
    Cierra y aprueba oficialmente la conciliación bancaria.
    """
    def post(self, request, pk):
        if err := _check_tenant(request): return err
        recon = BankReconciliationModel.objects.filter(id=pk, tenant_id=request.tenant.id).first()
        if not recon:
            return Response({'error': 'Conciliación no encontrada'}, status=status.HTTP_404_NOT_FOUND)

        recon.status = 'closed'
        recon.save(update_fields=['status'])
        return Response({'status': 'closed', 'message': 'Conciliación cerrada y aprobada formalmente.'})


class BankReconciliationExportPDFView(APIView):
    """
    Descarga el Acta Oficial de Conciliación Bancaria en PDF con firmas de responsabilidad.
    """
    def get(self, request, pk):
        if err := _check_tenant(request): return err
        try:
            pdf_bytes = BankReconciliationService.generate_pdf_report(pk, request.tenant.id)
            recon = BankReconciliationModel.objects.get(id=pk, tenant_id=request.tenant.id)
            filename = f"conciliacion_{recon.bank_account.bank_name}_{recon.period_end.strftime('%Y%m%d')}.pdf"

            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class BankReconciliationExportExcelView(APIView):
    """
    Descarga el Acta de Conciliación Bancaria en Excel corporativo (.xlsx).
    """
    def get(self, request, pk):
        if err := _check_tenant(request): return err
        try:
            excel_bytes = BankReconciliationService.generate_excel_report(pk, request.tenant.id)
            recon = BankReconciliationModel.objects.get(id=pk, tenant_id=request.tenant.id)
            filename = f"conciliacion_{recon.bank_account.bank_name}_{recon.period_end.strftime('%Y%m%d')}.xlsx"

            response = HttpResponse(
                excel_bytes,
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
