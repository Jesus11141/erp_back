from decimal import Decimal
from datetime import date
from ..domain.entities import Customer, Quotation, Order, SaleProduct
from ..domain.repositories import CustomerRepository, QuotationRepository, OrderRepository


class SendQuotation:
    def __init__(self, repo: QuotationRepository):
        self.repo = repo

    def execute(self, quotation_id: int, tenant_id: int) -> Quotation:
        quotation = self.repo.find_by_id(quotation_id, tenant_id)
        if not quotation:
            raise ValueError("Quotation not found")
        quotation.send()
        return self.repo.save(quotation)


