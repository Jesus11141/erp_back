from typing import List, Dict, Any
from decimal import Decimal
from modules.technical_service.domain.entities import WorkOrder, WorkOrderItem
from modules.technical_service.domain.repositories import WorkOrderRepository
from modules.ventas.domain.entities import AccountReceivable
from modules.ventas.infrastructure.repository_impl import DjangoAccountReceivableRepository
from modules.pos.domain.entities import CashRegisterMovement
from modules.contabilidad.application.accounting_service import AccountingService
from modules.contabilidad.infrastructure.repository_impl import DjangoAccountingRepository

class CreateWorkOrderUseCase:
    def __init__(self, order_repo: WorkOrderRepository, register_repo=None, param_repo=None, inventory_service=None):
        self.order_repo = order_repo
        self.register_repo = register_repo
        self.param_repo = param_repo
        self.inventory_service = inventory_service
        
    def execute(self, tenant_id: int, user_id: int, data: Dict[str, Any]) -> WorkOrder:
        items = []
        for item_data in data.get('items', []):
            items.append(
                WorkOrderItem(
                    id=None,
                    product_id=item_data.get('product_id'),
                    description=item_data['description'],
                    quantity=Decimal(str(item_data['quantity'])),
                    unit_price=Decimal(str(item_data['unit_price'])),
                    discount=Decimal(str(item_data.get('discount', 0)))
                )
            )
            
        order = WorkOrder(
            id=None,
            tenant_id=tenant_id,
            customer_id=data['customer_id'],
            customer_name=data['customer_name'],
            device_type=data['device_type'],
            device_model=data.get('device_model', 'Generic'),
            device_identifier=data['device_identifier'],
            physical_conditions=data.get('physical_conditions', ''),
            reported_fault=data['reported_fault'],
            advance_payment=Decimal(str(data.get('advance_payment', 0))),
            status=data.get('status', 'RECEIVED'),
            items=items
        )
        # 1. Validar Caja (si aplica)
        open_register = None
        if self.param_repo and self.register_repo:
            param = self.param_repo.get(tenant_id, 'pos', 'apertura_caja_obligatoria')
            obligatorio = param.value.lower() == 'true' if param else True
            
            if obligatorio:
                if not user_id:
                    raise ValueError("Debe iniciar sesión correctamente para registrar órdenes.")
                open_register = self.register_repo.get_open_register(tenant_id, user_id)
                if not open_register:
                    raise ValueError("Debe abrir caja en el módulo POS antes de registrar órdenes de trabajo.")

        saved_order = self.order_repo.save(order)
        
        # 2. Descontar Inventario
        if self.inventory_service:
            for item in saved_order.items:
                if item.product_id:
                    self.inventory_service.reduce_stock(tenant_id, item.product_id, item.quantity)
                    
        # 3. Registrar Movimiento de Caja (Abono Inicial)
        if saved_order.advance_payment > 0 and open_register and self.register_repo:
            movement = CashRegisterMovement(
                id=0,
                tenant_id=tenant_id,
                register_id=open_register.id,
                user_id=user_id,
                movement_type='inflow',
                amount=saved_order.advance_payment,
                reason=f"Abono Inicial OT #{saved_order.id} - Cliente: {saved_order.customer_name}"
            )
            self.register_repo.save_movement(movement)
            
            # Registrar Anticipo Contable
            try:
                acc_repo = DjangoAccountingRepository()
                acc_service = AccountingService(acc_repo)
                acc_service.register_work_order_advance(
                    tenant_id=tenant_id,
                    order_id=saved_order.id,
                    amount=saved_order.advance_payment
                )
            except Exception as e:
                print(f"Error generando asiento contable para anticipo inicial de orden {saved_order.id}: {e}")
        
        if saved_order.balance_due > 0:
            ar_repo = DjangoAccountReceivableRepository()
            ar = AccountReceivable(
                id=None,
                tenant_id=tenant_id,
                customer_id=saved_order.customer_id,
                customer_name=saved_order.customer_name,
                total_amount=saved_order.total,
                balance_due=saved_order.balance_due,
                status='PENDING',
                reference_type='WORK_ORDER',
                reference_id=saved_order.id
            )
            ar_repo.save(ar)
            
        return saved_order
