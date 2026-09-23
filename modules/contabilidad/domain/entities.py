from dataclasses import dataclass, field
from decimal import Decimal
from datetime import date
from typing import List, Optional


@dataclass
class Account:
    id: int
    tenant_id: int
    code: str
    name: str
    type: str
    parent_id: Optional[int] = None


@dataclass
class JournalEntryLine:
    id: int
    account_id: int
    debit: Decimal
    credit: Decimal
    account_code: str = ''
    account_name: str = ''


@dataclass
class JournalEntry:
    id: int
    tenant_id: int
    date: date
    description: str
    type: str = 'general'
    reference: str = ''
    lines: List[JournalEntryLine] = field(default_factory=list)
