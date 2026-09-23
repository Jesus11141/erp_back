from typing import List, Optional, Dict, Any
from decimal import Decimal
from ..domain.entities import AccountReceivable, ReceivablePayment
from ..domain.repositories import AccountReceivableRepository

class ListAccountReceivablesUseCase:
    def __init__(self, repo: AccountReceivableRepository):
        self.repo = repo
        
    def execute(self, tenant_id: int) -> List[AccountReceivable]:
        return self.repo.list_by_tenant(tenant_id)

class AddReceivablePaymentUseCase:
    def __init__(self, repo: AccountReceivableRepository, register_repo=None, param_repo=None):
        self.repo = repo
        self.register_repo = register_repo
        self.param_repo = param_repo
        
    def execute(self, tenant, user_id: int, account_id: int, data: Dict[str, Any]) -> AccountReceivable:
        ar = self.repo.find_by_id(account_id, tenant.id)
        if not ar:
            raise ValueError("Account Receivable not found")
            
        amount = Decimal(str(data['amount']))
        if amount <= 0:
            raise ValueError("Amount must be greater than zero")
            
        if amount > ar.balance_due:
            raise ValueError("Amount exceeds balance due")
            
        # 1. Validar Caja (si tiene módulo POS activo)
        open_register = None
        if tenant.has_module('pos') and self.param_repo and self.register_repo:
            param = self.param_repo.get(tenant.id, 'pos', 'apertura_caja_obligatoria')
            obligatorio = param.value.lower() == 'true' if param else True
            
            if obligatorio:
                if not user_id:
                    raise ValueError("Debe iniciar sesión correctamente para registrar abonos.")
                open_register = self.register_repo.get_open_register(tenant.id, user_id)
                if not open_register:
                    raise ValueError("Debe abrir caja en el módulo POS antes de registrar abonos a cuentas por cobrar.")

        # 2. Registrar abono en Cuentas por Cobrar
        payment = ReceivablePayment(
            id=None,
            account_receivable_id=ar.id,
            amount=amount,
            payment_method=data['payment_method'],
            date=None, # will be set by DB
            notes=data.get('notes', '')
        )
        self.repo.add_payment(payment)
        
        # 3. Registrar Movimiento de Caja (Ingreso de dinero)
        if open_register and self.register_repo:
            from modules.pos.domain.entities import RegisterMovement
            mov = RegisterMovement(
                id=None,
                register_id=open_register.id,
                type='IN',
                amount=amount,
                payment_method=data['payment_method'],
                reason='Pago de Deuda Cta. Cobrar - Cliente: ' + (ar.customer_name or 'N/A'),
                reference_id=str(ar.id),
                date=None
            )
            self.register_repo.add_movement(mov)
            
        # 4. Actualizar balance
        ar.balance_due -= amount
        if ar.balance_due == 0:
            ar.status = 'PAID'
        else:
            ar.status = 'PARTIAL'
            
        return self.repo.save(ar)
