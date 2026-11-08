from datetime import date, datetime
from typing import Optional, Union, Dict, Any, List
from rest_framework.exceptions import ValidationError
from django.utils import timezone


class PeriodClosedError(ValidationError):
    def __init__(self, detail: str):
        super().__init__({'error': detail, 'code': 'PERIOD_CLOSED'})


class PeriodLockedError(ValidationError):
    def __init__(self, detail: str):
        super().__init__({'error': detail, 'code': 'PERIOD_LOCKED'})


MESES_NOMBRES = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
    5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
}


def _parse_date(target: Union[date, datetime, str]) -> date:
    if isinstance(target, datetime):
        return target.date()
    if isinstance(target, date):
        return target
    if isinstance(target, str):
        # Tomar los primeros 10 caracteres YYYY-MM-DD
        return date.fromisoformat(target[:10])
    return date.today()


def validate_accounting_period(
    tenant_id: int,
    target_date: Union[date, datetime, str],
    user_role: str = 'vendedor',
    action_desc: str = 'la operación'
) -> None:
    """
    Valida si la fecha de una transacción pertenece a un período abierto.
    Si está CERRADO: nadie puede operar (ni siquiera contador ni admin).
    Si está con BLOQUEO OPERATIVO: solo 'contador', 'admin' o 'superadmin' pueden registrar asientos o ajustes.
    Si está ABIERTO: todos los usuarios autorizados pueden operar.
    """
    if not tenant_id:
        return

    from ..infrastructure.django_models import AccountingPeriodModel

    d = _parse_date(target_date)
    try:
        period = AccountingPeriodModel.objects.filter(
            tenant_id=tenant_id,
            year=d.year,
            month=d.month
        ).first()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("No se pudo verificar el período contable (tabla aún no migrada o error de conexión): %s", e)
        return

    if not period or period.status == 'open':
        return

    mes_nom = MESES_NOMBRES.get(d.month, str(d.month))

    if period.status == 'closed':
        raise PeriodClosedError(
            f"Operación rechazada: El período contable {mes_nom} {d.year} se encuentra CERRADO DEFINITIVAMENTE "
            f"por auditoría fiscal del SRI. No se permite {action_desc}."
        )

    if period.status == 'locked':
        # Bloqueo operativo: solo perfiles contables / gerenciales pueden realizar ajustes
        allowed_roles = {'contador', 'admin', 'superadmin'}
        if user_role not in allowed_roles:
            raise PeriodLockedError(
                f"Operación rechazada: El período contable {mes_nom} {d.year} se encuentra con BLOQUEO OPERATIVO "
                f"(declaración en proceso). Solo el departamento contable puede realizar ajustes de {action_desc}."
            )


class PeriodManagementService:
    """
    Servicio de consulta y gestión de cierres y bloqueos de períodos fiscales.
    """

    def __init__(self, tenant_id: int):
        self.tenant_id = tenant_id

    def list_periods_for_year(self, year: int) -> List[Dict[str, Any]]:
        from ..infrastructure.django_models import AccountingPeriodModel, JournalEntryModel
        from modules.tax_documents.invoicing.infrastructure.persistence.django_models import InvoiceModel
        from modules.compras.infrastructure.django_models import FacturaCompraModel

        existing_periods = {
            p.month: p
            for p in AccountingPeriodModel.objects.filter(tenant_id=self.tenant_id, year=year)
        }

        result = []
        for month in range(1, 13):
            p = existing_periods.get(month)
            status = p.status if p else 'open'
            closed_by = p.closed_by if p else ''
            closed_at = p.closed_at.isoformat() if (p and p.closed_at) else None
            reopened_by = p.reopened_by if p else ''
            reopened_at = p.reopened_at.isoformat() if (p and p.reopened_at) else None
            notes = p.notes if p else ''

            # Métricas rápidas del período para el contador
            sales_qs = InvoiceModel.objects.filter(
                tenant_id=self.tenant_id,
                date__year=year,
                date__month=month
            ).exclude(status__in=['canceled', 'cancelled', 'void'])

            sales_count = sales_qs.count()
            sales_total = sum((inv.total for inv in sales_qs), 0)

            purchases_qs = FacturaCompraModel.objects.filter(
                tenant_id=self.tenant_id,
                date__year=year,
                date__month=month
            ).exclude(status='anulada')

            purchases_count = purchases_qs.count()
            purchases_total = sum((fac.total for fac in purchases_qs), 0)

            entries_count = JournalEntryModel.objects.filter(
                tenant_id=self.tenant_id,
                date__year=year,
                date__month=month
            ).count()

            result.append({
                'year': year,
                'month': month,
                'month_name': MESES_NOMBRES.get(month, f"Mes {month}"),
                'status': status,
                'closed_by': closed_by,
                'closed_at': closed_at,
                'reopened_by': reopened_by,
                'reopened_at': reopened_at,
                'notes': notes,
                'metrics': {
                    'sales_count': sales_count,
                    'sales_total': float(sales_total),
                    'purchases_count': purchases_count,
                    'purchases_total': float(purchases_total),
                    'entries_count': entries_count,
                }
            })

        return result

    def set_status(
        self,
        year: int,
        month: int,
        new_status: str,
        user_name: str,
        notes: str = ''
    ) -> Dict[str, Any]:
        if new_status not in ['open', 'locked', 'closed']:
            raise ValidationError(f"Estado de período inválido: {new_status}")

        if month < 1 or month > 12:
            raise ValidationError(f"Mes inválido: {month}")

        from ..infrastructure.django_models import AccountingPeriodModel

        period, _ = AccountingPeriodModel.objects.get_or_create(
            tenant_id=self.tenant_id,
            year=year,
            month=month,
            defaults={'status': 'open'}
        )

        old_status = period.status
        period.status = new_status
        if notes:
            period.notes = notes.strip()

        now = timezone.now()
        if new_status in ['closed', 'locked']:
            period.closed_by = user_name
            period.closed_at = now
        elif new_status == 'open' and old_status in ['closed', 'locked']:
            period.reopened_by = user_name
            period.reopened_at = now

        period.save()

        return {
            'year': period.year,
            'month': period.month,
            'month_name': MESES_NOMBRES.get(period.month, ''),
            'status': period.status,
            'closed_by': period.closed_by,
            'closed_at': period.closed_at.isoformat() if period.closed_at else None,
            'reopened_by': period.reopened_by,
            'reopened_at': period.reopened_at.isoformat() if period.reopened_at else None,
            'notes': period.notes,
        }
