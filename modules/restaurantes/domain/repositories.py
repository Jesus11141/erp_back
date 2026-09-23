from abc import ABC, abstractmethod
from typing import List, Optional
from .entities import RestaurantZone, RestaurantTable, RestaurantOrder, RestaurantOrderLine
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
    def close_order(self, tenant_id: int, order_id: int) -> None:
        pass
        
    @abstractmethod
    def get_kitchen_lines(self, tenant_id: int) -> List[RestaurantOrderLine]:
        pass
        
    @abstractmethod
    def update_kitchen_line_status(self, tenant_id: int, line_id: int, status: KitchenStatus) -> None:
        pass
