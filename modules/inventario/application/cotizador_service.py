from decimal import Decimal
from typing import Tuple, Optional, List
from ..domain.repositories import ProductRepository, VolumeDiscountRuleRepository

class QuotationService:
    def __init__(self, product_repo: ProductRepository, rule_repo: VolumeDiscountRuleRepository):
        self.product_repo = product_repo
        self.rule_repo = rule_repo

    def resolve_unit_price(self, tenant_id: int, product_id: int, quantity: Decimal) -> Tuple[Decimal, Optional[dict]]:
        product = self.product_repo.find_by_id(product_id, tenant_id)
        if not product:
            raise ValueError("Producto no encontrado")

        base_price = product.sale_price
        rule = self.rule_repo.find_applicable_rule(tenant_id, product_id, float(quantity))

        if not rule:
            return base_price, None

        if rule.get('unit_price') is not None:
            return Decimal(str(rule['unit_price'])), rule
        elif rule.get('discount_percentage') is not None:
            pct = Decimal(str(rule['discount_percentage']))
            discount = (base_price * (pct / Decimal('100'))).quantize(Decimal('0.01'))
            return (base_price - discount), rule

        return base_price, None

    def get_product_tiers(self, tenant_id: int, product_id: int) -> List[dict]:
        return self.rule_repo.list_product_tiers(tenant_id, product_id)

    def calculate_quotation(self, tenant_id: int, product_id: int, quantity: Decimal) -> dict:
        if quantity <= 0:
            raise ValueError("La cantidad debe ser mayor a cero")

        product = self.product_repo.find_by_id(product_id, tenant_id)
        if not product:
            raise ValueError("Producto no encontrado")

        base_price = product.sale_price
        base_subtotal = (base_price * quantity).quantize(Decimal('0.01'))

        applied_price, rule = self.resolve_unit_price(tenant_id, product_id, quantity)
        applied_subtotal = (applied_price * quantity).quantize(Decimal('0.01'))

        savings = (base_subtotal - applied_subtotal).quantize(Decimal('0.01'))

        savings_percentage = Decimal('0.00')
        if base_subtotal > 0:
            savings_percentage = ((savings / base_subtotal) * Decimal('100')).quantize(Decimal('0.01'))

        return {
            'product_id': product.id,
            'product_code': product.code,
            'product_name': product.name,
            'quantity': str(quantity),
            'base_unit_price': str(base_price),
            'base_subtotal': str(base_subtotal),
            'applied_unit_price': str(applied_price),
            'subtotal': str(applied_subtotal),
            'total_savings': str(savings),
            'savings_percentage': str(savings_percentage),
            'applied_rule': rule
        }
