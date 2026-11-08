from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from ..repository_impl import (
    DjangoProveedorRepository,
    DjangoOrdenCompraRepository,
    DjangoFacturaCompraRepository,
    DjangoCuentaPagarRepository,
)
from ...application.use_cases import (
    CreateSupplier, UpdateSupplier, ListSuppliers, DeleteSupplier,
    CreatePurchaseOrder, UpdatePurchaseOrderStatus, ListPurchaseOrders,
    RegisterPurchaseInvoice, ReceivePurchaseInvoiceStock, ListPurchaseInvoices,
    ListAccountsPayable, RegisterPayablePayment, ListPayablePayments,
)


def _check_tenant(request):
    if not getattr(request, 'tenant', None):
        return Response({'error': 'Company not found'}, status=status.HTTP_404_NOT_FOUND)
    return None


# ── PROVEEDORES ──────────────────────────────────────────────

class SuppliersView(APIView):
    def get(self, request):
        if err := _check_tenant(request): return err
        repo = DjangoProveedorRepository()
        query = request.query_params.get('q', None)
        proveedores = ListSuppliers(repo).execute(request.tenant.id, query)
        return Response([
            {
                'id': p.id,
                'identification': p.identification,
                'id_type': p.id_type,
                'business_name': p.business_name,
                'commercial_name': p.commercial_name,
                'email': p.email,
                'phone': p.phone,
                'address': p.address,
                'credit_days': p.credit_days,
                'active': p.active,
                'bank_name': p.bank_name,
                'bank_account_type': p.bank_account_type,
                'bank_account_number': p.bank_account_number,
                'beneficiary_name': p.beneficiary_name,
                'beneficiary_id': p.beneficiary_id,
                'created_at': p.created_at.isoformat() if p.created_at else None,
            }
            for p in proveedores
        ])

    def post(self, request):
        if err := _check_tenant(request): return err
        repo = DjangoProveedorRepository()
        try:
            proveedor = CreateSupplier(repo).execute(request.tenant.id, request.data)
            return Response({'id': proveedor.id, 'business_name': proveedor.business_name}, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SupplierDetailView(APIView):
    def put(self, request, supplier_id):
        if err := _check_tenant(request): return err
        repo = DjangoProveedorRepository()
        try:
            proveedor = UpdateSupplier(repo).execute(request.tenant.id, supplier_id, request.data)
            return Response({'id': proveedor.id, 'business_name': proveedor.business_name})
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, supplier_id):
        if err := _check_tenant(request): return err
        repo = DjangoProveedorRepository()
        success = DeleteSupplier(repo).execute(request.tenant.id, supplier_id)
        if success:
            return Response({'status': 'deleted'})
        return Response({'error': 'Proveedor no encontrado o no se pudo eliminar'}, status=status.HTTP_404_NOT_FOUND)


# ── ÓRDENES DE COMPRA (PO) ───────────────────────────────────

class PurchaseOrdersView(APIView):
    def get(self, request):
        if err := _check_tenant(request): return err
        repo = DjangoOrdenCompraRepository()
        st = request.query_params.get('status', None)
        ordenes = ListPurchaseOrders(repo).execute(request.tenant.id, st)
        return Response([
            {
                'id': o.id,
                'number': o.number,
                'supplier_id': o.supplier_id,
                'supplier_name': o.supplier_name,
                'date': o.date.isoformat(),
                'expected_delivery_date': o.expected_delivery_date.isoformat() if o.expected_delivery_date else None,
                'status': o.status,
                'payment_terms': o.payment_terms,
                'notes': o.notes,
                'subtotal': str(o.subtotal),
                'discount': str(o.discount),
                'vat': str(o.vat),
                'total': str(o.total),
                'branch_id': o.branch_id,
                'items_count': len(o.items),
                'items': [
                    {
                        'id': i.id,
                        'product_id': i.product_id,
                        'description': i.description,
                        'quantity': str(i.quantity),
                        'unit_price': str(i.unit_price),
                        'discount': str(i.discount),
                        'vat_rate': i.vat_rate,
                        'subtotal': str(i.subtotal),
                    }
                    for i in o.items
                ]
            }
            for o in ordenes
        ])

    def post(self, request):
        if err := _check_tenant(request): return err
        order_repo = DjangoOrdenCompraRepository()
        supp_repo = DjangoProveedorRepository()
        try:
            orden = CreatePurchaseOrder(order_repo, supp_repo).execute(request.tenant.id, request.data)
            return Response({'id': orden.id, 'number': orden.number, 'total': str(orden.total)}, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PurchaseOrderDetailView(APIView):
    def get(self, request, order_id):
        if err := _check_tenant(request): return err
        repo = DjangoOrdenCompraRepository()
        o = repo.find_by_id(order_id, request.tenant.id)
        if not o:
            return Response({'error': 'Orden de compra no encontrada'}, status=status.HTTP_404_NOT_FOUND)
        return Response({
            'id': o.id,
            'number': o.number,
            'supplier_id': o.supplier_id,
            'supplier_name': o.supplier_name,
            'date': o.date.isoformat(),
            'expected_delivery_date': o.expected_delivery_date.isoformat() if o.expected_delivery_date else None,
            'status': o.status,
            'payment_terms': o.payment_terms,
            'notes': o.notes,
            'subtotal': str(o.subtotal),
            'discount': str(o.discount),
            'vat': str(o.vat),
            'total': str(o.total),
            'branch_id': o.branch_id,
            'items': [
                {
                    'id': i.id,
                    'product_id': i.product_id,
                    'description': i.description,
                    'quantity': str(i.quantity),
                    'unit_price': str(i.unit_price),
                    'discount': str(i.discount),
                    'vat_rate': i.vat_rate,
                    'subtotal': str(i.subtotal),
                }
                for i in o.items
            ]
        })


class PurchaseOrderStatusView(APIView):
    def post(self, request, order_id):
        if err := _check_tenant(request): return err
        repo = DjangoOrdenCompraRepository()
        new_status = request.data.get('status')
        try:
            orden = UpdatePurchaseOrderStatus(repo).execute(request.tenant.id, order_id, new_status)
            return Response({'id': orden.id, 'status': orden.status})
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ── FACTURAS DE COMPRA ───────────────────────────────────────

class PurchaseInvoicesView(APIView):
    def get(self, request):
        if err := _check_tenant(request): return err
        repo = DjangoFacturaCompraRepository()
        facturas = ListPurchaseInvoices(repo).execute(request.tenant.id)
        return Response([
            {
                'id': f.id,
                'supplier_id': f.supplier_id,
                'supplier_name': f.supplier_name,
                'invoice_number': f.invoice_number,
                'access_key': f.access_key,
                'date': f.date.isoformat(),
                'registration_date': f.registration_date.isoformat(),
                'purchase_type': f.purchase_type,
                'payment_condition': f.payment_condition,
                'credit_days': f.credit_days,
                'due_date': f.due_date.isoformat() if f.due_date else None,
                'status': f.status,
                'reception_status': f.reception_status,
                'subtotal_0': str(f.subtotal_0),
                'subtotal_iva': str(f.subtotal_iva),
                'discount': str(f.discount),
                'vat': str(f.vat),
                'total': str(f.total),
                'branch_id': f.branch_id,
                'purchase_order_id': f.purchase_order_id,
                'items_count': len(f.items),
                'items': [
                    {
                        'id': i.id,
                        'product_id': i.product_id,
                        'description': i.description,
                        'quantity': str(i.quantity),
                        'unit_price': str(i.unit_price),
                        'discount': str(i.discount),
                        'vat_rate': i.vat_rate,
                        'subtotal': str(i.subtotal),
                    }
                    for i in f.items
                ]
            }
            for f in facturas
        ])

    def post(self, request):
        if err := _check_tenant(request): return err
        invoice_repo = DjangoFacturaCompraRepository()
        supp_repo = DjangoProveedorRepository()
        cxp_repo = DjangoCuentaPagarRepository()
        order_repo = DjangoOrdenCompraRepository()
        try:
            factura = RegisterPurchaseInvoice(invoice_repo, supp_repo, cxp_repo, order_repo).execute(request.tenant.id, request.data)
            return Response({
                'id': factura.id,
                'invoice_number': factura.invoice_number,
                'total': str(factura.total),
                'reception_status': factura.reception_status
            }, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PurchaseInvoiceDetailView(APIView):
    def get(self, request, invoice_id):
        if err := _check_tenant(request): return err
        repo = DjangoFacturaCompraRepository()
        f = repo.find_by_id(invoice_id, request.tenant.id)
        if not f:
            return Response({'error': 'Factura de compra no encontrada'}, status=status.HTTP_404_NOT_FOUND)
        return Response({
            'id': f.id,
            'supplier_id': f.supplier_id,
            'supplier_name': f.supplier_name,
            'invoice_number': f.invoice_number,
            'access_key': f.access_key,
            'date': f.date.isoformat(),
            'registration_date': f.registration_date.isoformat(),
            'purchase_type': f.purchase_type,
            'payment_condition': f.payment_condition,
            'credit_days': f.credit_days,
            'due_date': f.due_date.isoformat() if f.due_date else None,
            'status': f.status,
            'reception_status': f.reception_status,
            'subtotal_0': str(f.subtotal_0),
            'subtotal_iva': str(f.subtotal_iva),
            'discount': str(f.discount),
            'vat': str(f.vat),
            'total': str(f.total),
            'items': [
                {
                    'id': i.id,
                    'product_id': i.product_id,
                    'description': i.description,
                    'quantity': str(i.quantity),
                    'unit_price': str(i.unit_price),
                    'discount': str(i.discount),
                    'vat_rate': i.vat_rate,
                    'subtotal': str(i.subtotal),
                }
                for i in f.items
            ]
        })


class PurchaseInvoiceReceiveStockView(APIView):
    """
    Acción explícita para ingresar mercadería físicamente al inventario
    y recalcular el Kardex.
    """
    def post(self, request, invoice_id):
        if err := _check_tenant(request): return err
        repo = DjangoFacturaCompraRepository()
        user_id = getattr(request.user, 'id', 0) if hasattr(request, 'user') else 0
        try:
            factura = ReceivePurchaseInvoiceStock(repo).execute(request.tenant.id, invoice_id, user_id)
            return Response({
                'status': 'success',
                'message': 'Mercadería ingresada exitosamente al inventario y Kardex recalculado',
                'reception_status': factura.reception_status
            })
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ── CUENTAS POR PAGAR (CXP) ──────────────────────────────────

class AccountsPayableView(APIView):
    def get(self, request):
        if err := _check_tenant(request): return err
        repo = DjangoCuentaPagarRepository()
        st = request.query_params.get('status', None)
        cuentas = ListAccountsPayable(repo).execute(request.tenant.id, st)
        return Response([
            {
                'id': c.id,
                'supplier_id': c.supplier_id,
                'supplier_name': c.supplier_name,
                'invoice_id': c.invoice_id,
                'invoice_number': c.invoice_number,
                'total_amount': str(c.total_amount),
                'balance_due': str(c.balance_due),
                'due_date': c.due_date.isoformat() if c.due_date else None,
                'status': c.status,
                'created_at': c.created_at.isoformat() if c.created_at else None,
            }
            for c in cuentas
        ])


class AccountPayablePaymentView(APIView):
    def get(self, request, account_payable_id):
        if err := _check_tenant(request): return err
        repo = DjangoCuentaPagarRepository()
        abonos = ListPayablePayments(repo).execute(request.tenant.id, account_payable_id)
        return Response([
            {
                'id': a.id,
                'account_payable_id': a.account_payable_id,
                'amount': str(a.amount),
                'payment_date': a.payment_date.isoformat(),
                'payment_method': a.payment_method,
                'reference': a.reference,
                'notes': a.notes,
                'created_at': a.created_at.isoformat() if a.created_at else None,
            }
            for a in abonos
        ])

    def post(self, request, account_payable_id):
        if err := _check_tenant(request): return err
        repo = DjangoCuentaPagarRepository()
        try:
            abono = RegisterPayablePayment(repo).execute(request.tenant.id, account_payable_id, request.data)
            return Response({
                'id': abono.id,
                'amount': str(abono.amount),
                'message': 'Abono registrado exitosamente'
            }, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
