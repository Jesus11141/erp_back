from typing import Dict, List, Optional
from decimal import Decimal, InvalidOperation
from ..domain.entities import RestaurantZone, RestaurantTable, RestaurantOrder, RestaurantOrderLine, RecipeIngredient
from ..domain.repositories import RestaurantRepository, RestaurantInventoryService
from ..domain.value_objects import TableStatus, OrderStatus, KitchenStatus

class RestaurantService:
    def __init__(self, repo: RestaurantRepository, inventory_service: Optional[RestaurantInventoryService] = None):
        self._repo = repo
        self._inventory = inventory_service


    # ------------------------------------------------------------------
    # Recipes (escandallo): stored in inventory as the components of a hidden
    # composite product linked to the dish (single source of truth).
    # ------------------------------------------------------------------
    def get_dish_recipe(self, tenant_id: int, dish_id: str) -> dict:
        dish = self._repo.get_dish_summary(tenant_id, dish_id)
        if not dish:
            raise LookupError('Dish not found')
        ingredients = []
        if self._inventory and dish['product_id']:
            ingredients = self._inventory.get_recipe(tenant_id, dish['product_id'])
        products = self._inventory.get_products_info(tenant_id, [i.product_id for i in ingredients]) if self._inventory else {}

        items = []
        total_cost = Decimal('0.00')
        for ing in ingredients:
            info = products.get(ing.product_id)
            unit_cost = Decimal(str(info['unit_cost'])) if info else Decimal('0.00')
            line_cost = (unit_cost * ing.quantity).quantize(Decimal('0.01'))
            total_cost += line_cost
            items.append({
                'product_id': ing.product_id,
                'product_name': info['name'] if info else f'Product #{ing.product_id}',
                'product_code': info['code'] if info else '',
                'unit': info['unit'] if info else '',
                'quantity': float(ing.quantity),
                'unit_cost': float(unit_cost),
                'line_cost': float(line_cost),
                'current_stock': float(info['current_stock']) if info else 0.0,
            })
        return {'dish_id': str(dish_id), 'ingredients': items, 'total_cost': float(total_cost)}

    def set_dish_recipe(self, tenant_id: int, dish_id: str, ingredients_data: List[dict]) -> dict:
        dish = self._repo.get_dish_summary(tenant_id, dish_id)
        if not dish:
            raise LookupError('Dish not found')
        if self._inventory is None:
            raise ValueError('Inventory service not available')

        merged: Dict[int, Decimal] = {}
        for raw in ingredients_data or []:
            try:
                product_id = int(raw.get('product_id'))
                quantity = Decimal(str(raw.get('quantity')))
            except (TypeError, ValueError, InvalidOperation):
                raise ValueError('Invalid ingredient data')
            if quantity <= 0:
                raise ValueError('Ingredient quantity must be greater than zero')
            merged[product_id] = merged.get(product_id, Decimal('0')) + quantity

        existing = self._inventory.get_products_info(tenant_id, list(merged.keys()))
        missing = [pid for pid in merged if pid not in existing]
        if missing:
            raise ValueError(f'Inventory products not found: {missing}')

        product_id = dish['product_id']
        if not product_id:
            if not merged:
                return self.get_dish_recipe(tenant_id, dish_id)
            product_id = self._inventory.ensure_dish_product(tenant_id, dish_id, dish['name'], dish['price'])
            self._repo.set_dish_product_id(tenant_id, dish_id, product_id)

        self._inventory.replace_recipe(
            tenant_id, product_id,
            [RecipeIngredient(product_id=pid, quantity=qty) for pid, qty in merged.items()]
        )
        return self.get_dish_recipe(tenant_id, dish_id)

    def get_recipe_counts(self, tenant_id: int) -> Dict[str, int]:
        if not self._inventory:
            return {}
        dish_products = self._repo.get_dish_product_map(tenant_id)
        counts = self._inventory.get_recipe_counts(tenant_id, list(dish_products.values()))
        return {dish_id: counts.get(pid, 0) for dish_id, pid in dish_products.items() if counts.get(pid)}

    def delete_dish_recipe_holder(self, tenant_id: int, dish_id: str) -> None:
        """Removes the hidden inventory product (and its recipe) linked to a dish. Never raises."""
        try:
            dish = self._repo.get_dish_summary(tenant_id, dish_id)
            if self._inventory and dish and dish['product_id']:
                self._repo.set_dish_product_id(tenant_id, dish_id, None)
                self._inventory.delete_dish_product(tenant_id, dish['product_id'])
        except Exception as e:
            print(f"[RestaurantService] Error removing dish recipe holder {dish_id}: {e}")

    def _consume_recipe_stock(self, tenant_id: int, order: RestaurantOrder, user_id: int = 0) -> List[dict]:
        """Deducts inventory for every dish sold in the order. Never blocks the checkout."""
        if not self._inventory or not order:
            return []

        dish_products = self._repo.get_dish_product_map(tenant_id)
        sold: Dict[int, int] = {}
        for line in order.lines:
            product_id = dish_products.get(str(line.item_id))
            if product_id:
                sold[product_id] = sold.get(product_id, 0) + line.quantity

        warnings = []
        for product_id, quantity in sold.items():
            try:
                self._inventory.consume_dish(
                    tenant_id, product_id, Decimal(quantity),
                    reference=f'restaurant_order_{order.id}', user_id=user_id
                )
            except Exception as e:
                print(f"[RestaurantService] Error consuming dish product {product_id}: {e}")
                warnings.append({'product_id': product_id, 'error': str(e)})
        return warnings
        
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
            grouped_lines = {}
            for l in p.lines:
                k = (l.item_name, float(l.unit_price), l.notes or '', l.kitchen_status.value)
                if k not in grouped_lines:
                    grouped_lines[k] = {
                        'id': str(l.id),
                        'item_nombre': l.item_name,
                        'cantidad': l.quantity,
                        'precio_unitario': float(l.unit_price),
                        'notas': l.notes,
                        'estado_cocina': l.kitchen_status.value
                    }
                else:
                    grouped_lines[k]['cantidad'] += l.quantity

            result.append({
                'id': str(p.id),
                'mesa_id': str(p.table_id),
                'estado': p.status.value,
                'total': float(p.total),
                'creado_en': p.created_at,
                'lineas': list(grouped_lines.values())
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

    def close_order(self, tenant_id: int, order_id: int, table_id: Optional[int] = None, billing_data: Optional[dict] = None, user_id: int = 0) -> dict:
        # Only an open order consumes ingredients, so closing twice never double-deducts stock.
        order_to_close = self._repo.get_order_by_id(tenant_id, order_id)
        should_consume_stock = bool(order_to_close and order_to_close.status == OrderStatus.OPEN)
        billing_info_record = None
        factura_dict = None

        if billing_data and billing_data.get('facturar', True):
            try:
                from modules.tax_documents.invoicing.application.create_service import CreateInvoice
                from modules.tax_documents.invoicing.infrastructure.persistence.repository_impl import DjangoInvoiceRepository
                from modules.tax_documents.invoicing.infrastructure.ui.views import _get_emisor, _param

                emisor = _get_emisor(tenant_id)
                iva_str = _param(tenant_id, 'ventas', 'iva', '15')
                try:
                    vat_val = float(iva_str)
                except (ValueError, TypeError):
                    vat_val = 15.0
                
                factor_iva = 1.0 + (vat_val / 100.0)

                cliente_info = billing_data.get('cliente', {})
                cliente_nombre = cliente_info.get('nombre') or 'CONSUMIDOR FINAL'
                cliente_id = cliente_info.get('identificacion') or '9999999999999'
                cliente_tipo_id = cliente_info.get('tipo_id')
                if not cliente_tipo_id:
                    if cliente_id == '9999999999999':
                        cliente_tipo_id = '07'
                    elif len(cliente_id) == 13:
                        cliente_tipo_id = '04'
                    elif len(cliente_id) == 10:
                        cliente_tipo_id = '05'
                    else:
                        cliente_tipo_id = '06'

                cliente_email = cliente_info.get('email', '')
                cliente_dir = cliente_info.get('direccion', 'S/D')
                metodo_pago = billing_data.get('metodo_pago', '01')

                # Auto create or update customer in Ventas if not Consumidor Final
                if cliente_id != '9999999999999' and cliente_nombre:
                    try:
                        from modules.ventas.infrastructure.django_models import CustomerModel
                        CustomerModel.objects.update_or_create(
                            tenant_id=tenant_id,
                            rfc=cliente_id,
                            defaults={
                                'name': cliente_nombre,
                                'email': cliente_email,
                                'address': cliente_dir,
                                'active': True
                            }
                        )
                    except Exception as e:
                        print(f"[RestauranteService] Error registrando cliente: {e}")

                order = self._repo.get_order_by_id(tenant_id, order_id)
                lines = order.lines if order else []

                # Group lines by item and unit_price
                grouped_items = {}
                for l in lines:
                    key = (str(l.item_id), l.item_name, float(l.unit_price))
                    if key not in grouped_items:
                        grouped_items[key] = {
                            'description': l.item_name,
                            'quantity': l.quantity,
                            'unit_price': round(float(l.unit_price) / factor_iva, 4),
                            'discount': 0,
                            'main_code': str(l.item_id),
                            'vat_rate': str(int(vat_val))
                        }
                    else:
                        grouped_items[key]['quantity'] += l.quantity

                items = list(grouped_items.values())
                if not items and order and order.total > 0:
                    items = [{
                        'description': 'Consumo Restaurante',
                        'quantity': 1,
                        'unit_price': round(float(order.total) / factor_iva, 4),
                        'discount': 0,
                        'main_code': 'REST-01',
                        'vat_rate': str(int(vat_val))
                    }]

                invoice_data = {
                    'client': cliente_nombre,
                    'client_identification': cliente_id,
                    'client_id_type': cliente_tipo_id,
                    'client_address': cliente_dir,
                    'client_email': cliente_email,
                    'payment_method': metodo_pago,
                    'notes': f'Mesa Restaurante - Pedido #{order_id}',
                    'items': items
                }

                invoice_repo = DjangoInvoiceRepository()
                factura = CreateInvoice(invoice_repo).execute(
                    tenant_id=tenant_id,
                    data=invoice_data,
                    issuer=emisor,
                    vat=int(vat_val),
                    document_type='01'
                )

                sri_status = getattr(factura, 'sri_status', None)
                sri_message = getattr(factura, 'sri_message', None)

                # Emit to SRI if requested
                if billing_data.get('emitir_sri'):
                    cert_path = _param(tenant_id, 'facturacion', 'signature_file', '')
                    cert_pass = _param(tenant_id, 'facturacion', 'signature_password', '')
                    if cert_path:
                        try:
                            from modules.tax_documents.invoicing.application.emit_invoice_sri import EmitInvoiceSRI
                            factura = EmitInvoiceSRI(invoice_repo).execute(
                                factura.id, tenant_id, emisor, cert_path, cert_pass
                            )
                            sri_status = getattr(factura, 'sri_status', None)
                            sri_message = getattr(factura, 'sri_message', None)
                        except Exception as ex:
                            print(f"[RestauranteService] Error emitiendo al SRI: {ex}")
                            sri_status = 'error_emision'
                            sri_message = str(ex)

                billing_info_record = {
                    'factura_id': factura.id,
                    'factura_numero': factura.number,
                    'clave_acceso': getattr(factura, 'access_key', ''),
                    'cliente_nombre': cliente_nombre,
                    'cliente_identificacion': cliente_id,
                    'metodo_pago': metodo_pago
                }

                factura_dict = {
                    'id': factura.id,
                    'numero': factura.number,
                    'clave_acceso': getattr(factura, 'access_key', ''),
                    'total': float(factura.total),
                    'subtotal': float(factura.subtotal),
                    'iva': float(factura.tax),
                    'cliente': cliente_nombre,
                    'identificacion': cliente_id,
                    'metodo_pago': metodo_pago,
                    'sri_status': sri_status,
                    'sri_message': sri_message
                }
            except Exception as e:
                print(f"[RestauranteService] Error en facturación: {e}")
                # Don't block closing if invoicing fails unexpectedly, but return warning
                factura_dict = {'error': str(e)}
        elif billing_data and not billing_data.get('facturar', True):
            billing_info_record = {
                'factura_id': billing_data.get('factura_id'),
                'factura_numero': billing_data.get('factura_numero'),
                'clave_acceso': billing_data.get('clave_acceso'),
                'cliente_nombre': billing_data.get('cliente_nombre'),
                'cliente_identificacion': billing_data.get('cliente_identificacion'),
                'metodo_pago': billing_data.get('metodo_pago', '01')
            }

        self._repo.close_order(tenant_id, order_id, billing_info=billing_info_record)
        stock_warnings = []
        if should_consume_stock:
            stock_warnings = self._consume_recipe_stock(tenant_id, order_to_close, user_id)
        if table_id:
            open_order = self._repo.get_open_order_for_table(tenant_id, table_id)
            if not open_order:
                self._repo.update_table_status(tenant_id, table_id, TableStatus.FREE)

        res = {'status': 'cerrado'}
        if factura_dict:
            res['factura'] = factura_dict
        if stock_warnings:
            res['inventory_warnings'] = stock_warnings
        return res

    def get_kitchen_dashboard(self, tenant_id: int) -> List[dict]:
        lines = self._repo.get_kitchen_lines(tenant_id)
        from django.utils import timezone
        now = timezone.now()
        
        grouped = {}
        for l in lines:
            key = (str(l.order_id), l.item_name, l.kitchen_status.value, l.notes or '')
            seconds_wait = (now - l.sent_to_kitchen_at).total_seconds() if l.sent_to_kitchen_at else 0
            if key not in grouped:
                grouped[key] = {
                    'id': str(l.id),
                    'pedido_id': str(l.order_id),
                    'mesa_nombre': l.table_name or '',
                    'item_nombre': l.item_name,
                    'cantidad': l.quantity,
                    'notas': l.notes,
                    'estado_cocina': l.kitchen_status.value,
                    'tiempo_espera': seconds_wait,
                    'ids': [str(l.id)]
                }
            else:
                grouped[key]['cantidad'] += l.quantity
                grouped[key]['ids'].append(str(l.id))
                grouped[key]['id'] = ','.join(grouped[key]['ids'])
                grouped[key]['tiempo_espera'] = max(grouped[key]['tiempo_espera'], seconds_wait)
                
        return list(grouped.values())
        
    def update_kitchen_line(self, tenant_id: int, line_id: str, status_str: str) -> dict:
        try:
            status = KitchenStatus(status_str)
            self._repo.update_kitchen_line_status(tenant_id, line_id, status)
            return {'status': 'ok'}
        except ValueError:
            raise ValueError(f"Invalid kitchen status: {status_str}")
