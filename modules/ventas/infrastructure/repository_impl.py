from typing import Optional, List
from django.db import models
from ..domain.entities import Customer, Quotation, Order, SaleProduct, PaymentMethod
from ..domain.repositories import CustomerRepository, QuotationRepository, OrderRepository, PaymentMethodRepository
from .django_models import CustomerModel, QuotationModel, QuotationItemModel, OrderModel, OrderItemModel

class DjangoCustomerRepository(CustomerRepository):
    def _to_entity(self, m) -> Customer:
        return Customer(
            id=m.id,
            tenant_id=m.tenant_id,
            name=m.name,
            email=m.email,
            phone=m.phone,
            address=m.address,
            rfc=m.rfc,
            active=m.active
        )

    def save(self, customer: Customer) -> Customer:
        if customer.id:
            m = CustomerModel.objects.get(id=customer.id)
            m.name = customer.name
            m.email = customer.email
            m.phone = customer.phone
            m.address = customer.address
            m.rfc = customer.rfc
            m.active = customer.active
            m.save()
        else:
            m = CustomerModel.objects.create(
                tenant_id=customer.tenant_id,
                name=customer.name,
                email=customer.email,
                phone=customer.phone,
                address=customer.address,
                rfc=customer.rfc,
                active=customer.active
            )
        return self._to_entity(m)

    def find_by_id(self, id: int, tenant_id: int) -> Optional[Customer]:
        try:
            return self._to_entity(CustomerModel.objects.get(id=id, tenant_id=tenant_id))
        except CustomerModel.DoesNotExist:
            return None

    def list_by_tenant(self, tenant_id: int) -> List[Customer]:
        return [self._to_entity(m) for m in CustomerModel.objects.filter(tenant_id=tenant_id, active=True)]

    def find_by_name(self, name: str, tenant_id: int) -> List[Customer]:
        qs = CustomerModel.objects.filter(tenant_id=tenant_id, active=True)
        return [self._to_entity(m) for m in qs.filter(
            models.Q(name__icontains=name) | models.Q(rfc__icontains=name)
        )]

def _items_to_entities(items_qs):
    return [
        SaleProduct(
            product_id=i.product_id,
            description=i.description,
            quantity=i.quantity,
            unit_price=i.unit_price,
            discount=i.discount
        )
        for i in items_qs.all()
    ]

class DjangoQuotationRepository(QuotationRepository):
    def _to_entity(self, m, vat_percent=None) -> Quotation:
        if vat_percent is None:
            from modules.parametros.infrastructure.django_models import ParameterModel
            from decimal import Decimal
            try:
                vat_param = ParameterModel.objects.get(tenant_id=m.tenant_id, module='ventas', key='iva')
                vat_percent = Decimal(vat_param.value)
            except Exception:
                vat_percent = Decimal('12')

        return Quotation(
            id=m.id,
            tenant_id=m.tenant_id,
            customer_id=m.customer_id,
            customer_name=m.customer_name,
            date=m.date,
            status=m.status,
            items=_items_to_entities(m.items),
            notes=m.notes,
            vat=vat_percent,
            validity_days=getattr(m, 'validity_days', 15),
            payment_terms=getattr(m, 'payment_terms', ''),
            delivery_time=getattr(m, 'delivery_time', ''),
            print_style=getattr(m, 'print_style', 'corporativo'),
            show_images=getattr(m, 'show_images', False),
            is_preinvoice=getattr(m, 'is_preinvoice', False),
            seller_id=getattr(m, 'seller_id', None),
            branch_id=getattr(m, 'branch_id', None)
        )

    def save(self, quotation: Quotation) -> Quotation:
        if quotation.id:
            m = QuotationModel.objects.get(id=quotation.id)
            m.status = quotation.status
            m.save()
        else:
            m = QuotationModel.objects.create(
                tenant_id=quotation.tenant_id,
                customer_id=quotation.customer_id,
                customer_name=quotation.customer_name,
                status=quotation.status,
                notes=quotation.notes,
                validity_days=quotation.validity_days,
                payment_terms=quotation.payment_terms,
                delivery_time=quotation.delivery_time,
                print_style=quotation.print_style,
                show_images=quotation.show_images,
                is_preinvoice=quotation.is_preinvoice,
                seller_id=quotation.seller_id,
                branch_id=quotation.branch_id
            )
            for item in quotation.items:
                QuotationItemModel.objects.create(
                    quotation=m,
                    product_id=item.product_id,
                    description=item.description,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    discount=item.discount
                )
        return self._to_entity(m)

    def find_by_id(self, id: int, tenant_id: int) -> Optional[Quotation]:
        try:
            return self._to_entity(QuotationModel.objects.get(id=id, tenant_id=tenant_id))
        except QuotationModel.DoesNotExist:
            return None

    def list_by_tenant(self, tenant_id: int) -> List[Quotation]:
        from modules.parametros.infrastructure.django_models import ParameterModel
        from decimal import Decimal
        try:
            vat_param = ParameterModel.objects.get(tenant_id=tenant_id, module='ventas', key='iva')
            vat_percent = Decimal(vat_param.value)
        except Exception:
            vat_percent = Decimal('12')
            
        return [self._to_entity(m, vat_percent) for m in QuotationModel.objects.filter(tenant_id=tenant_id)]

    def next_number(self, tenant_id: int) -> str:
        count = QuotationModel.objects.filter(tenant_id=tenant_id).count()
        return f"COT-{tenant_id}-{str(count + 1).zfill(5)}"

class DjangoOrderRepository(OrderRepository):
    def _to_entity(self, m) -> Order:
        return Order(
            id=m.id,
            tenant_id=m.tenant_id,
            customer_id=m.customer_id,
            customer_name=m.customer_name,
            quotation_id=m.quotation_id,
            date=m.date,
            status=m.status,
            items=_items_to_entities(m.items)
        )

    def save(self, order: Order) -> Order:
        if order.id:
            m = OrderModel.objects.get(id=order.id)
            m.status = order.status
            m.save()
        else:
            m = OrderModel.objects.create(
                tenant_id=order.tenant_id,
                customer_id=order.customer_id,
                customer_name=order.customer_name,
                quotation_id=order.quotation_id,
                status=order.status
            )
            for item in order.items:
                OrderItemModel.objects.create(
                    order=m,
                    product_id=item.product_id,
                    description=item.description,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    discount=item.discount
                )
        return self._to_entity(m)

    def find_by_id(self, id: int, tenant_id: int) -> Optional[Order]:
        try:
            return self._to_entity(OrderModel.objects.get(id=id, tenant_id=tenant_id))
        except OrderModel.DoesNotExist:
            return None

    def list_by_tenant(self, tenant_id: int) -> List[Order]:
        return [self._to_entity(m) for m in OrderModel.objects.filter(tenant_id=tenant_id)]

    def delete(self, order_id: int):
        OrderModel.objects.filter(id=order_id).delete()

def _infer_sri_code(name: str) -> str:
    n = (name or '').lower()
    if 'efectivo' in n or 'cash' in n:
        return '01'
    if 'débito' in n or 'debito' in n:
        return '16'
    if 'crédito' in n or 'credito' in n or 'tarjeta' in n or 'card' in n:
        return '19'
    if any(k in n for k in ['transfer', 'banco', 'depósito', 'deposito', 'cheque', 'pichincha', 'guayaquil', 'produbanco', 'pacifico', 'deuna', 'de una']):
        return '20'
    if 'compensaci' in n:
        return '15'
    if 'dinero elect' in n:
        return '17'
    if 'prepago' in n:
        return '18'
    if 'endoso' in n:
        return '21'
    return '20'

class DjangoPaymentMethodRepository(PaymentMethodRepository):
    def _to_entity(self, m) -> PaymentMethod:
        sri_code = getattr(m, 'sri_code', None) or _infer_sri_code(m.name)
        return PaymentMethod(
            id=m.id,
            tenant_id=m.tenant_id,
            name=m.name,
            active=m.active,
            requires_reference=m.requires_reference,
            sri_code=sri_code or '01'
        )

    def save(self, p: PaymentMethod) -> PaymentMethod:
        from .django_models import PaymentMethodModel
        sri = p.sri_code or _infer_sri_code(p.name)
        data = {
            'tenant_id': p.tenant_id,
            'name': p.name,
            'active': p.active,
            'requires_reference': p.requires_reference,
            'sri_code': sri or '01'
        }
        if p.id:
            PaymentMethodModel.objects.filter(id=p.id, tenant_id=p.tenant_id).update(**data)
            m = PaymentMethodModel.objects.get(id=p.id)
        else:
            m = PaymentMethodModel.objects.create(**data)
        return self._to_entity(m)

    def find_all(self, tenant_id: int, include_inactive: bool = False) -> List[PaymentMethod]:
        from .django_models import PaymentMethodModel
        qs = PaymentMethodModel.objects.filter(tenant_id=tenant_id)
        if not include_inactive:
            qs = qs.filter(active=True)
        return [self._to_entity(m) for m in qs.order_by('name')]

    def delete(self, method_id: int, tenant_id: int):
        from .django_models import PaymentMethodModel
        PaymentMethodModel.objects.filter(id=method_id, tenant_id=tenant_id).delete()

    def find_by_id(self, id: int, tenant_id: int) -> Optional[PaymentMethod]:
        from .django_models import PaymentMethodModel
        try:
            m = PaymentMethodModel.objects.get(id=id, tenant_id=tenant_id)
            return self._to_entity(m)
        except PaymentMethodModel.DoesNotExist:
            return None

from ..domain.entities import AccountReceivable, ReceivablePayment
from ..domain.repositories import AccountReceivableRepository
from .django_models import AccountReceivableModel, ReceivablePaymentModel

class DjangoAccountReceivableRepository(AccountReceivableRepository):
    def _to_entity(self, m) -> AccountReceivable:
        return AccountReceivable(
            id=m.id,
            tenant_id=m.tenant_id,
            customer_id=m.customer_id,
            customer_name=m.customer_name,
            total_amount=m.total_amount,
            balance_due=m.balance_due,
            status=m.status,
            reference_type=m.reference_type,
            reference_id=m.reference_id
        )

    def save(self, ar: AccountReceivable) -> AccountReceivable:
        if ar.id:
            m = AccountReceivableModel.objects.get(id=ar.id)
            m.total_amount = ar.total_amount
            m.balance_due = ar.balance_due
            m.status = ar.status
            m.save()
        else:
            m = AccountReceivableModel.objects.create(
                tenant_id=ar.tenant_id,
                customer_id=ar.customer_id,
                customer_name=ar.customer_name,
                total_amount=ar.total_amount,
                balance_due=ar.balance_due,
                status=ar.status,
                reference_type=ar.reference_type,
                reference_id=ar.reference_id
            )
        return self._to_entity(m)

    def find_by_id(self, id: int, tenant_id: int) -> Optional[AccountReceivable]:
        try:
            return self._to_entity(AccountReceivableModel.objects.get(id=id, tenant_id=tenant_id))
        except AccountReceivableModel.DoesNotExist:
            return None

    def list_by_tenant(self, tenant_id: int) -> List[AccountReceivable]:
        return [self._to_entity(m) for m in AccountReceivableModel.objects.filter(tenant_id=tenant_id)]

    def find_by_reference(self, reference_type: str, reference_id: int, tenant_id: int) -> Optional[AccountReceivable]:
        try:
            return self._to_entity(AccountReceivableModel.objects.get(reference_type=reference_type, reference_id=reference_id, tenant_id=tenant_id))
        except AccountReceivableModel.DoesNotExist:
            return None

    def add_payment(self, payment: ReceivablePayment) -> ReceivablePayment:
        m = ReceivablePaymentModel.objects.create(
            account_receivable_id=payment.account_receivable_id,
            amount=payment.amount,
            payment_method=payment.payment_method,
            notes=payment.notes
        )
        payment.id = m.id
        payment.date = m.date
        return payment

    def get_payments(self, account_receivable_id: int) -> List[ReceivablePayment]:
        qs = ReceivablePaymentModel.objects.filter(account_receivable_id=account_receivable_id)
        return [
            ReceivablePayment(
                id=m.id,
                account_receivable_id=m.account_receivable_id,
                amount=m.amount,
                payment_method=m.payment_method,
                date=m.date,
                notes=m.notes
            ) for m in qs
        ]
