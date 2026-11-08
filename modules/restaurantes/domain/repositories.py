from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Dict, List, Optional
from .entities import RestaurantZone, RestaurantTable, RestaurantOrder, RestaurantOrderLine, RecipeIngredient
from .value_objects import KitchenStatus, TableStatus

class RestaurantRepository(ABC):
    
    @abstractmethod
    def get_zones(self, tenant_id: int) -> List[RestaurantZone]:
        pass
        
    @abstractmethod
    def get_tables_by_zone(self, tenant_id: int, zone_id: int) -> List[RestaurantTable]:
        pass
        
    @abstractmethod
    def get_table_by_id(self, tenant_id: int, table_id: int) -> Optional[RestaurantTable]:
        pass
        
    @abstractmethod
    def create_zone(self, tenant_id: int, name: str) -> RestaurantZone:
        pass
        
    @abstractmethod
    def create_table(self, tenant_id: int, zone_id: int, name: str, seats: int) -> RestaurantTable:
        pass
        
    @abstractmethod
    def update_table_status(self, tenant_id: int, table_id: int, status: TableStatus) -> None:
        pass

    @abstractmethod
    def get_open_order_for_table(self, tenant_id: int, table_id: int) -> Optional[RestaurantOrder]:
        pass
        
    @abstractmethod
    def create_order(self, tenant_id: int, table_id: int) -> RestaurantOrder:
        pass
        
    @abstractmethod
    def add_line_to_order(self, tenant_id: int, order_id: int, item_id: str, item_name: str, quantity: int, unit_price: float, notes: str) -> RestaurantOrderLine:
        pass
        
    @abstractmethod
    def update_order_total(self, tenant_id: int, order_id: int, total: float) -> None:
        pass
        
    @abstractmethod
    def get_order_by_id(self, tenant_id: int, order_id: int) -> Optional[RestaurantOrder]:
        pass

    @abstractmethod
    def close_order(self, tenant_id: int, order_id: int, billing_info: Optional[dict] = None) -> None:
        pass
        
    @abstractmethod
    def get_kitchen_lines(self, tenant_id: int) -> List[RestaurantOrderLine]:
        pass
        
    @abstractmethod
    def update_kitchen_line_status(self, tenant_id: int, line_id: int, status: KitchenStatus) -> None:
        pass

    @abstractmethod
    def dish_exists(self, tenant_id: int, dish_id: str) -> bool:
        pass

    @abstractmethod
    def get_dish_summary(self, tenant_id: int, dish_id: str) -> Optional[dict]:
        """Returns {'name', 'price', 'product_id'} for the dish or None when it does not exist."""
        pass

    @abstractmethod
    def set_dish_product_id(self, tenant_id: int, dish_id: str, product_id: Optional[int]) -> None:
        pass

    @abstractmethod
    def get_dish_product_map(self, tenant_id: int) -> Dict[str, int]:
        """Maps dish id -> linked inventory product id (only dishes that have a recipe holder)."""
        pass


class RestaurantInventoryService(ABC):
    """Port to the inventory module. Recipes live in inventory (single source of truth)."""

    @abstractmethod
    def get_products_info(self, tenant_id: int, product_ids: List[int]) -> Dict[int, dict]:
        """Info of sellable/stockable goods (dish holder products are excluded)."""
        pass

    @abstractmethod
    def ensure_dish_product(self, tenant_id: int, dish_id: str, name: str, price: Decimal) -> int:
        """Creates (if needed) the hidden composite product that holds the dish recipe."""
        pass

    @abstractmethod
    def get_recipe(self, tenant_id: int, product_id: int) -> List[RecipeIngredient]:
        pass

    @abstractmethod
    def replace_recipe(self, tenant_id: int, product_id: int, ingredients: List[RecipeIngredient]) -> None:
        pass

    @abstractmethod
    def get_recipe_counts(self, tenant_id: int, product_ids: List[int]) -> Dict[int, int]:
        pass

    @abstractmethod
    def consume_dish(self, tenant_id: int, product_id: int, quantity: Decimal, reference: str, user_id: int = 0) -> None:
        pass

    @abstractmethod
    def delete_dish_product(self, tenant_id: int, product_id: int) -> None:
        pass
