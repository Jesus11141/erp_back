import uuid
from typing import Dict, List, Optional
from ..domain.entities import RestaurantZone, RestaurantTable, RestaurantOrder, RestaurantOrderLine
from ..domain.repositories import RestaurantRepository
from ..domain.value_objects import TableStatus, OrderStatus, KitchenStatus
from .django_models import ZonaModel, MesaModel, PedidoRestauranteModel, LineaPedidoRestauranteModel, PlatoModel

class DjangoRestaurantRepository(RestaurantRepository):

    def get_zones(self, tenant_id: int) -> List[RestaurantZone]:
        records = ZonaModel.objects.filter(tenant_id=tenant_id)
        return [RestaurantZone(id=r.id, tenant_id=r.tenant_id, name=r.nombre) for r in records]

    def get_tables_by_zone(self, tenant_id: int, zone_id: int) -> List[RestaurantTable]:
        records = MesaModel.objects.filter(tenant_id=tenant_id, zona_id=zone_id).order_by('nombre')
        results = []
        for r in records:
            has_open = PedidoRestauranteModel.objects.filter(tenant_id=tenant_id, mesa_id=r.id, estado=OrderStatus.OPEN.value).exists()
            current_status = TableStatus.OCCUPIED if has_open else TableStatus.FREE
            if r.estado != current_status.value:
                MesaModel.objects.filter(id=r.id).update(estado=current_status.value)
            results.append(RestaurantTable(id=r.id, tenant_id=r.tenant_id, zone_id=r.zona_id, name=r.nombre, seats=r.asientos, status=current_status))
        return results

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
            
            return RestaurantOrder(
                id=r.id, 
                tenant_id=r.tenant_id, 
                table_id=r.mesa_id, 
                status=OrderStatus(r.estado), 
                total=r.total, 
                created_at=r.creado_en, 
                lines=lines,
                factura_id=r.factura_id,
                factura_numero=r.factura_numero,
                clave_acceso=r.clave_acceso,
                cliente_nombre=r.cliente_nombre,
                cliente_identificacion=r.cliente_identificacion,
                metodo_pago=r.metodo_pago
            )
        except PedidoRestauranteModel.DoesNotExist:
            return None

    def get_order_by_id(self, tenant_id: int, order_id: int) -> Optional[RestaurantOrder]:
        try:
            r = PedidoRestauranteModel.objects.prefetch_related('lineas').get(tenant_id=tenant_id, id=order_id)
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
            
            return RestaurantOrder(
                id=r.id, 
                tenant_id=r.tenant_id, 
                table_id=r.mesa_id, 
                status=OrderStatus(r.estado), 
                total=r.total, 
                created_at=r.creado_en, 
                lines=lines,
                factura_id=r.factura_id,
                factura_numero=r.factura_numero,
                clave_acceso=r.clave_acceso,
                cliente_nombre=r.cliente_nombre,
                cliente_identificacion=r.cliente_identificacion,
                metodo_pago=r.metodo_pago
            )
        except PedidoRestauranteModel.DoesNotExist:
            return None

    def create_order(self, tenant_id: int, table_id: int) -> RestaurantOrder:
        r = PedidoRestauranteModel.objects.create(tenant_id=tenant_id, mesa_id=table_id, estado=OrderStatus.OPEN.value, total=0)
        return RestaurantOrder(id=r.id, tenant_id=r.tenant_id, table_id=r.mesa_id, status=OrderStatus(r.estado), total=r.total, created_at=r.creado_en, lines=[])

    def add_line_to_order(self, tenant_id: int, order_id: int, item_id: str, item_name: str, quantity: int, unit_price: float, notes: str) -> RestaurantOrderLine:
        existing = LineaPedidoRestauranteModel.objects.filter(
            pedido_id=order_id,
            item_id=item_id,
            notas=notes,
            estado_cocina=KitchenStatus.PENDING.value
        ).first()
        if existing:
            existing.cantidad += quantity
            existing.precio_unitario = unit_price
            existing.save()
            l = existing
        else:
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

    def close_order(self, tenant_id: int, order_id: int, billing_info: Optional[dict] = None) -> None:
        pedido = PedidoRestauranteModel.objects.filter(tenant_id=tenant_id, id=order_id).select_related('mesa').first()
        if pedido:
            pedido.estado = OrderStatus.CLOSED.value
            if billing_info:
                if 'factura_id' in billing_info:
                    pedido.factura_id = billing_info['factura_id']
                if 'factura_numero' in billing_info:
                    pedido.factura_numero = billing_info['factura_numero']
                if 'clave_acceso' in billing_info:
                    pedido.clave_acceso = billing_info['clave_acceso']
                if 'cliente_nombre' in billing_info:
                    pedido.cliente_nombre = billing_info['cliente_nombre']
                if 'cliente_identificacion' in billing_info:
                    pedido.cliente_identificacion = billing_info['cliente_identificacion']
                if 'metodo_pago' in billing_info:
                    pedido.metodo_pago = billing_info['metodo_pago']
            pedido.save()
            # Clear pending kitchen lines
            pedido.lineas.exclude(estado_cocina=KitchenStatus.DELIVERED.value).update(estado_cocina=KitchenStatus.DELIVERED.value)
            # Reconcile table
            if pedido.mesa:
                has_other = PedidoRestauranteModel.objects.filter(
                    tenant_id=tenant_id,
                    mesa=pedido.mesa,
                    estado=OrderStatus.OPEN.value
                ).exists()
                if not has_other:
                    pedido.mesa.estado = TableStatus.FREE.value
                    pedido.mesa.save()

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

    def update_kitchen_line_status(self, tenant_id: int, line_id: str, status: KitchenStatus) -> None:
        ids = [i.strip() for i in str(line_id).split(',') if i.strip()]
        LineaPedidoRestauranteModel.objects.filter(pedido__tenant_id=tenant_id, id__in=ids).update(estado_cocina=status.value)

    @staticmethod
    def _as_uuid(value) -> Optional[uuid.UUID]:
        try:
            return uuid.UUID(str(value))
        except (ValueError, AttributeError, TypeError):
            return None

    def dish_exists(self, tenant_id: int, dish_id: str) -> bool:
        parsed = self._as_uuid(dish_id)
        return bool(parsed) and PlatoModel.objects.filter(tenant_id=tenant_id, id=parsed).exists()

    def get_dish_summary(self, tenant_id: int, dish_id: str) -> Optional[dict]:
        parsed = self._as_uuid(dish_id)
        if not parsed:
            return None
        dish = PlatoModel.objects.filter(tenant_id=tenant_id, id=parsed).first()
        if not dish:
            return None
        return {'name': dish.nombre, 'price': dish.precio, 'product_id': dish.product_id}

    def set_dish_product_id(self, tenant_id: int, dish_id: str, product_id: Optional[int]) -> None:
        parsed = self._as_uuid(dish_id)
        if parsed:
            PlatoModel.objects.filter(tenant_id=tenant_id, id=parsed).update(product_id=product_id)

    def get_dish_product_map(self, tenant_id: int) -> Dict[str, int]:
        rows = PlatoModel.objects.filter(tenant_id=tenant_id, product_id__isnull=False).values_list('id', 'product_id')
        return {str(dish_id): product_id for dish_id, product_id in rows}
