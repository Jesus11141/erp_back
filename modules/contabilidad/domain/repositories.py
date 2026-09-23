from abc import ABC, abstractmethod
from typing import Optional, List
from .entities import Account, JournalEntry
from .value_objects import AccountData


class AccountingRepository(ABC):

    @abstractmethod
    def get_or_create_account(self, data: AccountData) -> Account: pass

    @abstractmethod
    def list_accounts(self, tenant_id: int) -> List[Account]: pass

    @abstractmethod
    def save_journal_entry(self, entry: JournalEntry) -> JournalEntry: pass

    @abstractmethod
    def get_journal_entries(self, tenant_id: int) -> List[JournalEntry]: pass

    @abstractmethod
    def get_journal_entry_by_id(self, tenant_id: int, entry_id: int) -> Optional[JournalEntry]: pass

    @abstractmethod
    def get_general_journal(
        self,
        tenant_id: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[dict]: pass

    @abstractmethod
    def get_trial_balance(
        self,
        tenant_id: int,
        cutoff_date: Optional[str] = None,
    ) -> List[dict]: pass

    @abstractmethod
    def entry_exists(self, tenant_id: int, reference: str) -> bool: pass
