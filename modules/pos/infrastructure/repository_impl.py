from decimal import Decimal
from typing import Optional, List
from django.db.models import Sum, Count
from ..domain.entities import CashRegister, POSSale, POSSaleItem, CashRegisterClosure, POSCustomer, POSSaleSummary, CashRegisterMovement
from ..domain.repositories import CashRegisterRepository, POSSaleRepository, POSDependencyRepository, POSInventoryService, POSBillingService, POSAccountingService
from .django_models import CashRegisterModel, CashRegisterClosureModel, POSSaleModel, POSSaleItemModel, PhysicalCashRegisterModel, CashRegisterMovementModel

class DjangoCashRegisterRepository(CashRegisterRepository):
    def _to_entity(self, m: CashRegisterModel) -> CashRegister:
        status = 'open' if m.status == 'open' else 'closed'
        return CashRegister(
            id=m.id,
            tenant_id=m.tenant_id,
            name=m.name,
            user_id=m.user_id,
            status=status,
            initial_balance=m.initial_balance,
            final_balance=m.final_balance,
            opened_at=m.opened_at,
            closed_at=m.closed_at,
            opening_breakdown=m.opening_breakdown,
            branch_id=m.branch_id,
            emission_point=getattr(m, 'emission_point', '001')
        )

    def save(self, register: CashRegister) -> CashRegister:
        status = 'open' if register.status == 'open' else 'closed'
        if register.id:
            m = CashRegisterModel.objects.get(id=register.id)
            m.status = status
            m.initial_balance = register.initial_balance
            m.final_balance = register.final_balance
            m.opened_at = register.opened_at
            m.closed_at = register.closed_at
            m.opening_breakdown = register.opening_breakdown
            m.branch_id = register.branch_id
            m.emission_point = register.emission_point
            m.save()
        else:
            m = CashRegisterModel.objects.create(
                tenant_id=register.tenant_id,
                name=register.name,
                user_id=register.user_id,
                status=status,
                initial_balance=register.initial_balance,
                opened_at=register.opened_at,
                opening_breakdown=register.opening_breakdown,
                branch_id=register.branch_id,
                emission_point=register.emission_point
            )
        return self._to_entity(m)

    def get_by_id(self, register_id: int, tenant_id: int) -> Optional[CashRegister]:
        try:
            return self._to_entity(CashRegisterModel.objects.get(id=register_id, tenant_id=tenant_id))
        except CashRegisterModel.DoesNotExist:
            return None

    def get_open_register(self, tenant_id: int, user_id: int) -> Optional[CashRegister]:
        try:
            record = CashRegisterModel.objects.filter(
                tenant_id=tenant_id,
                user_id=user_id,
                status='open'
            ).latest('opened_at')
            return self._to_entity(record)
        except CashRegisterModel.DoesNotExist:
            return None

    def save_closure(self, closure: CashRegisterClosure) -> CashRegisterClosure:
        # Translate closure breakdown to Spanish dict structure expected by database / legacy reports
        transactions_es = []
        pm_es = {'cash': 'efectivo', 'card': 'tarjeta', 'transfer': 'transferencia'}
        
        eng_breakdown = closure.closure_breakdown or {}
        eng_transactions = eng_breakdown.get('transactions', [])
        from django.utils import timezone
        
        for t in eng_transactions:
            transactions_es.append({
                'id': t.sale_id,
                'fecha': timezone.localtime(t.created_at).strftime('%Y-%m-%d %H:%M:%S') if t.created_at else '',
                'cliente': t.customer_name,
                'metodo_pago': pm_es.get(t.payment_method, 'efectivo'),
                'comprobante': t.reference_number,
                'total': float(t.total)
            })
            
        eng_counts = eng_breakdown.get('counts', {})
        counts_es = {
            'efectivo': eng_counts.get('cash', 0),
            'tarjeta': eng_counts.get('card', 0),
            'transferencia': eng_counts.get('transfer', 0)
        }
        
        complete_closure_breakdown = {
            'transacciones': transactions_es,
            'conteos': counts_es,
            'efectivo_desglose': eng_breakdown.get('cash_breakdown')
        }

        record, _ = CashRegisterClosureModel.objects.update_or_create(
            register_id=closure.register_id,
            defaults=dict(
                tenant_id=closure.tenant_id,
                user_id=closure.user_id,
                opened_at=closure.opened_at,
                closed_at=closure.closed_at,
                initial_balance=closure.initial_balance,
                total_cash=closure.total_cash,
                total_card=closure.total_card,
                total_transfer=closure.total_transfer,
                sales_count=closure.sales_count,
                expected_balance=closure.expected_balance,
                counted_balance=closure.counted_balance,
                difference=closure.difference,
                observations=closure.observations,
                closure_breakdown=complete_closure_breakdown,
            ),
        )
        closure.id = record.id
        return closure

    def has_active_physical_registers(self, tenant_id: int) -> bool:
        return PhysicalCashRegisterModel.objects.filter(tenant_id=tenant_id, active=True).exists()

    def save_movement(self, movement: CashRegisterMovement) -> CashRegisterMovement:
        m = CashRegisterMovementModel.objects.create(
            tenant_id=movement.tenant_id,
            register_id=movement.register_id,
            user_id=movement.user_id,
            movement_type=movement.movement_type,
            amount=movement.amount,
            reason=movement.reason
        )
        movement.id = m.id
        movement.created_at = m.created_at
        return movement

    def get_movements_by_register(self, register_id: int, tenant_id: int) -> List[CashRegisterMovement]:
        records = CashRegisterMovementModel.objects.filter(register_id=register_id, tenant_id=tenant_id)
        return [
            CashRegisterMovement(
                id=r.id,
                tenant_id=r.tenant_id,
                register_id=r.register_id,
                user_id=r.user_id,
                movement_type=r.movement_type,
                amount=r.amount,
                reason=r.reason,
                created_at=r.created_at
            ) for r in records
        ]


class DjangoPOSSaleRepository(POSSaleRepository):
    def _to_entity(self, m: POSSaleModel) -> POSSale:
        pm_map = {'efectivo': 'cash', 'tarjeta': 'card', 'transferencia': 'transfer'}
        payment_method = pm_map.get(m.payment_method, 'cash')
        
        st_map = {'pendiente': 'pending', 'completada': 'completed', 'canceled': 'cancelled'}
        status = st_map.get(m.status, 'pending')

        items = [
            POSSaleItem(
                product_id=i.product_id,
                code=i.code,
                description=i.description,
                quantity=i.quantity,
                unit_price=i.unit_price,
                discount=i.discount
            )
            for i in m.items.all()
        ]
        
        customer = POSCustomer(
            name=m.customer_name,
            identifier=m.customer_identifier,
            id_type=m.customer_id_type,
            address="",
            email="",
            payment_form="01"
        )
        
        return POSSale(
            id=m.id,
            tenant_id=m.tenant_id,
            register_id=m.register_id,
            user_id=m.user_id,
            seller_id=getattr(m, 'seller_id', None),
            customer=customer,
            items=items,
            document_type=getattr(m, 'document_type', '01'),
            payment_method=payment_method,
            amount_received=m.amount_received,
            vat_rate=m.vat_rate,
            status=status,
            created_at=m.created_at,
            invoice_id=m.invoice_id,
            reference_number=m.reference_number
        )

    def save(self, sale: POSSale) -> POSSale:
        pm_map = {'cash': 'efectivo', 'card': 'tarjeta', 'transfer': 'transferencia'}
        mapped_pm = pm_map.get(sale.payment_method, 'efectivo')
        
        st_map = {'pending': 'pendiente', 'completed': 'completada', 'cancelled': 'canceled'}
        mapped_status = st_map.get(sale.status, 'pendiente')

        if sale.id:
            m = POSSaleModel.objects.get(id=sale.id)
            m.status = mapped_status
            m.invoice_id = sale.invoice_id
            m.reference_number = sale.reference_number
            m.save()
        else:
            m = POSSaleModel.objects.create(
                tenant_id=sale.tenant_id,
                register_id=sale.register_id,
                user_id=sale.user_id,
                seller_id=sale.seller_id,
                payment_method=mapped_pm,
                amount_received=sale.amount_received,
                vat_rate=sale.vat_rate,
                status=mapped_status,
                created_at=sale.created_at,
                customer_name=sale.customer.name,
                customer_identifier=sale.customer.identifier,
                customer_id_type=sale.customer.id_type,
                invoice_id=sale.invoice_id,
                reference_number=sale.reference_number
            )
            
            for item in sale.items:
                POSSaleItemModel.objects.create(
                    sale=m,
                    product_id=item.product_id,
                    code=item.code,
                    description=item.description,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    discount=item.discount
                )
        return self._to_entity(m)

    def get_by_id(self, sale_id: int, tenant_id: int) -> Optional[POSSale]:
        try:
            return self._to_entity(POSSaleModel.objects.get(id=sale_id, tenant_id=tenant_id))
        except POSSaleModel.DoesNotExist:
            return None

    def list_by_register(self, register_id: int, tenant_id: int) -> List[POSSale]:
        records = POSSaleModel.objects.filter(
            register_id=register_id,
            tenant_id=tenant_id,
            status='completada'
        ).prefetch_related('items')
        return [self._to_entity(r) for r in records]

    def get_sales_totals_by_register(self, register_id: int) -> dict:
        sales = POSSaleModel.objects.filter(register_id=register_id, status='completada')
        count = sales.count()
        total = Decimal('0.00')
        for s in sales:
            for item in s.items.all():
                base = item.quantity * item.unit_price
                subtotal = base - (base * item.discount / 100)
                total += subtotal
        total = (total * Decimal('1.12')).quantize(Decimal('0.01'))
        return {'total': total, 'count': count}


