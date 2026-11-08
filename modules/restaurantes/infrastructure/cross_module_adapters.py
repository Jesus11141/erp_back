from decimal import Decimal
from typing import Dict, List

from django.db import transaction
from django.db.models import Count

from ..domain.entities import RecipeIngredient
from ..domain.repositories import RestaurantInventoryService


class DjangoRestaurantInventoryService(RestaurantInventoryService):
    """Adapter between restaurant dishes and the inventory module.

    The recipe (escandallo) is stored in inventory as the components of a hidden
    composite product of type 'dish' (ProductModel / ProductComponentModel).
    """

    def get_products_info(self, tenant_id: int, product_ids: List[int]) -> Dict[int, dict]:
        from modules.inventario.infrastructure.django_models import ProductModel
        products = ProductModel.objects.filter(tenant_id=tenant_id, id__in=product_ids).exclude(product_type='dish')
        return {
            p.id: {
                'name': p.name,
                'code': p.code,
                'unit': p.unit,
                'unit_cost': p.purchase_price,
                'current_stock': p.current_stock,
            }
            for p in products
        }

    def ensure_dish_product(self, tenant_id: int, dish_id: str, name: str, price: Decimal) -> int:
        from modules.inventario.infrastructure.django_models import ProductModel
        code = f"DISH-{str(dish_id).replace('-', '')[:12].upper()}"
        product, _ = ProductModel.objects.get_or_create(
            tenant_id=tenant_id, code=code,
            defaults={
                'name': name,
                'sale_price': price,
                'unit': 'und',
                'is_composite': True,
                'product_type': 'dish',
            },
        )
        return product.id

    def get_recipe(self, tenant_id: int, product_id: int) -> List[RecipeIngredient]:
        from modules.inventario.infrastructure.django_models import ProductComponentModel
        rows = ProductComponentModel.objects.filter(tenant_id=tenant_id, product_id=product_id).order_by('id')
        return [RecipeIngredient(product_id=r.component_id, quantity=r.quantity) for r in rows]

    def replace_recipe(self, tenant_id: int, product_id: int, ingredients: List[RecipeIngredient]) -> None:
        from modules.inventario.infrastructure.django_models import ProductComponentModel
        with transaction.atomic():
            ProductComponentModel.objects.filter(tenant_id=tenant_id, product_id=product_id).delete()
            ProductComponentModel.objects.bulk_create([
                ProductComponentModel(
                    tenant_id=tenant_id, product_id=product_id,
                    component_id=i.product_id, quantity=i.quantity,
                )
                for i in ingredients
            ])

    def get_recipe_counts(self, tenant_id: int, product_ids: List[int]) -> Dict[int, int]:
        from modules.inventario.infrastructure.django_models import ProductComponentModel
        rows = (ProductComponentModel.objects
                .filter(tenant_id=tenant_id, product_id__in=product_ids)
                .values('product_id').annotate(total=Count('id')))
        return {r['product_id']: r['total'] for r in rows}

    def consume_dish(self, tenant_id: int, product_id: int, quantity: Decimal, reference: str, user_id: int = 0) -> None:
        from modules.inventario.infrastructure.repository_impl import DjangoProductRepository, DjangoStockMovementRepository
        from modules.inventario.application.use_cases import AdjustStock
        # AdjustStock explodes 'dish' composites into their recipe components.
        AdjustStock(DjangoProductRepository(), DjangoStockMovementRepository()).execute(
            tenant_id=tenant_id,
            product_id=product_id,
            quantity=quantity,
            type='out',
            reference=reference,
            user_id=user_id,
        )

    def delete_dish_product(self, tenant_id: int, product_id: int) -> None:
        from modules.inventario.infrastructure.django_models import ProductModel
        # Components cascade; dish products are never components of other products.
        ProductModel.objects.filter(tenant_id=tenant_id, id=product_id, product_type='dish').delete()
