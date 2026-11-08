from decimal import Decimal
from datetime import datetime
from ..domain.entities import Product, StockMovement
from ..domain.repositories import ProductRepository, StockMovementRepository, BranchStockRepository, KardexRepository


class AdjustStock:
    def __init__(self, product_repo: ProductRepository, movement_repo: StockMovementRepository, kardex_repo: KardexRepository = None):
        self.product_repo = product_repo
        self.movement_repo = movement_repo
        self.kardex_repo = kardex_repo

    def execute(self, tenant_id: int, product_id: int, quantity: Decimal,
                 type: str, reference: str, user_id: int) -> Product:
        product = self.product_repo.find_by_id(product_id, tenant_id)
        if not product:
            raise ValueError("Producto no encontrado")
            
        # Feature Toggle Check for Composite Products
        try:
            from modules.tenants.infrastructure.django_models import TenantFeatureToggleModel
            is_composite_enabled = TenantFeatureToggleModel.objects.filter(
                tenant_id=tenant_id, feature_key='inventario_composite_products', is_enabled=True
            ).exists()
        except ImportError:
            is_composite_enabled = False

        is_dish = getattr(product, 'product_type', 'goods') == 'dish'

        if (is_composite_enabled or is_dish) and product.is_composite and type in ('out', 'salida'):
            # Composite product logic: explode into components
            from ..infrastructure.django_models import ProductComponentModel
            components = ProductComponentModel.objects.filter(tenant_id=tenant_id, product_id=product_id)
            if components.exists():
                for comp in components:
                    comp_qty = comp.quantity * quantity
                    # Directly execute to decrement component stock
                    self.execute(
                        tenant_id=tenant_id,
                        product_id=comp.component_id,
                        quantity=comp_qty,
                        type=type,
                        reference=f"{reference} (Kit: {product.name})",
                        user_id=user_id
                    )
                # Return the main product without adjusting its stock
                return product
            if is_dish:
                # Dish without a recipe: nothing to deduct, never touch the dish's own stock
                return product

        previous_stock = product.current_stock
        
        if self.kardex_repo:
            from .kardex_service import RegisterKardexWAC
            RegisterKardexWAC(self.kardex_repo).execute(
                tenant_id=tenant_id,
                product_id=product_id,
                type=type,
                quantity=quantity,
                unit_cost=None,
                reference=reference,
                user_id=user_id,
            )
        else:
            if type in ('in', 'entrada'):
                product.current_stock += quantity
            elif type in ('out', 'salida'):
                product.current_stock -= quantity
            elif type in ('adjustment', 'ajuste'):
                product.current_stock = quantity
            self.product_repo.save(product)

        # Reload product to get updated stock after Kardex computation
        product = self.product_repo.find_by_id(product_id, tenant_id)
        if self.movement_repo:
            self.movement_repo.register(StockMovement(
                id=0,
                tenant_id=tenant_id,
                product_id=product_id,
                product_name=product.name,
                type=type,
                quantity=quantity,
                previous_stock=previous_stock,
                new_stock=product.current_stock,
                reference=reference,
                created_at=datetime.now(),
                user_id=user_id,
            ))
        return product




