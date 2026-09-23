from typing import Dict, Any
from decimal import Decimal
from modules.technical_service.domain.repositories import WorkOrderRepository
from modules.pos.domain.entities import CashRegisterMovement
from modules.contabilidad.application.accounting_service import AccountingService
from modules.contabilidad.infrastructure.repository_impl import DjangoAccountingRepository
from modules.ventas.infrastructure.django_models import AccountReceivableModel

class PayWorkOrderUseCase:
    def __init__(self, order_repo: WorkOrderRepository, register_repo=None):
        self.order_repo = order_repo
        self.register_repo = register_repo
        
    def execute(self, tenant_id: int, user_id: int, order_id: int, payment_amount: Decimal) -> Dict[str, Any]:
        order = self.order_repo.get_by_id(tenant_id, order_id)
        if not order:
            raise ValueError(f"No se encontró la orden de trabajo con ID {order_id}.")
            
        if payment_amount <= 0:
            raise ValueError("El monto del abono debe ser mayor a cero.")
            
        if payment_amount > order.balance_due:
            raise ValueError(f"El monto del abono (${payment_amount}) no puede ser mayor al saldo pendiente (${order.balance_due}).")

        # 1. Validar Caja Abierta
        open_register = None
        if self.register_repo:
            open_register = self.register_repo.get_open_register(tenant_id, user_id)
            if not open_register:
                raise ValueError("Debe abrir caja en el módulo POS antes de registrar cobros.")

        # 2. Registrar Movimiento de Caja
        if open_register and self.register_repo:
            is_liquidation = payment_amount == order.balance_due
            texto_concepto = "Liquidación" if is_liquidation else "Abono Parcial"
            movement = CashRegisterMovement(
                id=0,
                tenant_id=tenant_id,
                register_id=open_register.id,
                user_id=user_id,
                movement_type='inflow',
                amount=payment_amount,
                reason=f"{texto_concepto} OT #{order.id} - Cliente: {order.customer_name}"
            )
            self.register_repo.save_movement(movement)

        # 3. Actualizar la Orden
        order.advance_payment += payment_amount
        # Guardamos la orden. Asumimos que el repo.save() actualiza si ya existe
        saved_order = self.order_repo.save(order)
        
        # 4. Bajar la Cuenta por Cobrar Interna (si existe)
        ar_model = AccountReceivableModel.objects.filter(
            tenant_id=tenant_id, 
            reference_type='WORK_ORDER', 
            reference_id=order.id
        ).first()
        
        if ar_model:
            ar_model.balance_due -= payment_amount
            if ar_model.balance_due <= 0:
                ar_model.status = 'PAID'
            ar_model.save()
            
        # 5. Generar Asiento Contable
        # Aquí usamos el AccountingService para registrar el movimiento de contabilidad real
        acc_repo = DjangoAccountingRepository()
        acc_service = AccountingService(acc_repo)
        
        try:
            if is_liquidation:
                # Si liquida la orden, se genera la venta final
                # El "previous_advance" es lo que ya había abonado ANTES de este pago actual
                previous_advance = saved_order.advance_payment - payment_amount
                acc_service.register_work_order_liquidation(
                    tenant_id=tenant_id,
                    order_id=order.id,
                    total=saved_order.total,
                    previous_advance=previous_advance,
                    current_payment=payment_amount
                )
            else:
                # Si es solo un abono parcial, se registra como anticipo
                acc_service.register_work_order_advance(
                    tenant_id=tenant_id, 
                    order_id=order.id, 
                    amount=payment_amount
                )
        except Exception as e:
            # Log failure but don't crash the payment
            print(f"Error generando asiento contable para abono de orden {order.id}: {e}")

        return {
            'success': True,
            'message': 'Abono registrado correctamente.',
            'new_balance': float(saved_order.balance_due),
            'order': {
                'id': saved_order.id,
                'advance_payment': float(saved_order.advance_payment),
                'balance_due': float(saved_order.balance_due)
            }
        }
