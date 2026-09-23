from typing import Optional, List
from decimal import Decimal
from ..domain.entities import Product, StockMovement
from ..domain.repositories import (
    ProductRepository, StockMovementRepository, VolumeDiscountRuleRepository,
    KardexRepository, BranchStockRepository, StockTransferRepository
)
from .django_models import (
    ProductModel, StockMovementModel, VolumeDiscountRuleModel,
    KardexModel, BranchStockModel, StockTransferModel, BranchModel
)

class DjangoProductRepository(ProductRepository):
    def _to_entity(self, m: ProductModel) -> Product:
        return Product(
            id=m.id,
            tenant_id=m.tenant_id,
            code=m.code,
            name=m.name,
            description=m.description,
            category=m.category or '',
            purchase_price=m.purchase_price,
            sale_price=m.sale_price,
            current_stock=m.current_stock,
            minimum_stock=m.minimum_stock,
            unit=m.unit,
            vat_rate=m.vat_rate,
            active=m.active,
            is_composite=getattr(m, 'is_composite', False),
            image=(m.image.url if m.image else None),
        )

    def save(self, p: Product) -> Product:
        data = {
            'name': p.name,
            'description': p.description,
            'category': p.category or '',
            'purchase_price': p.purchase_price,
            'sale_price': p.sale_price,
            'current_stock': p.current_stock,
            'minimum_stock': p.minimum_stock,
            'unit': p.unit,
            'vat_rate': p.vat_rate,
            'active': p.active,
            'is_composite': p.is_composite
        }
        if p.id:
            m = ProductModel.objects.get(id=p.id)
            for k, v in data.items():
                setattr(m, k, v)
            if hasattr(p, 'image') and p.image is not None:
                if not isinstance(p.image, str):
                    m.image = p.image
            m.save()
        else:
            m = ProductModel.objects.create(
                tenant_id=p.tenant_id,
                code=p.code,
                image=p.image,
                **data
            )
        return self._to_entity(m)

    def find_by_id(self, id: int, tenant_id: int) -> Optional[Product]:
        try:
            return self._to_entity(ProductModel.objects.get(id=id, tenant_id=tenant_id))
        except ProductModel.DoesNotExist:
            return None

    def find_by_code(self, code: str, tenant_id: int) -> Optional[Product]:
        try:
            return self._to_entity(ProductModel.objects.get(code=code, tenant_id=tenant_id))
        except ProductModel.DoesNotExist:
            return None

    def list_by_tenant(self, tenant_id: int) -> List[Product]:
        return [self._to_entity(m) for m in ProductModel.objects.filter(tenant_id=tenant_id, active=True)]

    def list_low_stock(self, tenant_id: int) -> List[Product]:
        from django.db.models import F
        qs = ProductModel.objects.filter(tenant_id=tenant_id, active=True).filter(current_stock__lte=F('minimum_stock'))
        return [self._to_entity(m) for m in qs]

    def search(self, query: str, tenant_id: int) -> List[Product]:
        qs = ProductModel.objects.filter(tenant_id=tenant_id, active=True).filter(
            name__icontains=query) | ProductModel.objects.filter(tenant_id=tenant_id, active=True).filter(code__icontains=query)
        return [self._to_entity(m) for m in qs.distinct()]


class DjangoStockMovementRepository(StockMovementRepository):
    def register(self, m: StockMovement) -> StockMovement:
        record = StockMovementModel.objects.create(
            tenant_id=m.tenant_id,
            product_id=m.product_id,
            product_name=m.product_name,
            type=m.type,
            quantity=m.quantity,
            previous_stock=m.previous_stock,
            new_stock=m.new_stock,
            reference=m.reference,
            user_id=m.user_id
        )
        m.id = record.id
        return m

    def list_by_product(self, product_id: int, tenant_id: int) -> List[StockMovement]:
        return [StockMovement(
            id=m.id,
            tenant_id=m.tenant_id,
            product_id=m.product_id,
            product_name=m.product_name,
            type=m.type,
            quantity=m.quantity,
            previous_stock=m.previous_stock,
            new_stock=m.new_stock,
            reference=m.reference,
            created_at=m.created_at,
            user_id=m.user_id,
        ) for m in StockMovementModel.objects.filter(product_id=product_id, tenant_id=tenant_id)]


class DjangoVolumeDiscountRuleRepository(VolumeDiscountRuleRepository):
    def list_product_tiers(self, tenant_id: int, product_id: int) -> List[dict]:
        rules = VolumeDiscountRuleModel.objects.filter(
            tenant_id=tenant_id,
            product_id=product_id,
            active=True
        ).order_by('minimum_quantity')
        return [
            {
                'id': r.id,
                'minimum_quantity': str(r.minimum_quantity),
                'maximum_quantity': str(r.maximum_quantity) if r.maximum_quantity is not None else None,
                'unit_price': str(r.unit_price),
                'discount_percentage': str(r.discount_percentage),
                'active': r.active
            }
            for r in rules
        ]

    def find_applicable_rule(self, tenant_id: int, product_id: int, quantity: float) -> Optional[dict]:
        rules = VolumeDiscountRuleModel.objects.filter(
            tenant_id=tenant_id,
            product_id=product_id,
            active=True,
            minimum_quantity__lte=quantity
        ).order_by('-minimum_quantity')
        for rule in rules:
            if rule.maximum_quantity is None or quantity <= rule.maximum_quantity:
                return {
                    'id': rule.id,
                    'minimum_quantity': str(rule.minimum_quantity),
                    'maximum_quantity': str(rule.maximum_quantity) if rule.maximum_quantity is not None else None,
                    'unit_price': rule.unit_price,
                    'discount_percentage': rule.discount_percentage,
                }
        return None


class DjangoKardexRepository(KardexRepository):
    def register(self, tenant_id: int, product_id: int, type: str, quantity: Decimal,
                 unit_cost: Decimal = None, reference: str = '', user_id: int = 0) -> dict:
        from django.db import transaction
        with transaction.atomic():
            try:
                prod = ProductModel.objects.get(id=product_id, tenant_id=tenant_id)
            except ProductModel.DoesNotExist:
                raise ValueError("Producto no encontrado")

            last_k = KardexModel.objects.filter(tenant_id=tenant_id, product_id=product_id).order_by('-created_at', '-id').first()
            
            balance_qty = last_k.balance_quantity if last_k else Decimal('0.0000')
            balance_unit_c = last_k.balance_unit_cost if last_k else prod.purchase_price
            balance_total_c = last_k.balance_total_cost if last_k else (balance_qty * balance_unit_c)

            entry_quantity = Decimal('0.0000')
            entry_unit_cost = Decimal('0.0000')
            entry_total_cost = Decimal('0.0000')

            exit_quantity = Decimal('0.0000')
            exit_unit_cost = Decimal('0.0000')
            exit_total_cost = Decimal('0.0000')

            new_balance_qty = Decimal('0.0000')
            new_balance_unit_c = Decimal('0.0000')
            new_balance_total_c = Decimal('0.0000')

            if type == 'in':
                c_unit = unit_cost if unit_cost is not None else balance_unit_c
                entry_quantity = quantity
                entry_unit_cost = c_unit
                entry_total_cost = (quantity * c_unit).quantize(Decimal('0.0001'))

                new_balance_qty = balance_qty + quantity
                new_balance_total_c = balance_total_c + entry_total_cost
                if new_balance_qty > 0:
                    new_balance_unit_c = (new_balance_total_c / new_balance_qty).quantize(Decimal('0.0001'))
                else:
                    new_balance_unit_c = Decimal('0.0000')

            elif type == 'out':
                c_unit = balance_unit_c
                exit_quantity = quantity
                exit_unit_cost = c_unit
                exit_total_cost = (quantity * c_unit).quantize(Decimal('0.0001'))

                new_balance_qty = balance_qty - quantity
                new_balance_total_c = balance_total_c - exit_total_cost
                new_balance_unit_c = c_unit

            elif type == 'adjustment':
                target_quantity = quantity
                if target_quantity >= balance_qty:
                    diff = target_quantity - balance_qty
                    c_unit = unit_cost if unit_cost is not None else balance_unit_c
                    entry_quantity = diff
                    entry_unit_cost = c_unit
                    entry_total_cost = (diff * c_unit).quantize(Decimal('0.0001'))

                    new_balance_qty = target_quantity
                    new_balance_total_c = balance_total_c + entry_total_cost
                    if new_balance_qty > 0:
                        new_balance_unit_c = (new_balance_total_c / new_balance_qty).quantize(Decimal('0.0001'))
                    else:
                        new_balance_unit_c = Decimal('0.0000')
                else:
                    diff = balance_qty - target_quantity
                    c_unit = balance_unit_c
                    exit_quantity = diff
                    exit_unit_cost = c_unit
                    exit_total_cost = (diff * c_unit).quantize(Decimal('0.0001'))

                    new_balance_qty = target_quantity
                    new_balance_total_c = balance_total_c - exit_total_cost
                    new_balance_unit_c = c_unit

            k_entry = KardexModel.objects.create(
                tenant_id=tenant_id,
                product_id=product_id,
                detail=reference,
                entry_quantity=entry_quantity,
                entry_unit_cost=entry_unit_cost,
                entry_total_cost=entry_total_cost,
                exit_quantity=exit_quantity,
                exit_unit_cost=exit_unit_cost,
                exit_total_cost=exit_total_cost,
                balance_quantity=new_balance_qty,
                balance_unit_cost=new_balance_unit_c,
                balance_total_cost=new_balance_total_c,
                user_id=user_id
            )

            prod.purchase_price = new_balance_unit_c
            prod.current_stock = new_balance_qty
            prod.save()

            return {
                'id': k_entry.id,
                'product_id': k_entry.product_id,
                'balance_quantity': str(k_entry.balance_quantity),
                'balance_unit_cost': str(k_entry.balance_unit_cost),
                'balance_total_cost': str(k_entry.balance_total_cost)
            }


class DjangoBranchStockRepository(BranchStockRepository):
    def adjust_branch_stock(self, tenant_id: int, product_id: int, branch_id: int,
                            quantity: Decimal, type: str, allow_negative: bool = False) -> Decimal:
        try:
            prod_model = ProductModel.objects.get(id=product_id, tenant_id=tenant_id)
        except ProductModel.DoesNotExist:
            raise ValueError("Producto no encontrado")

        stock_suc, _ = BranchStockModel.objects.get_or_create(
            tenant_id=tenant_id,
            product_id=product_id,
            branch_id=branch_id,
            defaults={'current_stock': Decimal('0')}
        )

        if type == 'out':
            if stock_suc.current_stock < quantity and not allow_negative:
                raise ValueError(f"Stock insuficiente en la sucursal. Disponible: {stock_suc.current_stock}")
            stock_suc.current_stock -= quantity
        elif type == 'in':
            stock_suc.current_stock += quantity
        elif type == 'adjustment':
            stock_suc.current_stock = quantity

        stock_suc.save()

        from django.db.models import Sum
        total_stock = BranchStockModel.objects.filter(
            tenant_id=tenant_id, product_id=product_id
        ).aggregate(total=Sum('current_stock'))['total'] or Decimal('0')
        prod_model.current_stock = total_stock
        prod_model.save()

        return stock_suc.current_stock

    def get_stock(self, tenant_id: int, product_id: int, branch_id: int) -> Decimal:
        try:
            stock_suc = BranchStockModel.objects.get(
                tenant_id=tenant_id,
                product_id=product_id,
                branch_id=branch_id
            )
            return stock_suc.current_stock
        except BranchStockModel.DoesNotExist:
            return Decimal('0.00')


class DjangoStockTransferRepository(StockTransferRepository):
    def transfer_stock(self, tenant_id: int, product_id: int, source_branch_id: int,
                        destination_branch_id: int, quantity: Decimal, user_id: int,
                        observations: str = '') -> dict:
        from django.db import transaction
        with transaction.atomic():
            try:
                prod = ProductModel.objects.get(id=product_id, tenant_id=tenant_id)
            except ProductModel.DoesNotExist:
                raise ValueError("Producto no encontrado")

            try:
                suc_origen = BranchModel.objects.get(id=source_branch_id, tenant_id=tenant_id)
                suc_destino = BranchModel.objects.get(id=destination_branch_id, tenant_id=tenant_id)
            except BranchModel.DoesNotExist:
                raise ValueError("Una o ambas sucursales no existen")

            stock_orig, _ = BranchStockModel.objects.get_or_create(
                tenant_id=tenant_id,
                product=prod,
                branch=suc_origen,
                defaults={'current_stock': Decimal('0')}
            )

            if stock_orig.current_stock < quantity:
                raise ValueError(f"Stock insuficiente en la sucursal de origen '{suc_origen.name}'. Disponible: {stock_orig.current_stock}")

            stock_dest, _ = BranchStockModel.objects.get_or_create(
                tenant_id=tenant_id,
                product=prod,
                branch=suc_destino,
                defaults={'current_stock': Decimal('0')}
            )

            stock_orig.current_stock -= quantity
            stock_orig.save()

            stock_dest.current_stock += quantity
            stock_dest.save()

            trans = StockTransferModel.objects.create(
                tenant_id=tenant_id,
                product=prod,
                source_branch=suc_origen,
                destination_branch=suc_destino,
                quantity=quantity,
                user_id=user_id,
                observations=observations,
                status='completed'
            )

            return trans

