from decimal import Decimal
from datetime import date
from ..domain.entities import Customer, Quotation, Order, SaleProduct
from ..domain.repositories import CustomerRepository, QuotationRepository, OrderRepository


class ConvertQuotationToOrder:
    def __init__(self, quotation_repo: QuotationRepository, order_repo: OrderRepository):
        self.quotation_repo = quotation_repo
        self.order_repo = order_repo

    def execute(self, quotation_id: int, tenant_id: int) -> Order:
        quotation = self.quotation_repo.find_by_id(quotation_id, tenant_id)
        if not quotation:
            raise ValueError("Quotation not found")
        quotation.accept()
        self.quotation_repo.save(quotation)
        order = Order(
            id=0,
            tenant_id=tenant_id,
            customer_id=quotation.customer_id,
            customer_name=quotation.customer_name,
            quotation_id=quotation.id,
            date=date.today(),
            status='pending',
            items=quotation.items,
        )
        return self.order_repo.save(order)

