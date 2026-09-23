from decimal import Decimal
from typing import Optional, List
from datetime import datetime
from ..domain.entities import CashRegister, POSSale, POSSaleItem, CashRegisterClosure, POSCustomer, POSSaleSummary, CashRegisterMovement
from ..domain.repositories import CashRegisterRepository, POSSaleRepository, POSDependencyRepository, POSInventoryService, POSBillingService, POSAccountingService
from modules.parametros.domain.repositories import ParameterRepository

class POSService:
    """
    Pure application service for the Point of Sale (POS) system.
    Contains only business and application logic, with no direct Django dependencies.
    """
    def __init__(self,
                 register_repo: CashRegisterRepository,
                 sale_repo: POSSaleRepository,
                 dep_repo: POSDependencyRepository,
                 param_repo: Optional[ParameterRepository] = None,
                 inventory_service: Optional[POSInventoryService] = None,
                 billing_service: Optional[POSBillingService] = None,
                 accounting_service: Optional[POSAccountingService] = None):
        self._register_repo = register_repo
        self._sale_repo = sale_repo
        self._dep_repo = dep_repo
        self._param_repo = param_repo
        self._inventory_service = inventory_service
        self._billing_service = billing_service
        self._accounting_service = accounting_service

    def open_register(self,
                      tenant_id: int, 
                      user_id: int,
                      name: str,
                      initial_balance: Decimal = Decimal('0.00'),
                      opening_breakdown: Optional[dict] = None,
                      branch_id: Optional[int] = None) -> CashRegister:
        
        # 1. Validate that no open cash register register exists for this user
        open_reg = self._register_repo.get_open_register(tenant_id, user_id)
        if open_reg:
            raise ValueError("You already have an open register")

        # 2. Validate active physical registers
        if not self._register_repo.has_active_physical_registers(tenant_id):
            raise ValueError("Cannot open shift: No physical registers registered for this company. Register a register first in Location Control.")

        # 3. Validate active employees
        if not self._dep_repo.has_active_employees(tenant_id):
            raise ValueError("Cannot open shift: No employees or cashiers registered in the company. Register at least one employee in Human Resources.")

        # 4. Validate bills/coins breakdown if configured
        if self._param_repo:
            param_bills = self._param_repo.get(tenant_id, 'pos', 'desglose_billetes_apertura')
            param_coins = self._param_repo.get(tenant_id, 'pos', 'desglose_monedas_apertura')
            
            breakdown_active = (
                (param_bills and param_bills.value.lower() == 'true') or 
                (param_coins and param_coins.value.lower() == 'true')
            )
            
            if breakdown_active:
                if not opening_breakdown:
                    raise ValueError("Cash breakdown is required by register configuration")
                total_breakdown = Decimal('0.00')
                
                if param_bills and param_bills.value.lower() == 'true':
                    bills = opening_breakdown.get('bills', {})
                    for denom, qty in bills.items():
                        try:
                            total_breakdown += Decimal(denom) * Decimal(str(qty))
                        except (ValueError, TypeError):
                            pass
                
                if param_coins and param_coins.value.lower() == 'true':
                    coins = opening_breakdown.get('coins', {})
                    for denom, qty in coins.items():
                        try:
                            total_breakdown += Decimal(denom) * Decimal(str(qty))
                        except (ValueError, TypeError):
                            pass
                
                initial_balance = total_breakdown

        # 5. Get emission point from physical register
        emission_point = '001'
        if name:
            from modules.pos.infrastructure.django_models import PhysicalCashRegisterModel
            phys_reg = PhysicalCashRegisterModel.objects.filter(tenant_id=tenant_id, name=name, branch_id=branch_id).first()
            if phys_reg and phys_reg.emission_point:
                emission_point = phys_reg.emission_point

        # 6. Create CashRegister and open it
        register = CashRegister(
            id=0,
            tenant_id=tenant_id,
            name=name,
            user_id=user_id,
            status='closed',
            initial_balance=Decimal('0.00'),
            final_balance=None,
            opened_at=None,
            closed_at=None,
            opening_breakdown=opening_breakdown,
            branch_id=branch_id,
            emission_point=emission_point
        )
        register.open(initial_balance, user_id, opening_breakdown)
        return self._register_repo.save(register)

    def close_register(self,
                       register_id: int,
                       tenant_id: int,
                       final_balance: Decimal = Decimal('0.00'),
                       observations: str = '',
                       closure_breakdown: Optional[dict] = None) -> dict:
        
        register = self._register_repo.get_by_id(register_id, tenant_id)
        if not register:
            raise ValueError("Register not found")

        # 1. Validate cash breakdown if configured
        if self._param_repo:
            param_bills = self._param_repo.get(tenant_id, 'pos', 'desglose_billetes_cierre')
            param_coins = self._param_repo.get(tenant_id, 'pos', 'desglose_monedas_cierre')
            
            breakdown_active = (
                (param_bills and param_bills.value.lower() == 'true') or 
                (param_coins and param_coins.value.lower() == 'true')
            )
            
            if breakdown_active:
                if not closure_breakdown:
                    raise ValueError("Cash breakdown is required to close the register")
                total_breakdown = Decimal('0.00')
                
                if param_bills and param_bills.value.lower() == 'true':
                    bills = closure_breakdown.get('bills', {})
                    for denom, qty in bills.items():
                        try:
                            total_breakdown += Decimal(denom) * Decimal(str(qty))
                        except (ValueError, TypeError):
                            pass
                
                if param_coins and param_coins.value.lower() == 'true':
                    coins = closure_breakdown.get('coins', {})
                    for denom, qty in coins.items():
                        try:
                            total_breakdown += Decimal(denom) * Decimal(str(qty))
                        except (ValueError, TypeError):
                            pass
                
                final_balance = total_breakdown

        # 2. Totalize register sales
        sales = self._sale_repo.list_by_register(register_id, tenant_id)
        
        sales_summaries = []
        payment_counts = {'cash': 0, 'card': 0, 'transfer': 0}
        
        for s in sales:
            if s.status == 'completed':
                payment_counts[s.payment_method] = payment_counts.get(s.payment_method, 0) + 1
                sales_summaries.append(POSSaleSummary(
                    sale_id=s.id,
                    created_at=s.created_at,
                    customer_name=s.customer.name,
                    payment_method=s.payment_method,
                    reference_number=s.reference_number or '',
                    total=s.total
                ))

        total_cash = sum(s.total for s in sales if s.payment_method == 'cash' and s.status == 'completed')
        total_card = sum(s.total for s in sales if s.payment_method == 'card' and s.status == 'completed')
        total_transfer = sum(s.total for s in sales if s.payment_method == 'transfer' and s.status == 'completed')
        sales_count = len([s for s in sales if s.status == 'completed'])

        # Store breakdown in structured English keys (infrastructure translates if needed)
        complete_closure_breakdown = {
            'transactions': sales_summaries,
            'counts': payment_counts,
            'cash_breakdown': closure_breakdown
        }

        # 3. Calculate expected balances and differences
        movements = self._register_repo.get_movements_by_register(register_id, tenant_id)
        total_inflows = sum(m.amount for m in movements if m.movement_type == 'inflow')
        total_outflows = sum(m.amount for m in movements if m.movement_type == 'outflow')

        expected_balance = register.initial_balance + total_cash + total_inflows - total_outflows
        difference = final_balance - expected_balance

        # 4. Close register
        register.close(final_balance)
        self._register_repo.save(register)
        
        # 5. Save immutable register closure record
        closure = CashRegisterClosure(
            id=0,
            tenant_id=tenant_id,
            register_id=register_id,
            user_id=register.user_id,
            opened_at=register.opened_at,
            closed_at=register.closed_at,
            initial_balance=register.initial_balance,
            total_cash=total_cash,
            total_card=total_card,
            total_transfer=total_transfer,
            total_inflows=total_inflows,
            total_outflows=total_outflows,
            sales_count=sales_count,
            expected_balance=expected_balance,
            counted_balance=final_balance,
            difference=difference,
            observations=observations,
            closure_breakdown=complete_closure_breakdown
        )
        self._register_repo.save_closure(closure)
        
        return {
            'register':            register,
            'total_cash':          total_cash,
            'total_card':          total_card,
            'total_transfer':      total_transfer,
            'total_inflows':       total_inflows,
            'total_outflows':      total_outflows,
            'total_sales':         total_cash + total_card + total_transfer,
            'sales_count':         sales_count,
            'initial_balance':     register.initial_balance,
            'expected_balance':    expected_balance,
            'final_balance':       final_balance,
            'difference':          difference,
        }

    def register_movement(self, tenant_id: int, user_id: int, register_id: int, movement_type: str, amount: Decimal, reason: str) -> CashRegisterMovement:
        register = self._register_repo.get_by_id(register_id, tenant_id)
        if not register or register.status != 'open':
            raise ValueError("No open register to record movement")

        if movement_type not in ('inflow', 'outflow'):
            raise ValueError("Invalid movement type")
            
        if amount <= 0:
            raise ValueError("Amount must be greater than zero")

        movement = CashRegisterMovement(
            id=0,
            tenant_id=tenant_id,
            register_id=register_id,
            user_id=user_id,
            movement_type=movement_type,
            amount=amount,
            reason=reason
        )
        return self._register_repo.save_movement(movement)

    def process_sale(self,
                     tenant_id: int,
                     register_id: int,
                     user_id: int,
                     items: list,
                     payment_method: str,
                     amount_received: Decimal,
                     vat_rate: Decimal = Decimal('0.12'),
                     sale_without_stock: bool = False,
                     customer: Optional[POSCustomer] = None,
                     emit_invoice: bool = False,
                     reference_number: Optional[str] = None,
                     quotation_id: Optional[int] = None,
                     seller_id: Optional[int] = None,
                     document_type: str = '01') -> POSSale:
        
        register = self._register_repo.get_by_id(register_id, tenant_id)
        if not register or register.status != 'open':
            raise ValueError("No open register")
            
        if quotation_id:
            try:
                from modules.ventas.application.convert_quotation_to_order import ConvertQuotationToOrder
                from modules.ventas.infrastructure.repository_impl import DjangoQuotationRepository, DjangoOrderRepository
                # Instead of completely creating a generic order, we can just mark the quotation as accepted.
                # However, the easiest way to clear it from "pending" is to convert it.
                ConvertQuotationToOrder(
                    DjangoQuotationRepository(), DjangoOrderRepository()
                ).execute(quotation_id, tenant_id)
            except Exception as e:
                pass # Don't block the POS sale if quotation conversion fails
                
        sale_items = []
        for i in items:
            prod_id = i.get('product_id')
            qty = Decimal(str(i['quantity']))
            price_u = Decimal(str(i['unit_price']))

            if prod_id:
                try:
                    from modules.inventario.application.cotizador_service import QuotationService
                    scaled_price, rule = QuotationService.resolve_unit_price(tenant_id, prod_id, qty)
                    if rule:
                        price_u = scaled_price
                except Exception:
                    pass

            sale_items.append(POSSaleItem(
                product_id=prod_id,
                code=i['code'],
                description=i['description'],
                quantity=qty,
                unit_price=price_u,
                discount=Decimal(str(i.get('discount', 0)))
            ))

        # 2. Validate stock available
        if self._inventory_service and not sale_without_stock:
            for item in sale_items:
                if not item.product_id:
                    continue
                stock_available = self._inventory_service.get_stock_available(tenant_id, item.product_id, register.branch_id)
                if stock_available < item.quantity:
                    prod_details = self._inventory_service.get_product_details(tenant_id, item.product_id)
                    product_name = prod_details.get('name', f"Product #{item.product_id}")
                    product_unit = prod_details.get('unit', '')
                    raise ValueError(f"Insufficient stock for '{product_name}'. Available: {stock_available} {product_unit}")

        # 3. Ensure customer exists
        active_customer = customer or POSCustomer.default_final_consumer()
        self._dep_repo.ensure_customer_exists(
            tenant_id=tenant_id,
            customer=active_customer
        )

        # 4. Create, complete and save the sale
        pm_map = {'cash': 'cash', 'card': 'card', 'transfer': 'transfer'}
        mapped_pm = pm_map.get(payment_method, 'cash')

        sale = POSSale(
            id=0,
            tenant_id=tenant_id,
            register_id=register_id,
            user_id=user_id,
            seller_id=seller_id,
            items=sale_items,
            payment_method=mapped_pm,
            amount_received=Decimal(str(amount_received)),
            vat_rate=vat_rate,
            customer=active_customer,
            reference_number=reference_number,
            document_type=document_type
        )
        sale.complete()
        sale = self._sale_repo.save(sale)

        # 5. Deduct stock from inventory
        if self._inventory_service:
            for item in sale_items:
                if item.product_id:
                    try:
                        self._inventory_service.adjust_stock(
                            tenant_id=tenant_id,
                            product_id=item.product_id,
                            quantity=item.quantity,
                            type='out',
                            reference=f'venta_pos_{sale.id}',
                            user_id=user_id,
                            branch_id=register.branch_id
                        )
                    except Exception:
                        pass

        # 6. General Ledger bookkeeping
        if self._accounting_service:
            try:
                self._accounting_service.register_sale_entry(tenant_id, sale)
            except Exception:
                pass

        # 7. Create SRI Invoice or Nota de Venta
        if self._billing_service and emit_invoice and customer:
            emisor = self._billing_service.get_issuer(tenant_id)
            if register and register.branch_id:
                from modules.inventario.infrastructure.django_models import BranchModel
                branch = BranchModel.objects.filter(id=register.branch_id).first()
                if branch and branch.establishment:
                    emisor['establecimiento'] = branch.establishment
                if register.emission_point:
                    emisor['punto_emision'] = register.emission_point

            invoice_result = self._billing_service.create_invoice(
                tenant_id=tenant_id,
                customer=active_customer,
                items=sale_items,
                sale_id=sale.id,
                issuer=emisor,
                vat_rate=vat_rate,
                document_type=document_type
            )
            if invoice_result:
                sale.invoice_id = invoice_result.get('invoice_id')
                sale.invoice_number = invoice_result.get('invoice_number')
                self._sale_repo.save(sale)
                
                # Check parameter if it's nota de venta to send to SRI
                send_to_sri = True
                if document_type == '02':
                    from modules.parametros.infrastructure.repository_impl import DjangoParameterRepository
                    param_repo = DjangoParameterRepository()
                    nv_sri_param = param_repo.get(tenant_id, 'pos', 'notas_venta_sri')
                    send_to_sri = nv_sri_param.value.lower() == 'true' if nv_sri_param else False

                if send_to_sri:
                    # Emit invoice to Go SRI signer asynchronously/safely
                    try:
                        self._billing_service.emit_invoice(tenant_id, sale.invoice_id, emisor)
                    except Exception as e:
                        import logging
                        logging.getLogger(__name__).error(f"Error emitiendo factura SRI desde POS: {str(e)}")

        return sale

    def get_register_summary(self, register_id: int, tenant_id: int) -> dict:
        register = self._register_repo.get_by_id(register_id, tenant_id)
        if not register:
            raise ValueError("Register not found")
            
        sales = self._sale_repo.list_by_register(register_id, tenant_id)
        totals = self._sale_repo.get_sales_totals_by_register(register_id)
        
        return {
            'register': register,
            'sales': sales,
            'total_cash': sum(s.total for s in sales if s.payment_method == 'cash'),
            'total_card': sum(s.total for s in sales if s.payment_method == 'card'),
            'total_transfer': sum(s.total for s in sales if s.payment_method == 'transfer'),
            'total_general': totals.get('total', Decimal('0.00')),
            'sales_count': totals.get('cantidad', 0)
        }
