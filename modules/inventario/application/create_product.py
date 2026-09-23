from decimal import Decimal
from datetime import datetime
from ..domain.entities import Product, StockMovement
from ..domain.repositories import ProductRepository, StockMovementRepository, BranchStockRepository, KardexRepository


class CreateProduct:
    def __init__(self, repo: ProductRepository, kardex_repo: KardexRepository = None):
        self.repo = repo
        self.kardex_repo = kardex_repo

    def execute(self, tenant_id: int, data: dict) -> Product:
        existing = self.repo.find_by_code(data['code'], tenant_id)
        if existing:
            raise ValueError(f"Ya existe un producto con el cÃ³digo {data['code']}")
        
        product = Product(
            id=0,
            tenant_id=tenant_id,
            code=data['code'],
            name=data['name'],
            description=data.get('description', ''),
            category=data.get('category', ''),
            purchase_price=Decimal(str(data.get('purchase_price', 0))),
            sale_price=Decimal(str(data['sale_price'])),
            current_stock=Decimal(str(data.get('initial_stock', 0))),
            minimum_stock=Decimal(str(data.get('minimum_stock', 0))),
            unit=data.get('unit', 'pza'),
            vat_rate=data.get('vat_rate', '15'),
            image=data.get('image', None),
        )
        prod = self.repo.save(product)
        
        if prod.current_stock > 0 and self.kardex_repo:
            from .kardex_service import RegisterKardexWAC
            RegisterKardexWAC(self.kardex_repo).execute(
                tenant_id=tenant_id,
                product_id=prod.id,
                type='in',
                quantity=prod.current_stock,
                unit_cost=prod.purchase_price,
                reference='Inventario Inicial',
                user_id=0,
            )
        return prod




