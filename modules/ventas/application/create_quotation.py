from decimal import Decimal
from datetime import date
from ..domain.entities import Customer, Quotation, Order, SaleProduct
from ..domain.repositories import CustomerRepository, QuotationRepository, OrderRepository


class CreateQuotation:
    def __init__(self, repo: QuotationRepository, customer_repo: CustomerRepository):
        self.repo = repo
        self.customer_repo = customer_repo

    def execute(self, tenant_id: int, customer_id: int, items: list, notes: str = '', vat=12, validity_days=15, payment_terms='', delivery_time='', print_style='corporativo', show_images=False, is_preinvoice=False, seller_id=None, customer_data=None) -> Quotation:
        if not customer_id:
            if customer_data and customer_data.get('identifier') and customer_data.get('identifier') != '9999999999999':
                # Create or find the provided customer
                customers = self.customer_repo.find_by_name(customer_data['identifier'], tenant_id)
                if customers:
                    customer = customers[0]
                    customer_id = customer.id
                else:
                    customer = Customer(
                        id=0,
                        tenant_id=tenant_id,
                        name=customer_data.get('name', 'CONSUMIDOR FINAL'),
                        email=customer_data.get('email', ''),
                        phone=customer_data.get('phone', ''),
                        address=customer_data.get('address', 'S/D'),
                        rfc=customer_data.get('identifier', '9999999999999'),
                        active=True
                    )
                    customer = self.customer_repo.save(customer)
                    customer_id = customer.id
            else:
                # Try to find default consumer
                customers = self.customer_repo.find_by_name("9999999999999", tenant_id)
                if customers:
                    customer = customers[0]
                    customer_id = customer.id
                else:
                    customer = Customer(
                        id=0,
                        tenant_id=tenant_id,
                        name="CONSUMIDOR FINAL",
                        email="",
                        phone="",
                        address="S/D",
                        rfc="9999999999999",
                        active=True
                    )
                    customer = self.customer_repo.save(customer)
                    customer_id = customer.id
        else:
            customer = self.customer_repo.find_by_id(customer_id, tenant_id)
            if not customer:
                raise ValueError("Customer not found")
        products = [
            SaleProduct(
                product_id=i.get('product_id', 0),
                description=i.get('description', ''),
                quantity=Decimal(str(i.get('quantity', 0))),
                unit_price=Decimal(str(i.get('unit_price', 0))),
                discount=Decimal(str(i.get('discount', 0))),
            ) for i in items
        ]
        quotation = Quotation(
            id=0,
            tenant_id=tenant_id,
            customer_id=customer_id,
            customer_name=customer.name,
            date=date.today(),
            status='draft',
            items=products,
            notes=notes,
            vat=Decimal(str(vat)),
            validity_days=validity_days,
            payment_terms=payment_terms,
            delivery_time=delivery_time,
            print_style=print_style,
            show_images=show_images,
            is_preinvoice=is_preinvoice,
            seller_id=seller_id,
        )
        return self.repo.save(quotation)


