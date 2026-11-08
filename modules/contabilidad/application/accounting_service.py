from datetime import date
from decimal import Decimal
from typing import Optional, List

from ..domain.entities import Account, JournalEntry, JournalEntryLine
from ..domain.repositories import AccountingRepository
from ..domain.value_objects import AccountData


class AccountingService:
    """
    Pure application service for accounting.
    Contains only business logic â€” no ORM, no framework dependencies.
    """

    def __init__(self, repo: AccountingRepository):
        self._repo = repo

    # ------------------------------------------------------------------
    # Accounts
    # ------------------------------------------------------------------

    def get_or_create_account(self, data: AccountData) -> Account:
        return self._repo.get_or_create_account(data)

    # ------------------------------------------------------------------
    # Journal Entries
    # ------------------------------------------------------------------

    def create_journal_entry(
        self,
        tenant_id: int,
        description: str,
        lines: list,
        entry_date: Optional[date] = None,
        reference: str = '',
    ) -> JournalEntry:
        """
        Creates a balanced journal entry.

        Args:
            tenant_id:   Company ID.
            description: Entry description (memo/description).
            lines:       List of dicts with keys: account_id, debit, credit.
            entry_date:  Date of the entry; defaults to today if None.
            reference:   External reference, e.g. 'payroll_5', 'pos_sale_12'.

        Raises:
            ValueError: If fewer than 2 lines are provided, or debits â‰  credits.
        """
        if not lines or len(lines) < 2:
            raise ValueError(
                "A journal entry requires at least 2 lines (one debit and one credit)"
            )

        # Control de Período Contable / Cierre Fiscal
        target_date = entry_date or date.today()
        from .period_service import validate_accounting_period
        validate_accounting_period(tenant_id, target_date, user_role='contador', action_desc='registrar asientos en el libro diario')

        total_debit  = Decimal('0.00')
        total_credit = Decimal('0.00')
        entry_lines  = []

        for line in lines:
            debit  = Decimal(str(line.get('debit',  0)))
            credit = Decimal(str(line.get('credit', 0)))
            total_debit  += debit
            total_credit += credit

            entry_lines.append(JournalEntryLine(
                id=0,
                account_id=line['account_id'],
                debit=debit,
                credit=credit,
                account_code=line.get('account_code', ''),
                account_name=line.get('account_name', ''),
            ))

        if abs(total_debit - total_credit) > Decimal('0.01'):
            raise ValueError(
                f"Journal entry is not balanced. "
                f"Total debit: {total_debit} / Total credit: {total_credit}"
            )

        entry = JournalEntry(
            id=0,
            tenant_id=tenant_id,
            date=entry_date or date.today(),
            description=description,
            type='general',
            reference=reference,
            lines=entry_lines,
        )
        return self._repo.save_journal_entry(entry)

    def initialize_default_accounts(self, tenant_id: int):
        from ..domain.value_objects import AccountType, AccountCode
        defaults = [
            (AccountCode('1.0.00.00'), 'Activos', AccountType.ASSET, None),
            (AccountCode('1.1.00.00'), 'Activos Corrientes', AccountType.ASSET, '1.0.00.00'),
            (AccountCode('1.1.01.01'), 'Caja y Bancos', AccountType.ASSET, '1.1.00.00'),
            (AccountCode('1.1.02.01'), 'Cuentas por Cobrar', AccountType.ASSET, '1.1.00.00'),
            (AccountCode('1.1.03.01'), 'Inventario', AccountType.ASSET, '1.1.00.00'),
            (AccountCode('2.0.00.00'), 'Pasivos', AccountType.LIABILITY, None),
            (AccountCode('2.1.00.00'), 'Pasivos Corrientes', AccountType.LIABILITY, '2.0.00.00'),
            (AccountCode('2.1.01.01'), 'Cuentas por Pagar', AccountType.LIABILITY, '2.1.00.00'),
            (AccountCode('2.1.03.01'), 'IVA por Pagar', AccountType.LIABILITY, '2.1.00.00'),
            (AccountCode('2.1.04.01'), 'Anticipos de Clientes', AccountType.LIABILITY, '2.1.00.00'),
            (AccountCode('3.0.00.00'), 'Patrimonio', AccountType.EQUITY, None),
            (AccountCode('3.1.01.01'), 'Capital Social', AccountType.EQUITY, '3.0.00.00'),
            (AccountCode('4.0.00.00'), 'Ingresos', AccountType.REVENUE, None),
            (AccountCode('4.1.01.01'), 'Ingresos por Ventas', AccountType.REVENUE, '4.0.00.00'),
            (AccountCode('5.0.00.00'), 'Egresos', AccountType.EXPENSE, None),
            (AccountCode('5.1.01.01'), 'Costo de Ventas', AccountType.EXPENSE, '5.0.00.00'),
            (AccountCode('5.2.01.01'), 'Gastos Operativos', AccountType.EXPENSE, '5.0.00.00'),
        ]
        
        # Two-pass insertion to handle parents
        for code, name, acc_type, parent_code_str in defaults:
            parent_id = None
            if parent_code_str:
                from ..infrastructure.django_models import AccountModel
                parent = AccountModel.objects.filter(tenant_id=tenant_id, code=parent_code_str).first()
                if parent:
                    parent_id = parent.id
                    
            self.get_or_create_account(AccountData(
                tenant_id=tenant_id,
                code=code,
                name=name,
                type=acc_type,
                parent_id=parent_id
            ))

    def register_sale_journal_entry(
        self,
        tenant_id: int,
        invoice,
    ) -> JournalEntry:
        """
        Creates a journal entry for a sale (Invoice).
        Debit: Accounts Receivable (or Cash)
        Credit: Sales Revenue
        Credit: VAT Payable
        """
        subtotal = sum((item.quantity * item.unit_price) - item.discount for item in invoice.items)
        vat_amount = sum(
            ((item.quantity * item.unit_price) - item.discount) * (Decimal(item.vat_rate) / Decimal('100'))
            for item in invoice.items if getattr(item, 'vat_rate', None) and item.vat_rate != '0'
        )
        total = subtotal + vat_amount

        # Fetch accounts to get their IDs
        # 1.1.01.01 - Caja y Bancos (En lugar de Cuentas por Cobrar para ventas directas)
        # 4.1.01.01 - Sales Revenue
        # 2.1.03.01 - VAT Payable
        accounts = self._repo.list_accounts(tenant_id)
        account_map = {acc.code: acc.id for acc in accounts}
        
        ar_account_id = account_map.get('1.1.01.01')
        sales_account_id = account_map.get('4.1.01.01')
        vat_account_id = account_map.get('2.1.03.01')
        
        if not all([ar_account_id, sales_account_id, vat_account_id]):
            # Inject defaults if the required ones are missing
            self.initialize_default_accounts(tenant_id)
            accounts = self._repo.list_accounts(tenant_id)
            account_map = {acc.code: acc.id for acc in accounts}
            
            ar_account_id = account_map.get('1.1.01.01')
            sales_account_id = account_map.get('4.1.01.01')
            vat_account_id = account_map.get('2.1.03.01')

            if not all([ar_account_id, sales_account_id, vat_account_id]):
                raise ValueError("Default accounts for sales are missing. Please initialize Chart of Accounts.")

        lines = [
            {'account_id': ar_account_id, 'debit': total, 'credit': Decimal('0.00')},
            {'account_id': sales_account_id, 'debit': Decimal('0.00'), 'credit': subtotal},
        ]
        
        if vat_amount > Decimal('0.00'):
            lines.append({'account_id': vat_account_id, 'debit': Decimal('0.00'), 'credit': vat_amount})

        description = f"Venta según Factura {invoice.number}"

        return self.create_journal_entry(
            tenant_id=tenant_id,
            description=description,
            lines=lines,
            entry_date=invoice.date,
            reference=f"factura_{invoice.number}"
        )

    def register_work_order_advance(self, tenant_id: int, order_id: int, amount: Decimal, date=None):
        if amount <= 0: return None
        accounts = self._repo.list_accounts(tenant_id)
        account_map = {acc.code: acc.id for acc in accounts}
        
        cash_account_id = account_map.get('1.1.01.01')
        advance_account_id = account_map.get('2.1.04.01')
        
        if not all([cash_account_id, advance_account_id]):
            self.initialize_default_accounts(tenant_id)
            accounts = self._repo.list_accounts(tenant_id)
            account_map = {acc.code: acc.id for acc in accounts}
            cash_account_id = account_map.get('1.1.01.01')
            advance_account_id = account_map.get('2.1.04.01')
            if not all([cash_account_id, advance_account_id]):
                return None
                
        lines = [
            {'account_id': cash_account_id, 'debit': amount, 'credit': Decimal('0.00')},
            {'account_id': advance_account_id, 'debit': Decimal('0.00'), 'credit': amount},
        ]
        
        from datetime import date as dt_date
        return self.create_journal_entry(
            tenant_id=tenant_id,
            description=f"Abono de Servicio Técnico OT #{order_id}",
            lines=lines,
            entry_date=date or dt_date.today(),
            reference=f"abono_ot_{order_id}"
        )

    def register_work_order_liquidation(self, tenant_id: int, order_id: int, total: Decimal, previous_advance: Decimal, current_payment: Decimal, date=None):
        accounts = self._repo.list_accounts(tenant_id)
        account_map = {acc.code: acc.id for acc in accounts}
        
        cash_account_id = account_map.get('1.1.01.01')
        advance_account_id = account_map.get('2.1.04.01')
        revenue_account_id = account_map.get('4.1.01.01')
        
        if not all([cash_account_id, advance_account_id, revenue_account_id]):
            self.initialize_default_accounts(tenant_id)
            accounts = self._repo.list_accounts(tenant_id)
            account_map = {acc.code: acc.id for acc in accounts}
            cash_account_id = account_map.get('1.1.01.01')
            advance_account_id = account_map.get('2.1.04.01')
            revenue_account_id = account_map.get('4.1.01.01')
            
        lines = []
        if previous_advance > 0:
            lines.append({'account_id': advance_account_id, 'debit': previous_advance, 'credit': Decimal('0.00')})
        if current_payment > 0:
            lines.append({'account_id': cash_account_id, 'debit': current_payment, 'credit': Decimal('0.00')})
            
        lines.append({'account_id': revenue_account_id, 'debit': Decimal('0.00'), 'credit': total})
        
        from datetime import date as dt_date
        return self.create_journal_entry(
            tenant_id=tenant_id,
            description=f"Liquidación de Servicio Técnico OT #{order_id}",
            lines=lines,
            entry_date=date or dt_date.today(),
            reference=f"liq_ot_{order_id}"
        )

    # ------------------------------------------------------------------
    # Reports
    # ------------------------------------------------------------------

    def get_general_journal(
        self,
        tenant_id: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[dict]:
        return self._repo.get_general_journal(tenant_id, start_date, end_date)

    def get_trial_balance(
        self,
        tenant_id: int,
        cutoff_date: Optional[str] = None,
    ) -> List[dict]:
        return self._repo.get_trial_balance(tenant_id, cutoff_date)

