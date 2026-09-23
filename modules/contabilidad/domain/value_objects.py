from dataclasses import dataclass
from enum import Enum
from typing import Optional


class AccountType(Enum):
    """Valid account types in the chart of accounts."""
    ASSET     = 'is_active'
    LIABILITY = 'pasivo'
    EQUITY    = 'patrimonio'
    REVENUE   = 'ingreso'
    EXPENSE   = 'egreso'


@dataclass(frozen=True)
class AccountCode:
    """Account code value object. Example: '1.1.01.01'"""
    value: str

    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValueError("Account code cannot be empty")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class AccountData:
    """Value object grouping all data needed to create or look up an account."""
    tenant_id: int
    code:      AccountCode
    name:      str
    type:      AccountType
    parent_id: Optional[int] = None

