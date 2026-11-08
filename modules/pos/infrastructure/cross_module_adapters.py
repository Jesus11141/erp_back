from decimal import Decimal
from typing import Optional, List
from modules.pos.domain.repositories import (
    POSDependencyRepository, POSInventoryService, 
    POSBillingService, POSAccountingService
)
from modules.pos.domain.entities import POSCustomer, POSSaleItem, POSSale

class DjangoPOSDependencyRepository(POSDependencyRepository):
    def has_active_employees(self, tenant_id: int) -> bool:
        from modules.rrhh.infrastructure.django_models import EmployeeModel
        return EmployeeModel.objects.filter(tenant_id=tenant_id, active=True).exists()

    def ensure_customer_exists(self, tenant_id: int, customer: POSCustomer) -> None:
        from modules.ventas.infrastructure.django_models import CustomerModel
        if customer.identifier != '9999999999999' and customer.name != '':
            cli_db = CustomerModel.objects.filter(tenant_id=tenant_id, rfc=customer.identifier).first()
            if not cli_db:
                CustomerModel.objects.create(
                    tenant_id=tenant_id,
                    name=customer.name,
                    rfc=customer.identifier,
                    email=customer.email,
                    active=True
                )


class DjangoPOSInventoryService(POSInventoryService):
    def get_stock_available(self, tenant_id: int, product_id: int, branch_id: Optional[int] = None) -> Decimal:
        from modules.inventario.infrastructure.repository_impl import DjangoProductRepository
        prod = DjangoProductRepository().find_by_id(product_id, tenant_id)
        general_stock = prod.current_stock if prod else Decimal('0.00')

        if branch_id:
            from modules.inventario.infrastructure.repository_impl import DjangoBranchStockRepository
            branch_stock = DjangoBranchStockRepository().get_stock(tenant_id, product_id, branch_id)
            if branch_stock > Decimal('0.00'):
                return branch_stock
            return general_stock
        return general_stock

    def get_product_details(self, tenant_id: int, product_id: int) -> dict:
        from modules.inventario.infrastructure.repository_impl import DjangoProductRepository
        prod = DjangoProductRepository().find_by_id(product_id, tenant_id)
        if prod:
            return {'name': prod.name, 'unit': prod.unit}
        return {'name': f"Product #{product_id}", 'unit': ''}

    def adjust_stock(self, tenant_id: int, product_id: int, quantity: Decimal, type: str, reference: str, user_id: int, branch_id: Optional[int] = None) -> None:
        from modules.inventario.infrastructure.repository_impl import DjangoProductRepository, DjangoStockMovementRepository
        prod_repo = DjangoProductRepository()
        mov_repo = DjangoStockMovementRepository()

        if branch_id:
            from modules.inventario.infrastructure.repository_impl import DjangoBranchStockRepository
            branch_repo = DjangoBranchStockRepository()
            branch_stock = branch_repo.get_stock(tenant_id, product_id, branch_id)
            if branch_stock > Decimal('0.00'):
                from modules.inventario.application.use_cases import AdjustBranchStock
                AdjustBranchStock(branch_repo, prod_repo, mov_repo).execute(
                    tenant_id=tenant_id,
                    product_id=product_id,
                    branch_id=branch_id,
                    quantity=quantity,
                    type=type,
                    reference=reference,
                    user_id=user_id,
                    allow_negative=True
                )
                return
        from modules.inventario.application.use_cases import AdjustStock
        AdjustStock(prod_repo, mov_repo).execute(
            tenant_id=tenant_id,
            product_id=product_id,
            quantity=quantity,
            type=type,
            reference=reference,
            user_id=user_id
        )


class DjangoPOSBillingService(POSBillingService):
    def __init__(self, invoice_repo=None):
        self._invoice_repo = invoice_repo

    def get_issuer(self, tenant_id: int) -> dict:
        from modules.tax_documents.invoicing.infrastructure.ui.views import _get_emisor
        return _get_emisor(tenant_id)

    def create_invoice(self, tenant_id: int, customer: POSCustomer, items: List[POSSaleItem], sale_id: int, issuer: dict, vat_rate: Decimal, document_type: str = '01') -> dict:
        from modules.tax_documents.invoicing.application.create_service import CreateInvoice
        vat_pct = int(vat_rate * 100)
        invoice_data = {
            'client': customer.name,
            'client_identification': customer.identifier,
            'client_address': customer.address,
            'client_email': customer.email,
            'client_id_type': customer.id_type,
            'payment_method': customer.payment_form,
            'notes': f'Venta POS #{sale_id}',
            'items': [
                {
                    'description': i.description,
                    'quantity': float(i.quantity),
                    'unit_price': float(i.unit_price),
                    'discount': float(i.discount),
                    'main_code': i.code,
                    'vat_rate': '15'
                } for i in items
            ]
        }
        
        factura = CreateInvoice(self._invoice_repo).execute(
            tenant_id=tenant_id,
            data=invoice_data,
            issuer=issuer,
            vat=vat_pct,
            document_type=document_type
        )
        return {
            'invoice_id': factura.id,
            'invoice_number': factura.number,
            'access_key': getattr(factura, 'access_key', '')
        }

    def emit_invoice(self, tenant_id: int, invoice_id: int, issuer: dict) -> None:
        from modules.tax_documents.invoicing.application.emit_invoice_sri import EmitInvoiceSRI
        EmitInvoiceSRI(self._invoice_repo).execute(tenant_id, invoice_id, issuer)


class DjangoPOSAccountingService(POSAccountingService):
    def __init__(self, contabilidad_repo=None):
        self._contabilidad_repo = contabilidad_repo

    def register_sale_entry(self, tenant_id: int, sale: POSSale) -> None:
        from modules.contabilidad.application.accounting_service import AccountingService
        from modules.contabilidad.domain.value_objects import AccountData, AccountType, AccountCode

        reference = f"venta_pos_{sale.id}"
        if self._contabilidad_repo.entry_exists(tenant_id, reference):
            return

        service = AccountingService(self._contabilidad_repo)

        cash_account = service.get_or_create_account(AccountData(
            tenant_id=tenant_id,
            code=AccountCode('1.1.01.01'),
            name='Caja y Bancos',
            type=AccountType.ASSET
        ))
        revenue_account = service.get_or_create_account(AccountData(
            tenant_id=tenant_id,
            code=AccountCode('4.1.01.01'),
            name='Ingresos por Ventas',
            type=AccountType.REVENUE
        ))
        tax_account = service.get_or_create_account(AccountData(
            tenant_id=tenant_id,
            code=AccountCode('2.1.03.01'),
            name='IVA por Pagar',
            type=AccountType.LIABILITY
        ))
        from modules.inventario.infrastructure.django_models import KardexModel
        from django.db.models import Sum

        kardex_sum = KardexModel.objects.filter(
            tenant_id=tenant_id, 
            detail=reference
        ).aggregate(total_cost=Sum('exit_total_cost'))
        
        total_cost = kardex_sum['total_cost'] or Decimal('0.00')

        lines = [
            {'account_id': cash_account.id,    'debit': sale.total,       'credit': Decimal('0.00')},
            {'account_id': revenue_account.id, 'debit': Decimal('0.00'),   'credit': sale.subtotal},
            {'account_id': tax_account.id,     'debit': Decimal('0.00'),   'credit': sale.vat_amount}
        ]

        if total_cost > Decimal('0.00'):
            cogs_account = service.get_or_create_account(AccountData(
                tenant_id=tenant_id,
                code=AccountCode('5.1.01.01'),
                name='Cost of Goods Sold',
                type=AccountType.EXPENSE
            ))
            inv_account = service.get_or_create_account(AccountData(
                tenant_id=tenant_id,
                code=AccountCode('1.1.03.01'),
                name='Inventory',
                type=AccountType.ASSET
            ))
            lines.append({'account_id': cogs_account.id, 'debit': total_cost, 'credit': Decimal('0.00')})
            lines.append({'account_id': inv_account.id,  'debit': Decimal('0.00'), 'credit': total_cost})

        service.create_journal_entry(
            tenant_id=tenant_id,
            description=f"POS Sale #{sale.id}",
            lines=lines,
            reference=reference
        )
