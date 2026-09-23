from typing import List, Optional
from ..domain.entities import RestaurantZone, RestaurantTable, RestaurantOrder, RestaurantOrderLine
from ..domain.repositories import RestaurantRepository
from ..domain.value_objects import TableStatus, OrderStatus, KitchenStatus
from .django_models import ZonaModel, MesaModel, PedidoRestauranteModel, LineaPedidoRestauranteModel

class DjangoRestaurantRepository(RestaurantRepository):

    def get_zones(self, tenant_id: int) -> List[RestaurantZone]:
        records = ZonaModel.objects.filter(tenant_id=tenant_id)
        return [RestaurantZone(id=r.id, tenant_id=r.tenant_id, name=r.nombre) for r in records]

    def get_tables_by_zone(self, tenant_id: int, zone_id: int) -> List[RestaurantTable]:
        records = MesaModel.objects.filter(tenant_id=tenant_id, zona_id=zone_id)
        return [RestaurantTable(id=r.id, tenant_id=r.tenant_id, zone_id=r.zona_id, name=r.nombre, seats=r.asientos, status=TableStatus(r.estado)) for r in records]

    def get_table_by_id(self, tenant_id: int, table_id: int) -> Optional[RestaurantTable]:
        try:
            r = MesaModel.objects.get(tenant_id=tenant_id, id=table_id)
            return RestaurantTable(id=r.id, tenant_id=r.tenant_id, zone_id=r.zona_id, name=r.nombre, seats=r.asientos, status=TableStatus(r.estado))
        except MesaModel.DoesNotExist:
            return None

    def create_zone(self, tenant_id: int, name: str) -> RestaurantZone:
        r = ZonaModel.objects.create(tenant_id=tenant_id, nombre=name)
        return RestaurantZone(id=r.id, tenant_id=r.tenant_id, name=r.nombre)

    def create_table(self, tenant_id: int, zone_id: int, name: str, seats: int) -> RestaurantTable:
        r = MesaModel.objects.create(tenant_id=tenant_id, zona_id=zone_id, nombre=name, asientos=seats)
        return RestaurantTable(id=r.id, tenant_id=r.tenant_id, zone_id=r.zona_id, name=r.nombre, seats=r.asientos, status=TableStatus(r.estado))

    def update_table_status(self, tenant_id: int, table_id: int, status: TableStatus) -> None:
        MesaModel.objects.filter(tenant_id=tenant_id, id=table_id).update(estado=status.value)

    def get_open_order_for_table(self, tenant_id: int, table_id: int) -> Optional[RestaurantOrder]:
        try:
            r = PedidoRestauranteModel.objects.prefetch_related('lineas').get(tenant_id=tenant_id, mesa_id=table_id, estado=OrderStatus.OPEN.value)
            lines = [RestaurantOrderLine(
                id=l.id, 
                item_id=l.item_id, 
                item_name=l.item_nombre, 
                quantity=l.cantidad, 
                unit_price=l.precio_unitario, 
                notes=l.notas, 
                kitchen_status=KitchenStatus(l.estado_cocina),
                sent_to_kitchen_at=l.enviado_cocina_en
            ) for l in r.lineas.all()]
            
            return RestaurantOrder(id=r.id, tenant_id=r.tenant_id, table_id=r.mesa_id, status=OrderStatus(r.estado), total=r.total, created_at=r.creado_en, lines=lines)
        except PedidoRestauranteModel.DoesNotExist:
            return None

    def create_order(self, tenant_id: int, table_id: int) -> RestaurantOrder:
        r = PedidoRestauranteModel.objects.create(tenant_id=tenant_id, mesa_id=table_id, estado=OrderStatus.OPEN.value, total=0)
        return RestaurantOrder(id=r.id, tenant_id=r.tenant_id, table_id=r.mesa_id, status=OrderStatus(r.estado), total=r.total, created_at=r.creado_en, lines=[])

    def add_line_to_order(self, tenant_id: int, order_id: int, item_id: str, item_name: str, quantity: int, unit_price: float, notes: str) -> RestaurantOrderLine:
        l = LineaPedidoRestauranteModel.objects.create(
            pedido_id=order_id,
            item_id=item_id,
            item_nombre=item_name,
            cantidad=quantity,
            precio_unitario=unit_price,
            notas=notes
        )
        return RestaurantOrderLine(id=l.id, item_id=l.item_id, item_name=l.item_nombre, quantity=l.cantidad, unit_price=l.precio_unitario, notes=l.notas, kitchen_status=KitchenStatus(l.estado_cocina), sent_to_kitchen_at=l.enviado_cocina_en)

    def update_order_total(self, tenant_id: int, order_id: int, total: float) -> None:
        PedidoRestauranteModel.objects.filter(tenant_id=tenant_id, id=order_id).update(total=total)

    def close_order(self, tenant_id: int, order_id: int) -> None:
        PedidoRestauranteModel.objects.filter(tenant_id=tenant_id, id=order_id).update(estado=OrderStatus.CLOSED.value)

    def get_kitchen_lines(self, tenant_id: int) -> List[RestaurantOrderLine]:
        # get lines from open orders that are not delivered
        records = LineaPedidoRestauranteModel.objects.filter(
            pedido__tenant_id=tenant_id, 
            pedido__estado=OrderStatus.OPEN.value
        ).exclude(estado_cocina=KitchenStatus.DELIVERED.value).order_by('enviado_cocina_en').select_related('pedido__mesa')
        
        return [RestaurantOrderLine(
            id=l.id, 
            item_id=l.item_id, 
            item_name=l.item_nombre, 
            quantity=l.cantidad, 
            unit_price=l.precio_unitario, 
            notes=l.notas, 
            kitchen_status=KitchenStatus(l.estado_cocina),
            sent_to_kitchen_at=l.enviado_cocina_en,
            table_name=l.pedido.mesa.nombre,
            order_id=l.pedido.id
        ) for l in records]

    def update_kitchen_line_status(self, tenant_id: int, line_id: int, status: KitchenStatus) -> None:
        LineaPedidoRestauranteModel.objects.filter(pedido__tenant_id=tenant_id, id=line_id).update(estado_cocina=status.value)
