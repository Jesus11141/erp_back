from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ...infrastructure.repository_impl import DjangoCustomerRepository, DjangoQuotationRepository, DjangoOrderRepository, DjangoPaymentMethodRepository, DjangoAccountReceivableRepository
from ...domain.entities import PaymentMethod
from ...application.use_cases import CreateCustomer, ListCustomers, CreateQuotation, SendQuotation, ConvertQuotationToOrder
from ...application.generate_quotation_pdf import GenerateQuotationPdf
from ...application.accounts_receivable_service import ListAccountReceivablesUseCase, AddReceivablePaymentUseCase
from django.http import HttpResponse
from modules.parametros.application.use_cases import GetParameter
from modules.parametros.infrastructure.repository_impl import DjangoParameterRepository

def verificar_modulo(request):
    if not request.tenant or not request.tenant.has_module('ventas'):
        return Response({'error': 'Module not available'}, status=status.HTTP_403_FORBIDDEN)

def _get_param(tenant_id, modulo, clave, default):
    return GetParameter(DjangoParameterRepository()).execute(tenant_id, modulo, clave, default)

class CustomersView(APIView):
    def get(self, request):
        if not request.tenant:
            return Response([], status=status.HTTP_200_OK)
        query = request.query_params.get('q', '')
        customers = ListCustomers(DjangoCustomerRepository()).execute(request.tenant.id, query)
        return Response([{
            'id': c.id,
            'name': c.name,
            'email': c.email,
            'phone': c.phone,
            'rfc': c.rfc,
            'address': c.address
        } for c in customers])

    def post(self, request):
        if e := verificar_modulo(request): return e
        try:
            customer = CreateCustomer(DjangoCustomerRepository()).execute(request.tenant.id, request.data)
            return Response({'id': customer.id, 'name': customer.name}, status=status.HTTP_201_CREATED)
        except (ValueError, KeyError) as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class QuotationsView(APIView):
    def get(self, request):
        if e := verificar_modulo(request): return e
        quotations = DjangoQuotationRepository().list_by_tenant(request.tenant.id)
        return Response([{
            'id': quotation.id,
            'customer': quotation.customer_name,
            'date': quotation.date,
            'total': str(quotation.total),
            'status': quotation.status
        } for quotation in quotations])

    def post(self, request):
        if e := verificar_modulo(request): return e
        try:
            db_vat = _get_param(request.tenant.id, 'ventas', 'iva', '12')
            vat = request.data.get('vat', db_vat)
            quotation = CreateQuotation(
                DjangoQuotationRepository(), DjangoCustomerRepository()
            ).execute(
                request.tenant.id,
                request.data.get('customer_id'),
                request.data.get('items', []),
                request.data.get('notes', ''),
                vat,
                validity_days=int(request.data.get('validity_days', 15)),
                payment_terms=request.data.get('payment_terms', ''),
                delivery_time=request.data.get('delivery_time', ''),
                print_style=request.data.get('print_style', 'corporativo'),
                show_images=request.data.get('show_images', False),
                is_preinvoice=request.data.get('is_preinvoice', False),
                seller_id=request.data.get('seller_id'),
                customer_data=request.data.get('customer')
            )
            return Response({'id': quotation.id}, status=status.HTTP_201_CREATED)
        except (ValueError, KeyError) as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class QuotationDetailView(APIView):
    def get(self, request, quotation_id):
        if e := verificar_modulo(request): return e
        q = DjangoQuotationRepository().find_by_id(quotation_id, request.tenant.id)
        if not q:
            return Response(status=status.HTTP_404_NOT_FOUND)
            
        customer = DjangoCustomerRepository().find_by_id(q.customer_id, request.tenant.id) if q.customer_id else None
            
        from modules.inventario.infrastructure.django_models import ProductModel
        items_data = []
        for i in q.items:
            prod_model = ProductModel.objects.filter(id=i.product_id).first()
            items_data.append({
                'product_id': i.product_id,
                'code': prod_model.code if prod_model else '-',
                'description': i.description or '-',
                'quantity': str(i.quantity),
                'unit_price': str(i.unit_price),
                'discount': str(i.discount),
                'subtotal': str(i.subtotal)
            })
            
        return Response({
            'id': q.id,
            'customer_id': q.customer_id,
            'customer_name': q.customer_name,
            'customer_rfc': customer.rfc if customer else '9999999999999',
            'customer_email': customer.email if customer else '',
            'customer_address': customer.address if customer else 'S/D',
            'date': q.date,
            'status': q.status,
            'total': str(q.total),
            'items': items_data
        })

    def delete(self, request, quotation_id):
        if e := verificar_modulo(request): return e
        from ..django_models import QuotationModel
        try:
            q = QuotationModel.objects.get(id=quotation_id, tenant_id=request.tenant.id)
            q.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except QuotationModel.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            q.status = 'rejected'
            q.save()
            return Response(status=status.HTTP_204_NO_CONTENT)

class QuotationConfigView(APIView):
    def put(self, request, quotation_id):
        if e := verificar_modulo(request): return e
        q = DjangoQuotationRepository().find_by_id(quotation_id, request.tenant.id)
        if not q:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        from ..django_models import QuotationModel
        qm = QuotationModel.objects.get(id=quotation_id, tenant_id=request.tenant.id)
        qm.validity_days = request.data.get('validity_days', qm.validity_days)
        qm.payment_terms = request.data.get('payment_terms', qm.payment_terms)
        qm.delivery_time = request.data.get('delivery_time', qm.delivery_time)
        qm.print_style = request.data.get('print_style', qm.print_style)
        qm.show_images = request.data.get('show_images', qm.show_images)
        qm.save()
        return Response({'status': 'ok'})

class QuotationPdfView(APIView):
    def get(self, request, quotation_id):
        if e := verificar_modulo(request): return e
        q = DjangoQuotationRepository().find_by_id(quotation_id, request.tenant.id)
        if not q:
            return Response(status=status.HTTP_404_NOT_FOUND)
            
        pdf_generator = GenerateQuotationPdf()
        pdf_bytes = pdf_generator.execute(q)
        
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="cotizacion_{q.id}.pdf"'
        return response

class QuotationActionView(APIView):
    def post(self, request, quotation_id, action):
        if e := verificar_modulo(request): return e
        try:
            if action == 'send':
                result = SendQuotation(DjangoQuotationRepository()).execute(quotation_id, request.tenant.id)
                return Response({'status': result.status})
            elif action == 'convert':
                order = ConvertQuotationToOrder(
                    DjangoQuotationRepository(), DjangoOrderRepository()
                ).execute(quotation_id, request.tenant.id)
                return Response({'order_id': order.id, 'status': order.status})
            return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class OrdersView(APIView):
    def get(self, request):
        if e := verificar_modulo(request): return e
        orders = DjangoOrderRepository().list_by_tenant(request.tenant.id)
        return Response([{
            'id': order.id,
            'customer': order.customer_name,
            'date': order.date,
            'total': str(order.total),
            'status': order.status
        } for order in orders])

class PaymentMethodsView(APIView):
    def get(self, request):
        if not request.tenant or not (request.tenant.has_module('ventas') or request.tenant.has_module('pos') or request.tenant.has_module('facturacion') or request.tenant.has_module('accounting')):
            return Response({'error': 'Module not available'}, status=status.HTTP_403_FORBIDDEN)
        repo = DjangoPaymentMethodRepository()
        include_inactive = request.query_params.get('all', 'false').lower() == 'true'
        methods = repo.find_all(request.tenant.id, include_inactive)
        return Response([{
            'id': m.id,
            'name': m.name,
            'active': m.active,
            'requires_reference': m.requires_reference,
            'sri_code': getattr(m, 'sri_code', '01') or '01'
        } for m in methods])

    def post(self, request):
        if not request.tenant or not (request.tenant.has_module('ventas') or request.tenant.has_module('pos') or request.tenant.has_module('facturacion') or request.tenant.has_module('accounting')):
            return Response({'error': 'Module not available'}, status=status.HTTP_403_FORBIDDEN)
        repo = DjangoPaymentMethodRepository()
        pm = PaymentMethod(
            id=None,
            tenant_id=request.tenant.id,
            name=request.data.get('name', ''),
            active=request.data.get('active', True),
            requires_reference=request.data.get('requires_reference', False),
            sri_code=request.data.get('sri_code') or None
        )
        if not pm.name:
            return Response({'error': 'Name is required'}, status=status.HTTP_400_BAD_REQUEST)
        saved = repo.save(pm)
        return Response({
            'id': saved.id,
            'name': saved.name,
            'active': saved.active,
            'requires_reference': saved.requires_reference,
            'sri_code': getattr(saved, 'sri_code', '01') or '01'
        }, status=status.HTTP_201_CREATED)

class PaymentMethodDetailView(APIView):
    def put(self, request, pk):
        if not request.tenant or not (request.tenant.has_module('ventas') or request.tenant.has_module('pos') or request.tenant.has_module('facturacion') or request.tenant.has_module('accounting')):
            return Response({'error': 'Module not available'}, status=status.HTTP_403_FORBIDDEN)
        repo = DjangoPaymentMethodRepository()
        pm = repo.find_by_id(pk, request.tenant.id)
        if not pm:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        pm.name = request.data.get('name', pm.name)
        pm.active = request.data.get('active', pm.active)
        pm.requires_reference = request.data.get('requires_reference', pm.requires_reference)
        if 'sri_code' in request.data:
            pm.sri_code = request.data.get('sri_code')
        if not pm.name:
            return Response({'error': 'Name is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        saved = repo.save(pm)
        return Response({
            'id': saved.id,
            'name': saved.name,
            'active': saved.active,
            'requires_reference': saved.requires_reference,
            'sri_code': getattr(saved, 'sri_code', '01') or '01'
        })

    def delete(self, request, pk):
        if not request.tenant or not (request.tenant.has_module('ventas') or request.tenant.has_module('pos') or request.tenant.has_module('facturacion') or request.tenant.has_module('accounting')):
            return Response({'error': 'Module not available'}, status=status.HTTP_403_FORBIDDEN)
        repo = DjangoPaymentMethodRepository()
        repo.delete(pk, request.tenant.id)
        return Response(status=status.HTTP_204_NO_CONTENT)

class AccountReceivablesView(APIView):
    def get(self, request):
        if e := verificar_modulo(request): return e
        receivables = ListAccountReceivablesUseCase(DjangoAccountReceivableRepository()).execute(request.tenant.id)
        return Response([{
            'id': ar.id,
            'customer_id': ar.customer_id,
            'customer_name': ar.customer_name,
            'total_amount': str(ar.total_amount),
            'balance_due': str(ar.balance_due),
            'status': ar.status,
            'reference_type': ar.reference_type,
            'reference_id': ar.reference_id
        } for ar in receivables])

class ReceivablePaymentView(APIView):
    def post(self, request, account_id):
        if e := verificar_modulo(request): return e
        
        from modules.pos.infrastructure.repository_impl import DjangoCashRegisterRepository
        from modules.parametros.infrastructure.repository_impl import DjangoParameterRepository
        
        user_id = request.user.id if hasattr(request, 'user') and request.user else None
        
        try:
            ar = AddReceivablePaymentUseCase(
                DjangoAccountReceivableRepository(),
                register_repo=DjangoCashRegisterRepository(),
                param_repo=DjangoParameterRepository()
            ).execute(
                request.tenant, user_id, account_id, request.data
            )
            return Response({
                'status': 'success',
                'new_balance': str(ar.balance_due),
                'ar_status': ar.status
            })
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
