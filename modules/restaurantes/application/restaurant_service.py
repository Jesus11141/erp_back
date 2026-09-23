from typing import List, Optional
from decimal import Decimal
from ..domain.entities import RestaurantZone, RestaurantTable, RestaurantOrder, RestaurantOrderLine
from ..domain.repositories import RestaurantRepository
from ..domain.value_objects import TableStatus, OrderStatus, KitchenStatus

class RestaurantService:
    def __init__(self, repo: RestaurantRepository):
        self._repo = repo
        
    def get_full_map(self, tenant_id: int) -> List[dict]:
        zones = self._repo.get_zones(tenant_id)
        result = []
        for zone in zones:
            tables = self._repo.get_tables_by_zone(tenant_id, zone.id)
            result.append({
                'id': str(zone.id),
                'nombre': zone.name,
                'mesas': [{
                    'id': str(m.id),
                    'nombre': m.name,
                    'asientos': m.seats,
                    'estado': m.status.value
                } for m in tables]
            })
        return result
        
    def create_zone(self, tenant_id: int, name: str) -> dict:
        zone = self._repo.create_zone(tenant_id, name)
        return {'id': str(zone.id), 'nombre': zone.name}
        
    def create_table(self, tenant_id: int, zone_id: int, name: str, seats: int) -> dict:
        table = self._repo.create_table(tenant_id, zone_id, name, seats)
        return {
            'id': str(table.id),
            'zona_id': str(table.zone_id),
            'nombre': table.name,
            'asientos': table.seats,
            'estado': table.status.value
        }
        
    def get_open_orders_by_table(self, tenant_id: int, table_id: Optional[int] = None) -> List[dict]:
        orders = []
        if table_id:
            order = self._repo.get_open_order_for_table(tenant_id, table_id)
            if order:
                orders.append(order)
        else:
            # We would need a get_all_open_orders in repo, let's just implement what's used
            pass 
            
        result = []
        for p in orders:
            result.append({
                'id': str(p.id),
                'mesa_id': str(p.table_id),
                'estado': p.status.value,
                'total': float(p.total),
                'creado_en': p.created_at,
                'lineas': [{
                    'id': str(l.id),
                    'item_nombre': l.item_name,
                    'cantidad': l.quantity,
                    'precio_unitario': float(l.unit_price),
                    'notas': l.notes,
                    'estado_cocina': l.kitchen_status.value
                } for l in p.lines]
            })
        return result

    def open_or_update_order(self, tenant_id: int, table_id: int, lines_data: List[dict]) -> dict:
        order = self._repo.get_open_order_for_table(tenant_id, table_id)
        if not order:
            order = self._repo.create_order(tenant_id, table_id)
            self._repo.update_table_status(tenant_id, table_id, TableStatus.OCCUPIED)
            
        total_agregado = Decimal('0.00')
        for l in lines_data:
            precio = float(l.get('precio_unitario', 0))
            cant = int(l.get('cantidad', 1))
            self._repo.add_line_to_order(
                tenant_id,
                order.id,
                item_id=str(l.get('item_id', '')),
                item_name=l.get('item_nombre', 'Producto'),
                quantity=cant,
                unit_price=precio,
                notes=l.get('notas', '')
            )
            total_agregado += Decimal(str(precio * cant))
            
        new_total = order.total + total_agregado
        self._repo.update_order_total(tenant_id, order.id, float(new_total))
        
        return {'id': str(order.id), 'total': float(new_total)}

    def close_order(self, tenant_id: int, order_id: int, table_id: int) -> dict:
        self._repo.close_order(tenant_id, order_id)
        
        # Release table if no more open orders
        open_order = self._repo.get_open_order_for_table(tenant_id, table_id)
        if not open_order:
            self._repo.update_table_status(tenant_id, table_id, TableStatus.FREE)
            
        return {'status': 'cerrado'}

    def get_kitchen_dashboard(self, tenant_id: int) -> List[dict]:
        lines = self._repo.get_kitchen_lines(tenant_id)
        from datetime import datetime
        now = datetime.now()
        
        result = []
        for l in lines:
            seconds_wait = (now - l.sent_to_kitchen_at).total_seconds() if l.sent_to_kitchen_at else 0
            result.append({
                'id': str(l.id),
                'pedido_id': str(l.order_id),
                'mesa_nombre': l.table_name or '',
                'item_nombre': l.item_name,
                'cantidad': l.quantity,
                'notas': l.notes,
                'estado_cocina': l.kitchen_status.value,
                'tiempo_espera': seconds_wait
            })
        return result
        
    def update_kitchen_line(self, tenant_id: int, line_id: int, status_str: str) -> dict:
        try:
            status = KitchenStatus(status_str)
            self._repo.update_kitchen_line_status(tenant_id, line_id, status)
            return {'status': 'ok'}
        except ValueError:
            raise ValueError(f"Invalid kitchen status: {status_str}")
