from decimal import Decimal
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ...infrastructure.repository_impl import DjangoCashRegisterRepository, DjangoPOSSaleRepository
from ...application.pos_service import POSService
from ...domain.entities import POSCustomer
from modules.parametros.infrastructure.repository_impl import DjangoParameterRepository
from modules.shared.role_permissions import admin_only

def verificar_modulo(request):
    if not request.tenant or not request.tenant.has_module('pos'):
        return Response({'error': 'Module not available'}, status=status.HTTP_403_FORBIDDEN)

def _register_dict(c):
    return {
        'id': c.id,
        'name': c.name,
        'status': c.status,
        'initial_balance': str(c.initial_balance),
        'final_balance': str(c.final_balance) if c.final_balance is not None else None,
        'opened_at': c.opened_at,
        'closed_at': c.closed_at,
        'difference': str(c.final_balance - c.initial_balance) if c.final_balance is not None else None,
        'opening_breakdown': c.opening_breakdown,
        'branch_id': c.branch_id,
        'emission_point': getattr(c, 'emission_point', '001'),
        'user_id': getattr(c, 'user_id', None)
    }

def _get_pos_service(request):
    from modules.contabilidad.infrastructure.repository_impl import DjangoAccountingRepository
    from modules.tax_documents.invoicing.infrastructure.persistence.repository_impl import DjangoInvoiceRepository
    from ...infrastructure.cross_module_adapters import (
        DjangoPOSInventoryService, DjangoPOSBillingService, DjangoPOSAccountingService,
        DjangoPOSDependencyRepository as CrossModuleDepRepo
    )
    return POSService(
        register_repo=DjangoCashRegisterRepository(),
        sale_repo=DjangoPOSSaleRepository(),
        dep_repo=CrossModuleDepRepo(),
        param_repo=DjangoParameterRepository(),
        inventory_service=DjangoPOSInventoryService(),
        billing_service=DjangoPOSBillingService(DjangoInvoiceRepository()),
        accounting_service=DjangoPOSAccountingService(DjangoAccountingRepository()),
    )

class VerifyPinView(APIView):
    def post(self, request):
        if e := verificar_modulo(request): return e
        from modules.rrhh.infrastructure.django_models import EmployeeModel
        cashier_id = request.data.get('cajero_id')
        pin_caja = request.data.get('pin_caja')
        if not cashier_id or not pin_caja:
            return Response({'error': 'Faltan credenciales'}, status=status.HTTP_400_BAD_REQUEST)
        emp = EmployeeModel.objects.filter(id=cashier_id, tenant_id=request.tenant.id).first()
        if not emp:
            return Response({'error': 'No se encontró al trabajador'}, status=status.HTTP_400_BAD_REQUEST)
        if str(emp.pin_caja).strip() != str(pin_caja).strip():
            return Response({'error': 'El PIN secreto es incorrecto'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'success': True, 'id': emp.id, 'name': emp.name, 'tenant_id': emp.tenant_id, 'status': 'seller_session'})

class CashRegisterView(APIView):
    def get(self, request):
        if e := verificar_modulo(request): return e
        from ...infrastructure.django_models import CashRegisterModel
        cajas_models = CashRegisterModel.objects.filter(tenant_id=request.tenant.id).order_by('-opened_at')
        cajas_entities = [DjangoCashRegisterRepository()._to_entity(c) for c in cajas_models]
        return Response([_register_dict(c) for c in cajas_entities])

    def post(self, request):
        if e := verificar_modulo(request): return e
        cashier_id = request.data.get('cashier_id') or request.data.get('cajero_id')
        cashier_pin = request.data.get('cashier_pin') or request.data.get('pin_caja', '')
        from modules.rrhh.infrastructure.django_models import EmployeeModel
        from modules.auth.infrastructure.django_models import UserModel
        
        if cashier_id:
            emp = EmployeeModel.objects.filter(id=cashier_id, tenant_id=request.tenant.id).first()
        else:
            if not cashier_pin:
                return Response({'error': 'You must enter a valid cashier PIN to open the register'}, status=status.HTTP_400_BAD_REQUEST)
            emp = EmployeeModel.objects.filter(pin_caja=cashier_pin, tenant_id=request.tenant.id).first()
            
        if not emp:
            return Response({'error': 'Incorrect PIN or cashier not found'}, status=status.HTTP_400_BAD_REQUEST)
            
        if str(emp.pin_caja).strip() != str(cashier_pin).strip():
            return Response({'error': 'The selected cashier PIN is incorrect'}, status=status.HTTP_400_BAD_REQUEST)
            
        cashier_id = emp.id
        
        # (Removida validación de UserModel ya que en un POS los empleados solo usan su PIN)

        try:
            service = _get_pos_service(request)
            register = service.open_register(
                tenant_id=request.tenant.id,
                user_id=cashier_id,
                name=request.data.get('name', ''),
                initial_balance=Decimal(str(request.data.get('saldo_inicial', '0'))),
                opening_breakdown=request.data.get('desglose_monedas'),
                branch_id=request.data.get('sucursal_id')
            )
            return Response(_register_dict(register), status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class PendingOrdersView(APIView):
    def get(self, request):
        if e := verificar_modulo(request): return e
        from modules.ventas.infrastructure.repository_impl import DjangoQuotationRepository
        repos = DjangoQuotationRepository()
        quotations = repos.list_by_tenant(request.tenant.id)
        
        sucursal_id = request.query_params.get('sucursal_id')
        
        # Fetching draft (Pre-Facturas)
        pending = [q for q in quotations if q.status in ('draft', 'sent') and q.is_preinvoice]
        if sucursal_id:
            pending = [q for q in pending if str(q.branch_id) == str(sucursal_id) or q.branch_id is None]
        
        
        return Response([{
            'id': q.id,
            'customer_name': q.customer_name,
            'date': q.date,
            'total': str(q.total),
            'status': q.status
        } for q in pending])

class POSQuotationsView(APIView):
    def get(self, request):
        if e := verificar_modulo(request): return e
        from modules.ventas.infrastructure.repository_impl import DjangoQuotationRepository
        repos = DjangoQuotationRepository()
        quotations = repos.list_by_tenant(request.tenant.id)
        # Fetching true quotations
        pending = [q for q in quotations if q.status in ('draft', 'sent') and not q.is_preinvoice]
        
        return Response([{
            'id': q.id,
            'customer_name': q.customer_name,
            'date': q.date,
            'total': str(q.total),
            'status': q.status
        } for q in pending])

class CashRegisterActionView(APIView):
    def post(self, request, register_id, action):
        if e := verificar_modulo(request): return e
        try:
            service = _get_pos_service(request)
            if action == 'close':
                result = service.close_register(
                    register_id=register_id,
                    tenant_id=request.tenant.id,
                    final_balance=Decimal(str(request.data.get('final_balance', 0))) if request.data.get('final_balance') is not None else Decimal('0'),
                    observations=request.data.get('observations', ''),
                    closure_breakdown=request.data.get('closing_breakdown'),
                )
                return Response({
                    'register':            _register_dict(result['register']),
                    'sales_count':         result['sales_count'],
                    'total_cash':          str(result['total_cash']),
                    'total_card':          str(result['total_card']),
                    'total_transfer':      str(result['total_transfer']),
                    'total_sales':         str(result['total_sales']),
                    'initial_balance':     str(result['initial_balance']),
                    'expected_balance':    str(result['expected_balance']),
                    'final_balance':       str(result['final_balance']),
                    'difference':          str(result['difference']),
                })
            elif action == 'summary':
                result = service.get_register_summary(register_id, request.tenant.id)
                return Response({
                    'register': _register_dict(result['register']),
                    'sales_count': result['sales_count'],
                    'total_cash': str(result['total_cash']),
                    'total_card': str(result['total_card']),
                    'total_transfer': str(result['total_transfer']),
                    'total_general': str(result['total_general']),
                })
            return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CashRegisterClosureView(APIView):
    """Historial de cierres para auditorÃ­a."""
    def get(self, request):
        if e := verificar_modulo(request): return e
        from ...infrastructure.django_models import CashRegisterClosureModel
        closures = CashRegisterClosureModel.objects.filter(tenant_id=request.tenant.id).order_by('-closed_at')
        
        # Resolviendo nombres de cajeros desde RRHH
        cajeros = {}
        try:
            from modules.rrhh.infrastructure.django_models import EmployeeModel
            for emp in EmployeeModel.objects.filter(tenant_id=request.tenant.id):
                cajeros[emp.id] = emp.name
        except Exception:
            pass

        return Response([{
            'id':                  c.id,
            'register_name':       c.register.name,
            'cashier_name':        cajeros.get(c.user_id, f"Cashier #{c.user_id}"),
            'opened_at':           c.opened_at,
            'closed_at':           c.closed_at,
            'sales_count':         c.sales_count,
            'total_cash':          str(c.total_cash),
            'total_card':          str(c.total_card),
            'total_transfer':      str(c.total_transfer),
            'initial_balance':     str(c.initial_balance),
            'expected_balance':    str(c.expected_balance),
            'counted_balance':     str(c.counted_balance),
            'difference':          str(c.difference),
            'difference_status':   'OK' if c.difference == 0 else ('SURPLUS' if c.difference > 0 else 'SHORTAGE'),
            'observations':       c.observations,
            'closure_breakdown':   c.closure_breakdown,
        } for c in closures])


class POSSaleView(APIView):
    def get(self, request, register_id):
        if e := verificar_modulo(request): return e
        ventas = DjangoPOSSaleRepository().list_by_register(register_id, request.tenant.id)
        
        invoice_ids = [v.invoice_id for v in ventas if getattr(v, 'invoice_id', None)]
        invoices_map = {}
        if invoice_ids:
            try:
                from modules.tax_documents.invoicing.infrastructure.django_models import InvoiceModel
                invoices_qs = InvoiceModel.objects.filter(id__in=invoice_ids, tenant_id=request.tenant.id).values('id', 'number', 'access_key')
                invoices_map = {inv['id']: inv for inv in invoices_qs}
            except Exception:
                pass

        return Response([{
            'id': v.id,
            'created_at': v.created_at,
            'payment_method': v.payment_method,
            'total': str(v.total),
            'subtotal': str(v.subtotal),
            'tax': str(getattr(v, 'vat_amount', '0.00')),
            'change': str(v.change),
            'status': v.status,
            'customer_name': v.customer.name if v.customer else 'CONSUMIDOR FINAL',
            'customer_identifier': v.customer.identifier if v.customer else '9999999999999',
            'invoice_id': v.invoice_id,
            'invoice_number': invoices_map.get(v.invoice_id, {}).get('number') if v.invoice_id else getattr(v, 'invoice_number', None),
            'access_key': invoices_map.get(v.invoice_id, {}).get('access_key') if v.invoice_id else getattr(v, 'access_key', None),
            'items': [{
                'description': i.description,
                'quantity': str(i.quantity),
                'unit_price': str(i.unit_price),
                'subtotal': str(i.subtotal)
            } for i in v.items]
        } for v in ventas])

    def post(self, request, register_id):
        if e := verificar_modulo(request): return e
        usuario_id = getattr(request.user, 'id', 0)
        
        items = request.data.get('items', [])
        payment_method = request.data.get('payment_method', 'cash')
        amount_received = Decimal(str(request.data.get('amount_received', 0)))
        
        param_repo = DjangoParameterRepository()
        iva_param = param_repo.get(request.tenant.id, 'ventas', 'iva')
        tasa_iva = Decimal(iva_param.value) / 100 if iva_param else Decimal('0.15')
        sin_stock_param = param_repo.get(request.tenant.id, 'pos', 'venta_sin_stock')
        venta_sin_stock = sin_stock_param.value.lower() == 'true' if sin_stock_param else False
        customer_data = request.data.get('customer')  # None = Final Consumer without invoice
        emit_invoice = bool(customer_data)
        pos_customer = None
        
        if emit_invoice:
            pos_customer = POSCustomer(
                name=customer_data.get('name', 'CONSUMIDOR FINAL').strip(),
                identifier=customer_data.get('identifier', '9999999999999').strip(),
                id_type=customer_data.get('id_type', '07').strip(),
                address=customer_data.get('address', '').strip(),
                email=customer_data.get('email', '').strip(),
                payment_form=customer_data.get('payment_form', '01').strip()
            )
            
            if request.data.get('update_customer'):
                from modules.ventas.infrastructure.django_models import CustomerModel
                c_id = customer_data.get('customer_id')
                if c_id:
                    c_model = CustomerModel.objects.filter(id=c_id, tenant_id=request.tenant.id).first()
                else:
                    c_model = CustomerModel.objects.filter(rfc=pos_customer.identifier, tenant_id=request.tenant.id).first()
                
                if c_model:
                    c_model.name = pos_customer.name
                    c_model.email = pos_customer.email
                    c_model.address = pos_customer.address
                    if pos_customer.identifier and pos_customer.identifier != '9999999999999':
                        c_model.rfc = pos_customer.identifier
                    c_model.save()

        try:
            service = _get_pos_service(request)
            sale = service.process_sale(
                tenant_id=request.tenant.id,
                register_id=register_id,
                user_id=usuario_id,
                seller_id=request.data.get('seller_id'),
                items=items,
                payment_method=payment_method,
                amount_received=amount_received,
                vat_rate=Decimal(str(request.data.get('vat_rate', tasa_iva))),
                sale_without_stock=request.data.get('sale_without_stock', venta_sin_stock),
                customer=pos_customer,
                emit_invoice=emit_invoice,
                reference_number=request.data.get('reference_number'),
                quotation_id=request.data.get('quotation_id'),
                document_type=request.data.get('document_type', '01')
            )
            
            resp = {
                'id': sale.id,
                'total': str(sale.total),
                'change': str(sale.change),
                'status': sale.status,
            }
            if sale.invoice_id:
                resp['invoice_id'] = sale.invoice_id
                resp['invoice_number'] = getattr(sale, 'invoice_number', None)
                resp['access_key'] = getattr(sale, 'access_key', None)
            return Response(resp, status=status.HTTP_201_CREATED)
        except ValueError as e:
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'error': f"Internal Server Error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PhysicalCashRegisterView(APIView):
    def get(self, request):
        if e := verificar_modulo(request): return e
        from django.db import models
        from ..django_models import PhysicalCashRegisterModel
        qs = PhysicalCashRegisterModel.objects.filter(tenant_id=request.tenant.id, active=True)
        sucursal_id = request.query_params.get('sucursal_id')
        if sucursal_id:
            qs = qs.filter(models.Q(branch_id=sucursal_id) | models.Q(branch_id__isnull=True))
        return Response([{
            'id': c.id,
            'code': c.code,
            'name': c.name,
            'branch_id': c.branch_id,
            'primary_cashier_id': c.primary_cashier_id,
            'active': c.active,
            'emission_point': c.emission_point
        } for c in qs])

    def post(self, request):
        if e := verificar_modulo(request): return e
        if e := admin_only(request): return e
        from ..django_models import PhysicalCashRegisterModel
        code = request.data.get('code', request.data.get('codigo', '')).strip()
        name = request.data.get('name', request.data.get('nombre', '')).strip()
        if not code or not name:
            return Response({'error': 'Code and name are required'}, status=status.HTTP_400_BAD_REQUEST)
        caja_reg = PhysicalCashRegisterModel.objects.create(
            tenant_id=request.tenant.id,
            code=code,
            name=name,
            branch_id=request.data.get('branch_id', request.data.get('sucursal_id')),
            primary_cashier_id=request.data.get('primary_cashier_id', request.data.get('cajero_principal_id')),
            active=request.data.get('active', request.data.get('activa', True)),
            emission_point=request.data.get('emission_point', '001')
        )
        return Response({
            'id': caja_reg.id,
            'code': caja_reg.code,
            'name': caja_reg.name,
            'branch_id': caja_reg.branch_id,
            'primary_cashier_id': caja_reg.primary_cashier_id,
            'active': caja_reg.active
        }, status=status.HTTP_201_CREATED)


class PhysicalCashRegisterDetailView(APIView):
    def put(self, request, physical_reg_id):
        if e := verificar_modulo(request): return e
        if e := admin_only(request): return e
        from ..django_models import PhysicalCashRegisterModel
        caja_reg = PhysicalCashRegisterModel.objects.filter(id=physical_reg_id, tenant_id=request.tenant.id).first()
        if not caja_reg:
            return Response({'error': 'Register not found'}, status=status.HTTP_404_NOT_FOUND)
        
        caja_reg.code = request.data.get('code', caja_reg.code).strip()
        caja_reg.name = request.data.get('name', caja_reg.name).strip()
        caja_reg.branch_id = request.data.get('branch_id', caja_reg.branch_id)
        caja_reg.primary_cashier_id = request.data.get('primary_cashier_id', caja_reg.primary_cashier_id)
        caja_reg.active = request.data.get('active', caja_reg.active)
        caja_reg.emission_point = request.data.get('emission_point', caja_reg.emission_point)
        caja_reg.save()
        return Response({'message': 'Register updated successfully'})

    def delete(self, request, physical_reg_id):
        if e := verificar_modulo(request): return e
        if e := admin_only(request): return e
        from ..django_models import PhysicalCashRegisterModel
        caja_reg = PhysicalCashRegisterModel.objects.filter(id=physical_reg_id, tenant_id=request.tenant.id).first()
        if not caja_reg:
            return Response({'error': 'Register not found'}, status=status.HTTP_404_NOT_FOUND)
        caja_reg.delete()
        return Response({'message': 'Register deleted successfully'})


class CashRegisterMovementView(APIView):
    def get(self, request, register_id):
        if e := verificar_modulo(request): return e
        from ...infrastructure.repository_impl import DjangoCashRegisterRepository
        movements = DjangoCashRegisterRepository().get_movements_by_register(register_id, request.tenant.id)
        return Response([{
            'id': m.id,
            'movement_type': m.movement_type,
            'amount': str(m.amount),
            'reason': m.reason,
            'created_at': m.created_at
        } for m in movements])

    def post(self, request, register_id):
        if e := verificar_modulo(request): return e
        user_id = getattr(request.user, 'id', 0)
        movement_type = request.data.get('movement_type')
        amount = Decimal(str(request.data.get('amount', '0')))
        reason = request.data.get('reason', '').strip()

        if not movement_type or not reason or amount <= 0:
            return Response({'error': 'Movement type, reason, and an amount greater than 0 are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            service = _get_pos_service(request)
            movement = service.register_movement(
                tenant_id=request.tenant.id,
                user_id=user_id,
                register_id=register_id,
                movement_type=movement_type,
                amount=amount,
                reason=reason
            )
            return Response({
                'id': movement.id,
                'movement_type': movement.movement_type,
                'amount': str(movement.amount),
                'reason': movement.reason,
                'created_at': movement.created_at
            }, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

