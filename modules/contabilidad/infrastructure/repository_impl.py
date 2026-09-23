from typing import Optional, List
from decimal import Decimal

from ..domain.entities import Account, JournalEntry, JournalEntryLine
from ..domain.repositories import AccountingRepository
from ..domain.value_objects import AccountData
from .django_models import AccountModel, JournalEntryModel, JournalEntryLineModel


class DjangoAccountingRepository(AccountingRepository):

    def get_or_create_account(self, data: AccountData) -> Account:
        record, _ = AccountModel.objects.get_or_create(
            tenant_id=data.tenant_id,
            code=str(data.code),
            defaults={
                'name':   data.name,
                'type':     data.type.value,
                'parent_id': data.parent_id,
            },
        )
        return Account(
            id=record.id,
            tenant_id=record.tenant_id,
            code=record.code,
            name=record.name,
            type=record.type,
            parent_id=record.parent_id,
        )

    def list_accounts(self, tenant_id: int) -> List[Account]:
        records = AccountModel.objects.filter(tenant_id=tenant_id).order_by('code')
        return [
            Account(
                id=r.id,
                tenant_id=r.tenant_id,
                code=r.code,
                name=r.name,
                type=r.type,
                parent_id=r.parent_id,
            )
            for r in records
        ]

    def save_journal_entry(self, entry: JournalEntry) -> JournalEntry:
        from django.db import transaction
        with transaction.atomic():
            record = JournalEntryModel.objects.create(
                tenant_id=entry.tenant_id,
                date=entry.date,
                description=entry.description,
                reference=entry.reference,
            )
            saved_lines = []
            for line in entry.lines:
                line_record = JournalEntryLineModel.objects.create(
                    entry=record,
                    account_id=line.account_id,
                    debit=line.debit,
                    credit=line.credit,
                )
                saved_lines.append(JournalEntryLine(
                    id=line_record.id,
                    account_id=line_record.account_id,
                    account_code=line.account_code,
                    account_name=line.account_name,
                    debit=line_record.debit,
                    credit=line_record.credit,
                ))
            return JournalEntry(
                id=record.id,
                tenant_id=record.tenant_id,
                date=record.date,
                description=record.description,
                type='general',
                reference=record.reference,
                lines=saved_lines,
            )

    def get_journal_entries(self, tenant_id: int) -> List[JournalEntry]:
        records = (
            JournalEntryModel.objects
            .filter(tenant_id=tenant_id)
            .prefetch_related('lines__account')
            .order_by('-date', '-id')
        )
        result = []
        for record in records:
            lines = [
                JournalEntryLine(
                    id=d.id,
                    account_id=d.account_id,
                    account_code=d.account.code if d.account else '',
                    account_name=d.account.name if d.account else '',
                    debit=d.debit,
                    credit=d.credit,
                )
                for d in record.lines.all()
            ]
            result.append(JournalEntry(
                id=record.id,
                tenant_id=record.tenant_id,
                date=record.date,
                description=record.description,
                type=record.type,
                reference=record.reference,
                lines=lines,
            ))
        return result

    def get_journal_entry_by_id(self, tenant_id: int, entry_id: int) -> Optional[JournalEntry]:
        try:
            record = (
                JournalEntryModel.objects
                .prefetch_related('lines__account')
                .get(id=entry_id, tenant_id=tenant_id)
            )
        except JournalEntryModel.DoesNotExist:
            return None

        lines = [
            JournalEntryLine(
                id=d.id,
                account_id=d.account_id,
                account_code=d.account.code if d.account else '',
                account_name=d.account.name if d.account else '',
                debit=d.debit,
                credit=d.credit,
            )
            for d in record.lines.all()
        ]
        return JournalEntry(
            id=record.id,
            tenant_id=record.tenant_id,
            date=record.date,
            description=record.description,
            type=record.type,
            reference=record.reference,
            lines=lines,
        )

    def get_general_journal(
        self,
        tenant_id: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[dict]:
        qs = (
            JournalEntryModel.objects
            .filter(tenant_id=tenant_id)
            .prefetch_related('lines__account')
            .order_by('date', 'id')
        )
        if start_date:
            qs = qs.filter(date__gte=start_date)
        if end_date:
            qs = qs.filter(date__lte=end_date)

        return [
            {
                'id':          record.id,
                'number':      str(record.id),
                'date':        str(record.date),
                'description': record.description,
                'reference':   record.reference,
                'status':      'posted',
                'lines': [
                    {
                        'account_code': d.account.code if d.account else '',
                        'account_name': d.account.name if d.account else '',
                        'debit':        str(d.debit),
                        'credit':       str(d.credit),
                    }
                    for d in record.lines.all()
                ],
            }
            for record in qs
        ]

    def get_trial_balance(
        self,
        tenant_id: int,
        cutoff_date: Optional[str] = None,
    ) -> List[dict]:
        from django.db.models import Sum

        lines_qs = JournalEntryLineModel.objects.filter(entry__tenant_id=tenant_id)
        if cutoff_date:
            lines_qs = lines_qs.filter(entry__date__lte=cutoff_date)

        accounts = AccountModel.objects.filter(tenant_id=tenant_id).order_by('code')
        result = []

        for account in accounts:
            sums = lines_qs.filter(account_id=account.id).aggregate(
                total_debit=Sum('debit'),
                total_credit=Sum('credit'),
            )
            total_debit  = sums['total_debit']  or Decimal('0.00')
            total_credit = sums['total_credit'] or Decimal('0.00')
            # Debit-normal accounts: asset, expense
            if account.type in ('is_active', 'egreso', 'gasto', 'costo'):
                net = total_debit - total_credit
                debit_balance  = net  if net >= 0 else Decimal('0.00')
                credit_balance = abs(net) if net < 0 else Decimal('0.00')
            else:
                net = total_credit - total_debit
                credit_balance = net  if net >= 0 else Decimal('0.00')
                debit_balance  = abs(net) if net < 0 else Decimal('0.00')

            if total_debit > 0 or total_credit > 0:
                result.append({
                    'code':          account.code,
                    'name':          account.name,
                    'type':          account.type,
                    'total_debit':   str(total_debit),
                    'total_credit':  str(total_credit),
                    'debit_balance': str(debit_balance),
                    'credit_balance': str(credit_balance),
                })

        return result

    def entry_exists(self, tenant_id: int, reference: str) -> bool:
        return JournalEntryModel.objects.filter(
            tenant_id=tenant_id,
            reference=reference,
        ).exists()



