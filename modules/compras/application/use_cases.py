from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional

from ..domain.entities import (
    Proveedor, OrdenCompra, OrdenCompraItem,
    FacturaCompra, FacturaCompraItem,
    CuentaPagar, AbonoCuentaPagar
)
from ..domain.repositories import (
    ProveedorRepository, OrdenCompraRepository,
    FacturaCompraRepository, CuentaPagarRepository
)


# ── PROVEEDORES ──────────────────────────────────────────────

class CreateSupplier:
    def __init__(self, repo: ProveedorRepository):
        self.repo = repo

    def execute(self, tenant_id: int, data: dict) -> Proveedor:
        identification = data.get('identification', '').strip()
        business_name = data.get('business_name', '').strip()

        if not identification or not business_name:
            raise ValueError("Identificación (RUC/Cédula) y Razón Social son requeridos.")

        existing = self.repo.find_by_identification(identification, tenant_id)
        if existing:
            raise ValueError(f"Ya existe un proveedor con identificación {identification}.")

        proveedor = Proveedor(
            id=0,
            tenant_id=tenant_id,
            identification=identification,
            id_type=data.get('id_type', '04'),
            business_name=business_name,
            commercial_name=data.get('commercial_name', '').strip(),
            email=data.get('email', '').strip(),
            phone=data.get('phone', '').strip(),
            address=data.get('address', '').strip(),
            credit_days=int(data.get('credit_days', 0)),
            active=data.get('active', True),
            bank_name=data.get('bank_name', '').strip(),
            bank_account_type=data.get('bank_account_type', 'AHO').strip(),
            bank_account_number=data.get('bank_account_number', '').strip(),
            beneficiary_name=data.get('beneficiary_name', '').strip(),
            beneficiary_id=data.get('beneficiary_id', '').strip(),
        )
        return self.repo.save(proveedor)


class UpdateSupplier:
    def __init__(self, repo: ProveedorRepository):
        self.repo = repo

    def execute(self, tenant_id: int, supplier_id: int, data: dict) -> Proveedor:
        proveedor = self.repo.find_by_id(supplier_id, tenant_id)
        if not proveedor:
            raise ValueError("Proveedor no encontrado.")

        proveedor.business_name = data.get('business_name', proveedor.business_name).strip()
        proveedor.commercial_name = data.get('commercial_name', proveedor.commercial_name).strip()
        proveedor.email = data.get('email', proveedor.email).strip()
        proveedor.phone = data.get('phone', proveedor.phone).strip()
        proveedor.address = data.get('address', proveedor.address).strip()
        proveedor.credit_days = int(data.get('credit_days', proveedor.credit_days))
        proveedor.active = data.get('active', proveedor.active)
        proveedor.bank_name = data.get('bank_name', proveedor.bank_name).strip()
        proveedor.bank_account_type = data.get('bank_account_type', proveedor.bank_account_type).strip()
        proveedor.bank_account_number = data.get('bank_account_number', proveedor.bank_account_number).strip()
        proveedor.beneficiary_name = data.get('beneficiary_name', proveedor.beneficiary_name).strip()
        proveedor.beneficiary_id = data.get('beneficiary_id', proveedor.beneficiary_id).strip()
        return self.repo.save(proveedor)


class ListSuppliers:
    def __init__(self, repo: ProveedorRepository):
        self.repo = repo

    def execute(self, tenant_id: int, query: str = None) -> List[Proveedor]:
        return self.repo.list(tenant_id, query)


class DeleteSupplier:
    def __init__(self, repo: ProveedorRepository):
        self.repo = repo

    def execute(self, tenant_id: int, supplier_id: int) -> bool:
        return self.repo.delete(supplier_id, tenant_id)


# ── ÓRDENES DE COMPRA (PO) ───────────────────────────────────

class CreatePurchaseOrder:
    def __init__(self, repo: OrdenCompraRepository, supplier_repo: ProveedorRepository):
        self.repo = repo
        self.supplier_repo = supplier_repo

    def execute(self, tenant_id: int, data: dict) -> OrdenCompra:
        supplier_id = data.get('supplier_id')
        supplier = self.supplier_repo.find_by_id(supplier_id, tenant_id)
        if not supplier:
            raise ValueError("Proveedor no válido o no encontrado.")

        raw_items = data.get('items', [])
        if not raw_items:
            raise ValueError("La orden de compra debe contener al menos un ítem.")

        # Generar número correlativo
        from ..infrastructure.django_models import OrdenCompraModel
        count = OrdenCompraModel.objects.filter(tenant_id=tenant_id).count() + 1
        number = f"OC-{count:05d}"

        subtotal_gen = Decimal('0.00')
        discount_gen = Decimal('0.00')
        vat_gen = Decimal('0.00')
        items = []

        for item_data in raw_items:
            qty = Decimal(str(item_data.get('quantity', 1)))
            price = Decimal(str(item_data.get('unit_price', 0)))
            disc = Decimal(str(item_data.get('discount', 0)))
            vat_rate_str = str(item_data.get('vat_rate', '15'))
            vat_pct = Decimal(vat_rate_str) / Decimal('100')

            base = (qty * price) - disc
            vat_val = round(base * vat_pct, 2)
            subtotal_item = base

            subtotal_gen += (qty * price)
            discount_gen += disc
            vat_gen += vat_val

            items.append(OrdenCompraItem(
                id=0,
                product_id=item_data.get('product_id'),
                description=item_data.get('description', '').strip(),
                quantity=qty,
                unit_price=price,
                discount=disc,
                vat_rate=vat_rate_str,
                subtotal=subtotal_item,
            ))

        total_gen = subtotal_gen - discount_gen + vat_gen

        orden = OrdenCompra(
            id=0,
            tenant_id=tenant_id,
            number=number,
            supplier_id=supplier.id,
            supplier_name=supplier.business_name,
            date=date.today(),
            expected_delivery_date=data.get('expected_delivery_date'),
            status='borrador',
            payment_terms=data.get('payment_terms', f"Crédito {supplier.credit_days} días" if supplier.credit_days > 0 else "Contado"),
            notes=data.get('notes', ''),
            subtotal=subtotal_gen,
            discount=discount_gen,
            vat=vat_gen,
            total=total_gen,
            branch_id=data.get('branch_id'),
            items=items,
        )
        return self.repo.save(orden)


class UpdatePurchaseOrderStatus:
    def __init__(self, repo: OrdenCompraRepository):
        self.repo = repo

    def execute(self, tenant_id: int, order_id: int, new_status: str) -> OrdenCompra:
        orden = self.repo.find_by_id(order_id, tenant_id)
        if not orden:
            raise ValueError("Orden de compra no encontrada.")

        valid_transitions = {
            'borrador': ['solicitada', 'cancelada'],
            'solicitada': ['aprobada', 'cancelada', 'borrador'],
            'aprobada': ['recibida', 'cancelada'],
            'recibida': [],
            'cancelada': [],
        }

        if new_status not in valid_transitions.get(orden.status, []):
            raise ValueError(f"No se puede cambiar el estado de '{orden.status}' a '{new_status}'.")

        orden.status = new_status
        return self.repo.save(orden)


class ListPurchaseOrders:
    def __init__(self, repo: OrdenCompraRepository):
        self.repo = repo

    def execute(self, tenant_id: int, status: str = None) -> List[OrdenCompra]:
        return self.repo.list(tenant_id, status)


# ── FACTURAS DE COMPRA ───────────────────────────────────────

class RegisterPurchaseInvoice:
    def __init__(
        self,
        invoice_repo: FacturaCompraRepository,
        supplier_repo: ProveedorRepository,
        cxp_repo: CuentaPagarRepository,
        order_repo: Optional[OrdenCompraRepository] = None,
    ):
        self.invoice_repo = invoice_repo
        self.supplier_repo = supplier_repo
        self.cxp_repo = cxp_repo
        self.order_repo = order_repo

    def execute(self, tenant_id: int, data: dict) -> FacturaCompra:
        supplier_id = data.get('supplier_id')
        supplier = self.supplier_repo.find_by_id(supplier_id, tenant_id)
        if not supplier:
            raise ValueError("Proveedor no válido o no encontrado.")

        invoice_number = data.get('invoice_number', '').strip()
        if not invoice_number:
            raise ValueError("El número de factura física/electrónica es requerido.")

        raw_items = data.get('items', [])
        if not raw_items:
            raise ValueError("La factura de compra debe contener al menos un ítem.")

        purchase_type = data.get('purchase_type', 'inventario')
        payment_condition = data.get('payment_condition', 'contado')
        credit_days = int(data.get('credit_days') or supplier.credit_days)

        # Cálculo de fechas
        date_emission = data.get('date') or date.today()
        if isinstance(date_emission, str):
            date_emission = date.fromisoformat(date_emission[:10])

        # Control de Período Contable / Cierre Fiscal
        from modules.contabilidad.application.period_service import validate_accounting_period
        validate_accounting_period(tenant_id, date_emission, action_desc='registrar facturas de compra')

        due_date = None
        if payment_condition == 'credito':
            due_date = date_emission + timedelta(days=max(credit_days, 1))

        # Estado de recepción según tipo: si es inventario queda pendiente; si es gasto no aplica
        reception_status = 'pendiente' if purchase_type == 'inventario' else 'no_aplica'

        subtotal_0 = Decimal('0.00')
        subtotal_iva = Decimal('0.00')
        discount_gen = Decimal('0.00')
        vat_gen = Decimal('0.00')
        items = []

        for item_data in raw_items:
            qty = Decimal(str(item_data.get('quantity', 1)))
            price = Decimal(str(item_data.get('unit_price', 0)))
            disc = Decimal(str(item_data.get('discount', 0)))
            vat_rate_str = str(item_data.get('vat_rate', '15'))
            vat_pct = Decimal(vat_rate_str) / Decimal('100')

            base = (qty * price) - disc
            vat_val = round(base * vat_pct, 2)

            if vat_pct == Decimal('0.00'):
                subtotal_0 += base
            else:
                subtotal_iva += base

            discount_gen += disc
            vat_gen += vat_val

            items.append(FacturaCompraItem(
                id=0,
                product_id=item_data.get('product_id'),
                description=item_data.get('description', '').strip(),
                quantity=qty,
                unit_price=price,
                discount=disc,
                vat_rate=vat_rate_str,
                subtotal=base,
            ))

        total_gen = subtotal_0 + subtotal_iva + vat_gen

        # Guardar Factura de Compra
        factura = FacturaCompra(
            id=0,
            tenant_id=tenant_id,
            supplier_id=supplier.id,
            supplier_name=supplier.business_name,
            invoice_number=invoice_number,
            access_key=data.get('access_key', '').strip(),
            date=date_emission,
            registration_date=date.today(),
            purchase_type=purchase_type,
            payment_condition=payment_condition,
            credit_days=credit_days,
            due_date=due_date,
            status='registrada',
            reception_status=reception_status,
            subtotal_0=subtotal_0,
            subtotal_iva=subtotal_iva,
            discount=discount_gen,
            vat=vat_gen,
            total=total_gen,
            branch_id=data.get('branch_id'),
            purchase_order_id=data.get('purchase_order_id'),
            items=items,
        )
        saved_factura = self.invoice_repo.save(factura)

        # Si fue a crédito -> Generar Cuenta por Pagar
        if payment_condition == 'credito':
            cxp = CuentaPagar(
                id=0,
                tenant_id=tenant_id,
                supplier_id=supplier.id,
                supplier_name=supplier.business_name,
                invoice_id=saved_factura.id,
                invoice_number=invoice_number,
                total_amount=total_gen,
                balance_due=total_gen,
                due_date=due_date,
                status='PENDING',
            )
            self.cxp_repo.save(cxp)

        # Si se vinculó una orden de compra, actualizarla a recibida
        if data.get('purchase_order_id') and self.order_repo:
            po = self.order_repo.find_by_id(data['purchase_order_id'], tenant_id)
            if po and po.status in ('solicitada', 'aprobada'):
                po.status = 'recibida'
                self.order_repo.save(po)

        return saved_factura


class ReceivePurchaseInvoiceStock:
    """
    Acción explícita del bodeguero para ingresar la mercadería físicamente.
    Suma el stock en ProductModel/BranchStock y recalcula el Kardex (CPP).
    """
    def __init__(self, invoice_repo: FacturaCompraRepository):
        self.invoice_repo = invoice_repo

    def execute(self, tenant_id: int, invoice_id: int, user_id: int = 0) -> FacturaCompra:
        factura = self.invoice_repo.find_by_id(invoice_id, tenant_id)
        if not factura:
            raise ValueError("Factura de compra no encontrada.")

        if factura.purchase_type != 'inventario':
            raise ValueError("Esta factura es de tipo Gasto Operativo y no afecta stock.")

        if factura.reception_status == 'recibida':
            raise ValueError("La mercadería de esta factura ya fue recepcionada previamente.")

        from modules.inventario.infrastructure.django_models import ProductModel, StockMovementModel, BranchStockModel
        from modules.inventario.infrastructure.repository_impl import DjangoProductRepository, DjangoStockMovementRepository, DjangoKardexRepository
        from modules.inventario.application.adjust_stock import AdjustStock

        prod_repo = DjangoProductRepository()
        mov_repo = DjangoStockMovementRepository()
        kardex_repo = DjangoKardexRepository()
        adjuster = AdjustStock(prod_repo, mov_repo, kardex_repo)

        for item in factura.items:
            if not item.product_id:
                continue

            ref_text = f"Factura Compra {factura.invoice_number} ({factura.supplier_name})"

            # Ajuste de stock y cálculo de Kardex CPP
            adjuster.execute(
                tenant_id=tenant_id,
                product_id=item.product_id,
                quantity=item.quantity,
                type='in',
                reference=ref_text,
                user_id=user_id
            )

            # Actualizar costo de compra directo en la ficha del producto
            prod = ProductModel.objects.filter(id=item.product_id, tenant_id=tenant_id).first()
            if prod:
                prod.purchase_price = item.unit_price
                prod.save()

            # Si hay sucursal específica, incrementar el stock de la sucursal
            if factura.branch_id:
                bs, _ = BranchStockModel.objects.get_or_create(
                    tenant_id=tenant_id,
                    product_id=item.product_id,
                    branch_id=factura.branch_id,
                    defaults={'current_stock': Decimal('0.00')}
                )
                bs.current_stock += item.quantity
                bs.save()

        factura.reception_status = 'recibida'
        return self.invoice_repo.save(factura)


class ListPurchaseInvoices:
    def __init__(self, repo: FacturaCompraRepository):
        self.repo = repo

    def execute(self, tenant_id: int) -> List[FacturaCompra]:
        return self.repo.list(tenant_id)


# ── CUENTAS POR PAGAR (CXP) ──────────────────────────────────

class ListAccountsPayable:
    def __init__(self, repo: CuentaPagarRepository):
        self.repo = repo

    def execute(self, tenant_id: int, status: str = None) -> List[CuentaPagar]:
        return self.repo.list(tenant_id, status)


class RegisterPayablePayment:
    def __init__(self, repo: CuentaPagarRepository):
        self.repo = repo

    def execute(self, tenant_id: int, account_payable_id: int, data: dict) -> AbonoCuentaPagar:
        cxp = self.repo.find_by_id(account_payable_id, tenant_id)
        if not cxp:
            raise ValueError("Cuenta por pagar no encontrada.")

        amount = Decimal(str(data.get('amount', 0)))
        if amount <= Decimal('0.00'):
            raise ValueError("El monto del abono debe ser mayor a 0.")

        if amount > cxp.balance_due:
            raise ValueError(f"El monto (${amount}) excede el saldo pendiente (${cxp.balance_due}).")

        payment_date = data.get('payment_date') or date.today()
        # Control de Período Contable / Cierre Fiscal
        from modules.contabilidad.application.period_service import validate_accounting_period
        validate_accounting_period(tenant_id, payment_date, action_desc='registrar abonos a cuentas por pagar')

        abono = AbonoCuentaPagar(
            id=0,
            tenant_id=tenant_id,
            account_payable_id=cxp.id,
            amount=amount,
            payment_date=payment_date,
            payment_method=data.get('payment_method', 'transferencia'),
            reference=data.get('reference', '').strip(),
            notes=data.get('notes', '').strip(),
        )
        return self.repo.add_payment(abono)


class ListPayablePayments:
    def __init__(self, repo: CuentaPagarRepository):
        self.repo = repo

    def execute(self, tenant_id: int, account_payable_id: int) -> List[AbonoCuentaPagar]:
        return self.repo.list_payments(account_payable_id, tenant_id)
