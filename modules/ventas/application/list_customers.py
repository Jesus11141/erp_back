from decimal import Decimal
from datetime import date
from ..domain.entities import Customer, Quotation, Order, SaleProduct
from ..domain.repositories import CustomerRepository, QuotationRepository, OrderRepository


class ListCustomers:
    def __init__(self, repo: CustomerRepository):
        self.repo = repo

    def execute(self, tenant_id: int, query: str = '') -> list:
        if query:
            return self.repo.find_by_name(query, tenant_id)
        return self.repo.list_by_tenant(tenant_id)


