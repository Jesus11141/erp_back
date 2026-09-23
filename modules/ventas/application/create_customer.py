from decimal import Decimal
from datetime import date
from ..domain.entities import Customer, Quotation, Order, SaleProduct
from ..domain.repositories import CustomerRepository, QuotationRepository, OrderRepository


class CreateCustomer:
    def __init__(self, repo: CustomerRepository):
        self.repo = repo

    def execute(self, tenant_id: int, data: dict) -> Customer:
        customer = Customer(
            id=0,
            tenant_id=tenant_id,
            name=data.get('name', ''),
            email=data.get('email', ''),
            phone=data.get('phone', ''),
            address=data.get('address', ''),
            rfc=data.get('rfc', ''),
        )
        return self.repo.save(customer)


