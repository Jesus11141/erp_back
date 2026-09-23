from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from decimal import Decimal
from ...infrastructure.repository_impl import DjangoProductRepository, DjangoStockMovementRepository
from ...application.use_cases import CreateProduct, AdjustStock, ListProducts
from modules.shared.role_permissions import admin_only

def verificar_modulo(request):
    if not request.tenant:
        return Response({'error': 'Empresa no encontrada'}, status=status.HTTP_404_NOT_FOUND)
    if not (request.tenant.has_module('inventario') or request.tenant.has_module('pos')):
        return Response({'error': 'Módulo no disponible'}, status=status.HTTP_403_FORBIDDEN)



def _product_dict(p, branch_stocks_map=None):
    if branch_stocks_map is None:
        branch_stocks_map = {}
    
    # Safely convert image to a URL string — it may arrive as an ImageFieldFile object
    image_val = p.image
    if image_val and not isinstance(image_val, str):
        try:
            image_val = image_val.url
        except (ValueError, AttributeError):
            image_val = None

    base_dict = {
        'id': p.id,
        'code': p.code,
        'name': p.name,
        'description': p.description,
        'category': p.category,
        'purchase_price': str(p.purchase_price),
        'sale_price': str(p.sale_price),
        'current_stock': str(p.current_stock),
        'minimum_stock': str(p.minimum_stock),
        'unit': p.unit,
        'vat_rate': p.vat_rate,
        'low_stock': p.low_stock,
        'margin': str(p.margin),
        'image': image_val,
        'branch_stocks': branch_stocks_map.get(p.id, [])
    }
    return base_dict

class ProductView(APIView):
    from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        if e := verificar_modulo(request): return e
        query = request.query_params.get('q', '')
        low_stock = request.query_params.get('bajo_stock') == 'true'
        products = ListProducts(DjangoProductRepository()).execute(request.tenant.id, query, low_stock)
        
        # Batch fetch branch stocks to avoid N+1 queries
        from ...infrastructure.django_models import BranchStockModel
        p_ids = [p.id for p in products]
        branch_stocks_qs = BranchStockModel.objects.filter(product_id__in=p_ids).select_related('branch')
        
        b_map = {}
        for bs in branch_stocks_qs:
            if bs.product_id not in b_map:
                b_map[bs.product_id] = []
            b_map[bs.product_id].append({
                'branch_id': bs.branch_id,
                'branch_name': bs.branch.name,
                'quantity': str(bs.quantity)
            })
            
        return Response([_product_dict(p, b_map) for p in products])

    def post(self, request):
        if e := verificar_modulo(request): return e
        try:
            # Map Spanish parameters from payload if they come from legacy frontend
            payload = {
                'code': request.data.get('code', request.data.get('codigo')),
                'name': request.data.get('name', request.data.get('nombre')),
                'description': request.data.get('description', request.data.get('descripcion', '')),
                'category': request.data.get('category', request.data.get('categoria', '')),
                'purchase_price': request.data.get('purchase_price', request.data.get('precio_compra', 0)),
                'sale_price': request.data.get('sale_price', request.data.get('precio_venta')),
                'initial_stock': request.data.get('initial_stock', request.data.get('stock_inicial', 0)),
                'minimum_stock': request.data.get('minimum_stock', request.data.get('stock_minimo', 0)),
                'unit': request.data.get('unit', request.data.get('unidad', 'pza')),
                'vat_rate': request.data.get('vat_rate', request.data.get('tarifa_iva', '15')),
                'image': request.data.get('image', request.data.get('foto'))
            }
            product = CreateProduct(DjangoProductRepository()).execute(request.tenant.id, payload)
            return Response(_product_dict(product), status=status.HTTP_201_CREATED)
        except (ValueError, KeyError, TypeError) as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class StockView(APIView):
    def post(self, request, producto_id):
        if e := verificar_modulo(request): return e
        try:
            user_id = getattr(request.usuario, 'id', 0) if hasattr(request, 'usuario') else 0
            qty = request.data.get('quantity', request.data.get('cantidad'))
            type_val = request.data.get('type', request.data.get('tipo'))
            ref_val = request.data.get('reference', request.data.get('referencia', ''))
            
            product = AdjustStock(DjangoProductRepository(), DjangoStockMovementRepository()).execute(
                tenant_id=request.tenant.id,
                product_id=producto_id,
                quantity=Decimal(str(qty)),
                type=type_val,
                reference=ref_val,
                user_id=user_id,
            )
            return Response(_product_dict(product))
        except (ValueError, KeyError, TypeError) as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class StockMovementView(APIView):
    def get(self, request, producto_id):
        if e := verificar_modulo(request): return e
        movements = DjangoStockMovementRepository().list_by_product(producto_id, request.tenant.id)
        return Response([{
            'type': m.type,
            'quantity': str(m.quantity),
            'new_stock': str(m.new_stock),
            'reference': m.reference,
            'created_at': m.created_at
        } for m in movements])


class BranchView(APIView):
    def get(self, request):
        if e := verificar_modulo(request): return e
        from ...infrastructure.django_models import BranchModel
        branches = BranchModel.objects.filter(tenant_id=request.tenant.id, active=True)
        return Response([{
            'id': s.id,
            'name': s.name,
            'address': s.address,
            'phone': s.phone,
            'establishment': s.establishment,
            'active': s.active
        } for s in branches])

    def post(self, request):
        if e := verificar_modulo(request): return e
        if e := admin_only(request): return e
        from ...infrastructure.django_models import BranchModel
        try:
            s = BranchModel.objects.create(
                tenant_id=request.tenant.id,
                name=request.data.get('name', request.data.get('nombre')),
                address=request.data.get('address', request.data.get('direccion', '')),
                phone=request.data.get('phone', request.data.get('telefono', '')),
                establishment=request.data.get('establishment', request.data.get('establecimiento')),
                active=request.data.get('active', True)
            )
            return Response({
                'id': s.id,
                'name': s.name,
                'address': s.address,
                'establishment': s.establishment
            }, status=status.HTTP_201_CREATED)
        except KeyError as e:
            return Response({'error': f'Falta el campo obligatorio: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)


class StockTransferView(APIView):
    def get(self, request):
        if e := verificar_modulo(request): return e
        from ...infrastructure.django_models import StockTransferModel
        transfers = StockTransferModel.objects.filter(tenant_id=request.tenant.id).order_by('-created_at')
        return Response([{
            'id': t.id,
            'product_id': t.product_id,
            'product_name': t.product.name,
            'source_branch_id': t.source_branch_id,
            'source_branch_name': t.source_branch.name,
            'destination_branch_id': t.destination_branch_id,
            'destination_branch_name': t.destination_branch.name,
            'quantity': str(t.quantity),
            'created_at': t.created_at,
            'status': t.status,
            'observations': t.observations
        } for t in transfers])

    def post(self, request):
        if e := verificar_modulo(request): return e
        from ...application.transferencia_use_cases import TransferStockBetweenBranches
        from modules.parametros.infrastructure.repository_impl import DjangoParameterRepository
        from ...infrastructure.repository_impl import DjangoStockTransferRepository
        user_id = getattr(request.usuario, 'id', 0) if hasattr(request, 'usuario') else 0
        try:
            param_repo = DjangoParameterRepository()
            trans_repo = DjangoStockTransferRepository()
            
            prod_id = request.data.get('product_id', request.data.get('producto_id'))
            src_id = request.data.get('source_branch_id', request.data.get('sucursal_origen_id'))
            dst_id = request.data.get('destination_branch_id', request.data.get('sucursal_destino_id'))
            qty = request.data.get('quantity', request.data.get('cantidad'))
            obs = request.data.get('observations', request.data.get('observaciones', ''))
            
            transfer = TransferStockBetweenBranches(
                transfer_repo=trans_repo,
                param_repo=param_repo,
                movement_repo=DjangoStockMovementRepository()
            ).execute(
                tenant_id=request.tenant.id,
                product_id=int(prod_id),
                source_branch_id=int(src_id),
                destination_branch_id=int(dst_id),
                quantity=Decimal(str(qty)),
                user_id=user_id,
                observations=obs
            )
            return Response({
                'id': transfer.id,
                'status': transfer.status,
                'quantity': str(transfer.quantity),
                'created_at': transfer.created_at
            }, status=status.HTTP_201_CREATED)
        except (ValueError, KeyError, TypeError) as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class BranchStockView(APIView):
    def get(self, request, sucursal_id):
        if e := verificar_modulo(request): return e
        from ...infrastructure.django_models import BranchStockModel
        stocks = BranchStockModel.objects.filter(tenant_id=request.tenant.id, branch_id=sucursal_id)
        return Response([{
            'product_id': s.product_id,
            'product_name': s.product.name,
            'product_code': s.product.code,
            'current_stock': str(s.current_stock)
        } for s in stocks])


class KardexView(APIView):
    def get(self, request, producto_id):
        if e := verificar_modulo(request): return e
        from ...infrastructure.django_models import KardexModel
        kardex = KardexModel.objects.filter(tenant_id=request.tenant.id, product_id=producto_id).order_by('created_at', 'id')
        return Response([{
            'id': k.id,
            'created_at': k.created_at,
            'detail': k.detail,
            'entry_quantity': str(k.entry_quantity),
            'entry_unit_cost': str(k.entry_unit_cost),
            'entry_total_cost': str(k.entry_total_cost),
            'exit_quantity': str(k.exit_quantity),
            'exit_unit_cost': str(k.exit_unit_cost),
            'exit_total_cost': str(k.exit_total_cost),
            'balance_quantity': str(k.balance_quantity),
            'balance_unit_cost': str(k.balance_unit_cost),
            'balance_total_cost': str(k.balance_total_cost),
        } for k in kardex])


class ProductDiscountTierView(APIView):
    def get(self, request, producto_id):
        if e := verificar_modulo(request): return e
        from ...application.cotizador_service import QuotationService
        from ...infrastructure.repository_impl import DjangoProductRepository, DjangoVolumeDiscountRuleRepository
        service = QuotationService(DjangoProductRepository(), DjangoVolumeDiscountRuleRepository())
        tiers = service.get_product_tiers(request.tenant.id, producto_id)
        return Response(tiers)

    def post(self, request, producto_id):
        if e := verificar_modulo(request): return e
        from ...infrastructure.django_models import VolumeDiscountRuleModel, ProductModel
        
        product = ProductModel.objects.filter(id=producto_id, tenant_id=request.tenant.id).first()
        if not product:
            return Response({'error': 'Producto no encontrado'}, status=status.HTTP_404_NOT_FOUND)

        min_qty = request.data.get('minimum_quantity', request.data.get('cantidad_minima', 1))
        max_qty = request.data.get('maximum_quantity', request.data.get('cantidad_maxima'))
        
        cant_min = Decimal(str(min_qty))
        cant_max = Decimal(str(max_qty)) if max_qty is not None and str(max_qty).strip() != '' else None
        precio_u = Decimal(str(request.data.get('unit_price', request.data.get('precio_unitario', 0))))
        porcentaje_d = Decimal(str(request.data.get('discount_percentage', request.data.get('porcentaje_descuento', 0))))

        rule = VolumeDiscountRuleModel.objects.create(
            tenant_id=request.tenant.id,
            product=product,
            minimum_quantity=cant_min,
            maximum_quantity=cant_max,
            unit_price=precio_u,
            discount_percentage=porcentaje_d,
            active=request.data.get('active', True)
        )

        return Response({
            'id': rule.id,
            'minimum_quantity': str(rule.minimum_quantity),
            'maximum_quantity': str(rule.maximum_quantity) if rule.maximum_quantity is not None else None,
            'unit_price': str(rule.unit_price),
            'discount_percentage': str(rule.discount_percentage),
            'active': rule.active
        }, status=status.HTTP_201_CREATED)


class DiscountTierDetailView(APIView):
    def delete(self, request, escala_id):
        if e := verificar_modulo(request): return e
        from ...infrastructure.django_models import VolumeDiscountRuleModel
        rule = VolumeDiscountRuleModel.objects.filter(id=escala_id, tenant_id=request.tenant.id).first()
        if not rule:
            return Response({'error': 'Escala no encontrada'}, status=status.HTTP_404_NOT_FOUND)
        rule.delete()
        return Response({'mensaje': 'Escala eliminada correctamente'})


class QuotationView(APIView):
    def post(self, request):
        if e := verificar_modulo(request): return e
        from ...application.cotizador_service import QuotationService
        from ...infrastructure.repository_impl import DjangoProductRepository, DjangoVolumeDiscountRuleRepository

        product_id = request.data.get('product_id', request.data.get('producto_id'))
        quantity = Decimal(str(request.data.get('quantity', request.data.get('cantidad', 1))))

        if not product_id:
            return Response({'error': 'product_id es obligatorio'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            prod_repo = DjangoProductRepository()
            service = QuotationService(prod_repo, DjangoVolumeDiscountRuleRepository())
            result = service.calculate_quotation(request.tenant.id, int(product_id), quantity)
            
            # Enrich with tax calculations for frontend consumption
            product = prod_repo.find_by_id(int(product_id), request.tenant.id)
            vat_rate_val = Decimal(product.vat_rate) if product else Decimal('15')
            
            subtotal = Decimal(result['subtotal'])
            iva_amount = (subtotal * (vat_rate_val / Decimal('100'))).quantize(Decimal('0.01'))
            total_amount = (subtotal + iva_amount).quantize(Decimal('0.01'))
            
            result['base_price'] = str(product.sale_price) if product else '0.00'
            result['vat_rate'] = str(vat_rate_val)
            result['vat_amount'] = str(iva_amount)
            result['total'] = str(total_amount)
            
            return Response(result)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
class BranchDetailView(APIView):
    def put(self, request, sucursal_id):
        if e := verificar_modulo(request): return e
        if e := admin_only(request): return e
        from ..django_models import BranchModel
        branch = BranchModel.objects.filter(id=sucursal_id, tenant_id=request.tenant.id).first()
        if not branch:
            return Response({'error': 'Sucursal no encontrada'}, status=status.HTTP_404_NOT_FOUND)
        branch.name = request.data.get('nombre', branch.name).strip()
        branch.establishment = request.data.get('establecimiento', branch.establishment).strip()
        branch.address = request.data.get('direccion', branch.address).strip()
        branch.active = request.data.get('active', branch.active)
        branch.save()
        return Response({'mensaje': 'Sucursal actualizada correctamente'})

    def delete(self, request, sucursal_id):
        if e := verificar_modulo(request): return e
        if e := admin_only(request): return e
        from ..django_models import BranchModel
        branch = BranchModel.objects.filter(id=sucursal_id, tenant_id=request.tenant.id).first()
        if not branch:
            return Response({'error': 'Sucursal no encontrada'}, status=status.HTTP_404_NOT_FOUND)
        try:
            branch.delete()
            return Response({'mensaje': 'Sucursal eliminada correctamente'})
        except Exception:
            return Response({'error': 'No se puede eliminar porque está en uso'}, status=status.HTTP_400_BAD_REQUEST)



