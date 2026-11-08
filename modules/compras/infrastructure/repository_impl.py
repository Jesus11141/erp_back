from typing import List, Optional
from decimal import Decimal
from django.db import transaction
from django.db.models import Q

from ..domain.entities import (
    Proveedor, OrdenCompra, OrdenCompraItem,
    FacturaCompra, FacturaCompraItem,
    CuentaPagar, AbonoCuentaPagar
)
from ..domain.repositories import (
    ProveedorRepository, OrdenCompraRepository,
    FacturaCompraRepository, CuentaPagarRepository
)
from .django_models import (
    ProveedorModel, OrdenCompraModel, OrdenCompraItemModel,
    FacturaCompraModel, FacturaCompraItemModel,
    AccountPayableModel, PayablePaymentModel
)


class DjangoProveedorRepository(ProveedorRepository):
    def _to_entity(self, m: ProveedorModel) -> Proveedor:
        return Proveedor(
            id=m.id,
            tenant_id=m.tenant_id,
            identification=m.identification,
            id_type=m.id_type,
            business_name=m.business_name,
            commercial_name=m.commercial_name,
            email=m.email,
            phone=m.phone,
            address=m.address,
            credit_days=m.credit_days,
            active=m.active,
            bank_name=m.bank_name or '',
            bank_account_type=m.bank_account_type or 'AHO',
            bank_account_number=m.bank_account_number or '',
            beneficiary_name=m.beneficiary_name or '',
            beneficiary_id=m.beneficiary_id or '',
            created_at=m.created_at,
        )

    def save(self, proveedor: Proveedor) -> Proveedor:
        if proveedor.id:
            m = ProveedorModel.objects.get(id=proveedor.id, tenant_id=proveedor.tenant_id)
            m.identification = proveedor.identification
            m.id_type = proveedor.id_type
            m.business_name = proveedor.business_name
            m.commercial_name = proveedor.commercial_name
            m.email = proveedor.email
            m.phone = proveedor.phone
            m.address = proveedor.address
            m.credit_days = proveedor.credit_days
            m.active = proveedor.active
            m.bank_name = proveedor.bank_name
            m.bank_account_type = proveedor.bank_account_type
            m.bank_account_number = proveedor.bank_account_number
            m.beneficiary_name = proveedor.beneficiary_name
            m.beneficiary_id = proveedor.beneficiary_id
            m.save()
        else:
            m = ProveedorModel.objects.create(
                tenant_id=proveedor.tenant_id,
                identification=proveedor.identification,
                id_type=proveedor.id_type,
                business_name=proveedor.business_name,
                commercial_name=proveedor.commercial_name,
                email=proveedor.email,
                phone=proveedor.phone,
                address=proveedor.address,
                credit_days=proveedor.credit_days,
                active=proveedor.active,
                bank_name=proveedor.bank_name,
                bank_account_type=proveedor.bank_account_type,
                bank_account_number=proveedor.bank_account_number,
                beneficiary_name=proveedor.beneficiary_name,
                beneficiary_id=proveedor.beneficiary_id,
            )
        return self._to_entity(m)

    def find_by_id(self, proveedor_id: int, tenant_id: int) -> Optional[Proveedor]:
        m = ProveedorModel.objects.filter(id=proveedor_id, tenant_id=tenant_id).first()
        return self._to_entity(m) if m else None

    def find_by_identification(self, identification: str, tenant_id: int) -> Optional[Proveedor]:
        m = ProveedorModel.objects.filter(identification=identification, tenant_id=tenant_id).first()
        return self._to_entity(m) if m else None

    def list(self, tenant_id: int, query: str = None) -> List[Proveedor]:
        qs = ProveedorModel.objects.filter(tenant_id=tenant_id)
        if query:
            qs = qs.filter(
                Q(identification__icontains=query) |
                Q(business_name__icontains=query) |
                Q(commercial_name__icontains=query)
            )
        return [self._to_entity(m) for m in qs]

    def delete(self, proveedor_id: int, tenant_id: int) -> bool:
        deleted, _ = ProveedorModel.objects.filter(id=proveedor_id, tenant_id=tenant_id).delete()
        return deleted > 0


class DjangoOrdenCompraRepository(OrdenCompraRepository):
    def _to_entity(self, m: OrdenCompraModel) -> OrdenCompra:
        items = [
            OrdenCompraItem(
                id=i.id,
                product_id=i.product_id,
                description=i.description,
                quantity=i.quantity,
                unit_price=i.unit_price,
                discount=i.discount,
                vat_rate=i.vat_rate,
                subtotal=i.subtotal,
            )
            for i in m.items.all()
        ]
        return OrdenCompra(
            id=m.id,
            tenant_id=m.tenant_id,
            number=m.number,
            supplier_id=m.supplier_id,
            supplier_name=m.supplier_name,
            date=m.date,
            expected_delivery_date=m.expected_delivery_date,
            status=m.status,
            payment_terms=m.payment_terms,
            notes=m.notes,
            subtotal=m.subtotal,
            discount=m.discount,
            vat=m.vat,
            total=m.total,
            branch_id=m.branch_id,
            items=items,
            created_at=m.created_at,
        )

    def save(self, orden: OrdenCompra) -> OrdenCompra:
        with transaction.atomic():
            if orden.id:
                m = OrdenCompraModel.objects.get(id=orden.id, tenant_id=orden.tenant_id)
                m.status = orden.status
                m.expected_delivery_date = orden.expected_delivery_date
                m.payment_terms = orden.payment_terms
                m.notes = orden.notes
                m.subtotal = orden.subtotal
                m.discount = orden.discount
                m.vat = orden.vat
                m.total = orden.total
                m.save()
            else:
                m = OrdenCompraModel.objects.create(
                    tenant_id=orden.tenant_id,
                    number=orden.number,
                    supplier_id=orden.supplier_id,
                    supplier_name=orden.supplier_name,
                    date=orden.date,
                    expected_delivery_date=orden.expected_delivery_date,
                    status=orden.status,
                    payment_terms=orden.payment_terms,
                    notes=orden.notes,
                    subtotal=orden.subtotal,
                    discount=orden.discount,
                    vat=orden.vat,
                    total=orden.total,
                    branch_id=orden.branch_id,
                )
                for item in orden.items:
                    OrdenCompraItemModel.objects.create(
                        purchase_order=m,
                        product_id=item.product_id,
                        description=item.description,
                        quantity=item.quantity,
                        unit_price=item.unit_price,
                        discount=item.discount,
                        vat_rate=item.vat_rate,
                        subtotal=item.subtotal,
                    )
        return self._to_entity(m)

    def find_by_id(self, orden_id: int, tenant_id: int) -> Optional[OrdenCompra]:
        m = OrdenCompraModel.objects.filter(id=orden_id, tenant_id=tenant_id).prefetch_related('items').first()
        return self._to_entity(m) if m else None

    def list(self, tenant_id: int, status: str = None) -> List[OrdenCompra]:
        qs = OrdenCompraModel.objects.filter(tenant_id=tenant_id).prefetch_related('items')
        if status:
            qs = qs.filter(status=status)
        return [self._to_entity(m) for m in qs]


class DjangoFacturaCompraRepository(FacturaCompraRepository):
    def _to_entity(self, m: FacturaCompraModel) -> FacturaCompra:
        items = [
            FacturaCompraItem(
                id=i.id,
                product_id=i.product_id,
                description=i.description,
                quantity=i.quantity,
                unit_price=i.unit_price,
                discount=i.discount,
                vat_rate=i.vat_rate,
                subtotal=i.subtotal,
            )
            for i in m.items.all()
        ]
        return FacturaCompra(
            id=m.id,
            tenant_id=m.tenant_id,
            supplier_id=m.supplier_id,
            supplier_name=m.supplier_name,
            invoice_number=m.invoice_number,
            access_key=m.access_key,
            date=m.date,
            registration_date=m.registration_date,
            purchase_type=m.purchase_type,
            payment_condition=m.payment_condition,
            credit_days=m.credit_days,
            due_date=m.due_date,
            status=m.status,
            reception_status=m.reception_status,
            subtotal_0=m.subtotal_0,
            subtotal_iva=m.subtotal_iva,
            discount=m.discount,
            vat=m.vat,
            total=m.total,
            branch_id=m.branch_id,
            purchase_order_id=m.purchase_order_id,
            journal_entry_id=m.journal_entry_id,
            items=items,
            created_at=m.created_at,
        )

    def save(self, factura: FacturaCompra) -> FacturaCompra:
        with transaction.atomic():
            if factura.id:
                m = FacturaCompraModel.objects.get(id=factura.id, tenant_id=factura.tenant_id)
                m.status = factura.status
                m.reception_status = factura.reception_status
                m.journal_entry_id = factura.journal_entry_id
                m.save()
            else:
                m = FacturaCompraModel.objects.create(
                    tenant_id=factura.tenant_id,
                    supplier_id=factura.supplier_id,
                    supplier_name=factura.supplier_name,
                    invoice_number=factura.invoice_number,
                    access_key=factura.access_key,
                    date=factura.date,
                    registration_date=factura.registration_date,
                    purchase_type=factura.purchase_type,
                    payment_condition=factura.payment_condition,
                    credit_days=factura.credit_days,
                    due_date=factura.due_date,
                    status=factura.status,
                    reception_status=factura.reception_status,
                    subtotal_0=factura.subtotal_0,
                    subtotal_iva=factura.subtotal_iva,
                    discount=factura.discount,
                    vat=factura.vat,
                    total=factura.total,
                    branch_id=factura.branch_id,
                    purchase_order_id=factura.purchase_order_id,
                    journal_entry_id=factura.journal_entry_id,
                )
                for item in factura.items:
                    FacturaCompraItemModel.objects.create(
                        invoice=m,
                        product_id=item.product_id,
                        description=item.description,
                        quantity=item.quantity,
                        unit_price=item.unit_price,
                        discount=item.discount,
                        vat_rate=item.vat_rate,
                        subtotal=item.subtotal,
                    )
        return self._to_entity(m)

    def find_by_id(self, factura_id: int, tenant_id: int) -> Optional[FacturaCompra]:
        m = FacturaCompraModel.objects.filter(id=factura_id, tenant_id=tenant_id).prefetch_related('items').first()
        return self._to_entity(m) if m else None

    def list(self, tenant_id: int) -> List[FacturaCompra]:
        qs = FacturaCompraModel.objects.filter(tenant_id=tenant_id).prefetch_related('items')
        return [self._to_entity(m) for m in qs]


class DjangoCuentaPagarRepository(CuentaPagarRepository):
    def _to_entity(self, m: AccountPayableModel) -> CuentaPagar:
        return CuentaPagar(
            id=m.id,
            tenant_id=m.tenant_id,
            supplier_id=m.supplier_id,
            supplier_name=m.supplier_name,
            invoice_id=m.invoice_id,
            invoice_number=m.invoice_number,
            total_amount=m.total_amount,
            balance_due=m.balance_due,
            due_date=m.due_date,
            status=m.status,
            created_at=m.created_at,
        )

    def _to_payment_entity(self, m: PayablePaymentModel) -> AbonoCuentaPagar:
        return AbonoCuentaPagar(
            id=m.id,
            tenant_id=m.tenant_id,
            account_payable_id=m.account_payable_id,
            amount=m.amount,
            payment_date=m.payment_date,
            payment_method=m.payment_method,
            reference=m.reference,
            notes=m.notes,
            created_at=m.created_at,
        )

    def save(self, cuenta: CuentaPagar) -> CuentaPagar:
        if cuenta.id:
            m = AccountPayableModel.objects.get(id=cuenta.id, tenant_id=cuenta.tenant_id)
            m.balance_due = cuenta.balance_due
            m.status = cuenta.status
            m.save()
        else:
            m = AccountPayableModel.objects.create(
                tenant_id=cuenta.tenant_id,
                supplier_id=cuenta.supplier_id,
                supplier_name=cuenta.supplier_name,
                invoice_id=cuenta.invoice_id,
                invoice_number=cuenta.invoice_number,
                total_amount=cuenta.total_amount,
                balance_due=cuenta.balance_due,
                due_date=cuenta.due_date,
                status=cuenta.status,
            )
        return self._to_entity(m)

    def find_by_id(self, cuenta_id: int, tenant_id: int) -> Optional[CuentaPagar]:
        m = AccountPayableModel.objects.filter(id=cuenta_id, tenant_id=tenant_id).first()
        return self._to_entity(m) if m else None

    def list(self, tenant_id: int, status: str = None) -> List[CuentaPagar]:
        qs = AccountPayableModel.objects.filter(tenant_id=tenant_id)
        if status:
            qs = qs.filter(status=status)
        return [self._to_entity(m) for m in qs]

    def add_payment(self, abono: AbonoCuentaPagar) -> AbonoCuentaPagar:
        with transaction.atomic():
            cp = AccountPayableModel.objects.select_for_update().get(id=abono.account_payable_id, tenant_id=abono.tenant_id)
            m = PayablePaymentModel.objects.create(
                tenant_id=abono.tenant_id,
                account_payable=cp,
                amount=abono.amount,
                payment_date=abono.payment_date,
                payment_method=abono.payment_method,
                reference=abono.reference,
                notes=abono.notes,
            )
            cp.balance_due = max(Decimal('0.00'), cp.balance_due - abono.amount)
            if cp.balance_due <= Decimal('0.00'):
                cp.status = 'PAID'
            else:
                cp.status = 'PARTIAL'
            cp.save()
            return self._to_payment_entity(m)

    def list_payments(self, cuenta_id: int, tenant_id: int) -> List[AbonoCuentaPagar]:
        qs = PayablePaymentModel.objects.filter(account_payable_id=cuenta_id, tenant_id=tenant_id)
        return [self._to_payment_entity(m) for m in qs]
