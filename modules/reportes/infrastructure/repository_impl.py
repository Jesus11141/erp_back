from decimal import Decimal
from datetime import date
from typing import List, Dict, Any, Optional
from django.utils import timezone
from ..domain.repositories import ReportRepository
from ..domain.entities import SalesMetrics, InventoryMetrics, HRMetrics

class DjangoReportRepository(ReportRepository):
    
    def get_dashboard_sales(self, tenant_id: int) -> SalesMetrics:
        from modules.ventas.infrastructure.django_models import QuotationModel, OrderModel
        from modules.pos.infrastructure.django_models import POSSaleModel
        from django.db.models import Sum, F
        
        total_orders = OrderModel.objects.filter(tenant_id=tenant_id, status='delivered').aggregate(
            total=Sum(F('items__quantity') * F('items__unit_price'))
        )['total'] or Decimal(0)
        
        total_pos = POSSaleModel.objects.filter(tenant_id=tenant_id, status='completed').aggregate(
            total=Sum(F('items__quantity') * F('items__unit_price'))
        )['total'] or Decimal(0)
        
        total_sales = total_orders + total_pos
        
        quotes = QuotationModel.objects.filter(tenant_id=tenant_id).count()
        orders = OrderModel.objects.filter(tenant_id=tenant_id).count()
        pending = OrderModel.objects.filter(tenant_id=tenant_id, status='pending').count()
        
        return SalesMetrics(
            total_sales=total_sales, 
            total_quotes=quotes,
            total_orders=orders, 
            pending_orders=pending, 
            top_clients=[]
        )

    def get_dashboard_inventory(self, tenant_id: int) -> InventoryMetrics:
        from modules.inventario.infrastructure.django_models import ProductModel
        from django.db.models import Sum, F
        
        products = ProductModel.objects.filter(tenant_id=tenant_id, active=True)
        total = products.count()
        low_stock = products.filter(current_stock__lte=F('minimum_stock')).count()
        value = products.aggregate(v=Sum(F('current_stock') * F('purchase_price')))['v'] or Decimal(0)
        
        return InventoryMetrics(
            total_products=total, 
            low_stock_products=low_stock, 
            inventory_value=value
        )

    def get_dashboard_hr(self, tenant_id: int) -> HRMetrics:
        from modules.rrhh.infrastructure.django_models import EmployeeModel, AttendanceModel
        from django.db.models import Sum
        
        empleados = EmployeeModel.objects.filter(tenant_id=tenant_id, active=True).count()
        payroll = EmployeeModel.objects.filter(tenant_id=tenant_id, active=True).aggregate(
            total=Sum('salary'))['total'] or Decimal(0)
        attendances_today = AttendanceModel.objects.filter(tenant_id=tenant_id, date=date.today()).count()
        
        return HRMetrics(
            total_employees=empleados, 
            monthly_payroll=payroll, 
            attendances_today=attendances_today
        )

    def get_bi_metrics(self, tenant_id: int) -> dict:
        from modules.pos.infrastructure.django_models import POSSaleModel, POSSaleItemModel
        from modules.inventario.infrastructure.django_models import ProductModel
        from django.db.models import Sum, F, Count
        from django.db.models.functions import TruncHour
        from datetime import datetime, timedelta
        from django.utils import timezone
        
        today = timezone.now().date()
        current_month = today.replace(day=1)
        
        # 1. Sales by Hour (Today)
        sales_today = POSSaleModel.objects.filter(
            tenant_id=tenant_id, 
            status='completed',
            created_at__date=today
        ).annotate(
            hour=TruncHour('created_at')
        ).values('hour').annotate(
            total=Sum(F('items__quantity') * F('items__unit_price'))
        ).order_by('hour')
        
        sales_by_hour = {}
        for s in sales_today:
            if s['hour']:
                hour_str = f"{s['hour'].hour:02d}:00"
                sales_by_hour[hour_str] = float(s['total'] or 0)
        
        # 2. Top Selling Products (Current Month)
        top_products_qs = POSSaleItemModel.objects.filter(
            sale__tenant_id=tenant_id,
            sale__status='completed',
            sale__created_at__gte=current_month
        ).values('description').annotate(
            total_qty=Sum('quantity'),
            total_revenue=Sum(F('quantity') * F('unit_price'))
        ).order_by('-total_qty')[:5]
        
        top_products = [
            {'name': p['description'], 'qty': float(p['total_qty']), 'revenue': float(p['total_revenue'])}
            for p in top_products_qs
        ]
        
        # 3. Revenue Projections (Current Month)
        # Using a simple moving average to project end of month revenue
        # Find days in current month
        next_month = current_month.replace(day=28) + timedelta(days=4)
        last_day_of_month = next_month - timedelta(days=next_month.day)
        days_in_month = last_day_of_month.day
        current_day = today.day
        
        current_revenue = POSSaleModel.objects.filter(
            tenant_id=tenant_id,
            status='completed',
            created_at__gte=current_month
        ).aggregate(
            total=Sum(F('items__quantity') * F('items__unit_price'))
        )['total'] or Decimal(0)
        
        avg_daily = current_revenue / Decimal(current_day) if current_day > 0 else Decimal(0)
        projected_revenue = avg_daily * Decimal(days_in_month)
        
        projections = {
            'current_revenue': float(current_revenue),
            'projected_revenue': float(projected_revenue),
            'avg_daily': float(avg_daily)
        }
        
        # 4. Low Stock Alerts
        low_stock_qs = ProductModel.objects.filter(
            tenant_id=tenant_id, 
            active=True,
            current_stock__lte=F('minimum_stock')
        ).values('id', 'name', 'code', 'current_stock', 'minimum_stock')[:10]
        
        low_stock_products = [
            {
                'id': p['id'],
                'name': p['name'],
                'code': p['code'],
                'stock': float(p['current_stock']),
                'min_stock': float(p['minimum_stock'])
            }
            for p in low_stock_qs
        ]
        
        return {
            'sales_by_hour': sales_by_hour,
            'top_products': top_products,
            'projections': projections,
            'low_stock_products': low_stock_products
        }


    def get_profit_margin_report(self, tenant_id: int) -> List[Dict[str, Any]]:
        from modules.pos.infrastructure.django_models import POSSaleModel
        from modules.inventario.infrastructure.django_models import ProductModel
        
        sales = POSSaleModel.objects.filter(tenant_id=tenant_id, status='completada').prefetch_related('items')
        
        # Cache cost prices to avoid repeated database queries
        product_costs = {p.id: p.purchase_price for p in ProductModel.objects.filter(tenant_id=tenant_id)}
        
        report_data = []
        for sale in sales:
            for item in sale.items.all():
                qty = item.quantity
                unit_price = item.unit_price
                discount_pct = item.discount
                
                gross_revenue = qty * unit_price
                discount_val = gross_revenue * (discount_pct / Decimal('100'))
                net_revenue = gross_revenue - discount_val
                
                unit_cost = product_costs.get(item.product_id, Decimal('0.00')) or Decimal('0.00')
                total_cost = qty * unit_cost
                
                profit = net_revenue - total_cost
                margin = (profit / net_revenue * 100) if net_revenue > 0 else Decimal('0.00')
                
                report_data.append({
                    'sale_id': sale.id,
                    'date': sale.created_at.strftime('%Y-%m-%d %H:%M') if sale.created_at else '',
                    'product_code': item.code,
                    'product_name': item.description,
                    'quantity': float(qty),
                    'revenue': float(net_revenue),
                    'cost': float(total_cost),
                    'profit': float(profit),
                    'margin': float(margin.quantize(Decimal('0.01')))
                })
        return report_data

    def get_top_selling_products_report(self, tenant_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        from modules.pos.infrastructure.django_models import POSSaleItemModel
        from django.db.models import Sum, F
        
        top_items = (
            POSSaleItemModel.objects
            .filter(sale__tenant_id=tenant_id, sale__status='completada')
            .values('code', 'description')
            .annotate(
                total_qty=Sum('quantity'),
                total_revenue=Sum(F('quantity') * F('unit_price') * (1 - F('discount') / 100))
            )
            .order_by('-total_qty')[:limit]
        )
        
        return [
            {
                'code': item['code'],
                'name': item['description'],
                'quantity': float(item['total_qty'] or 0),
                'revenue': float((item['total_revenue'] or 0))
            }
            for item in top_items
        ]

    def get_cash_register_closure_report(self, tenant_id: int, closure_id: int) -> Dict[str, Any]:
        from modules.pos.infrastructure.django_models import CashRegisterClosureModel
        try:
            m = CashRegisterClosureModel.objects.select_related('register').get(id=closure_id, tenant_id=tenant_id)
        except CashRegisterClosureModel.DoesNotExist:
            raise ValueError("Cierre de cash_register no encontrado")

        employee_name = f"Cajero ID #{m.user_id}"
        try:
            from modules.rrhh.infrastructure.django_models import EmployeeModel
            emp = EmployeeModel.objects.filter(id=m.user_id, tenant_id=tenant_id).first()
            if emp:
                employee_name = emp.name
        except Exception:
            pass

        return {
            'id': m.id,
            'caja_nombre': m.register.name,
            'cajero': employee_name,
            'fecha_apertura': timezone.localtime(m.opened_at).strftime('%Y-%m-%d %H:%M:%S') if m.opened_at else '',
            'fecha_cierre': timezone.localtime(m.closed_at).strftime('%Y-%m-%d %H:%M:%S') if m.closed_at else '',
            'saldo_inicial': float(m.initial_balance),
            'total_efectivo': float(m.total_cash),
            'total_tarjeta': float(m.total_card),
            'total_transferencia': float(m.total_transfer),
            'total_sales': float(m.total_cash + m.total_card + m.total_transfer),
            'total_ingresos': float(m.total_inflows),
            'total_egresos': float(m.total_outflows),
            'num_ventas': m.sales_count,
            'saldo_esperado': float(m.expected_balance),
            'saldo_contado': float(m.counted_balance),
            'diferencia': float(m.difference),
            'observaciones': m.observations or 'Sin observaciones',
            'closing_breakdown': m.closure_breakdown or {}
        }

    def get_cash_register_closure_summary_report(
        self, 
        tenant_id: int, 
        period_type: str, 
        date_str: str,
        branch_id: Optional[int] = None, 
        register_id: Optional[int] = None,
        employee_id: Optional[int] = None
    ) -> Dict[str, Any]:
        from datetime import datetime, date, timedelta
        import calendar
        from modules.pos.infrastructure.django_models import CashRegisterClosureModel, POSSaleModel, CashRegisterModel
        from modules.inventario.infrastructure.django_models import BranchModel
        from modules.rrhh.infrastructure.django_models import EmployeeModel

        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            target_date = date.today()

        if period_type == 'day':
            start_date = target_date
            end_date = target_date
        elif period_type == 'week':
            start_date = target_date - timedelta(days=target_date.weekday())
            end_date = start_date + timedelta(days=6)
        elif period_type == 'biweekly':
            if target_date.day <= 15:
                start_date = date(target_date.year, target_date.month, 1)
                end_date = date(target_date.year, target_date.month, 15)
            else:
                start_date = date(target_date.year, target_date.month, 16)
                last_day = calendar.monthrange(target_date.year, target_date.month)[1]
                end_date = date(target_date.year, target_date.month, last_day)
        else: # month
            start_date = date(target_date.year, target_date.month, 1)
            last_day = calendar.monthrange(target_date.year, target_date.month)[1]
            end_date = date(target_date.year, target_date.month, last_day)

        report_meta = {
            'period_type': period_type,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'branch_name': 'All branches',
            'register_name': 'All registers',
            'employee_name': 'All employees',
            'is_employee_report': bool(employee_id)
        }

        if branch_id:
            branch = BranchModel.objects.filter(id=branch_id, tenant_id=tenant_id).first()
            if branch:
                report_meta['branch_name'] = branch.name

        if employee_id:
            emp = EmployeeModel.objects.filter(id=employee_id, tenant_id=tenant_id).first()
            if emp:
                report_meta['employee_name'] = emp.name

        # CASE 1: Employee detailed report
        if employee_id:
            sales_qs = POSSaleModel.objects.filter(
                tenant_id=tenant_id,
                user_id=employee_id,
                status='completada',
                created_at__date__range=(start_date, end_date)
            )
            if branch_id:
                sales_qs = sales_qs.filter(register__branch_id=branch_id)
            if register_id:
                from modules.pos.infrastructure.django_models import PhysicalCashRegisterModel
                p_caja = PhysicalCashRegisterModel.objects.filter(id=register_id, tenant_id=tenant_id).first()
                if p_caja:
                    sales_qs = sales_qs.filter(register__name=p_caja.name)
                    report_meta['register_name'] = p_caja.name

            from django.db.models import Sum, Q, Count
            grouped_sales = (
                sales_qs.values('register__name')
                .annotate(
                    cash=Sum('amount_received', filter=Q(payment_method='efectivo')),
                    card=Sum('amount_received', filter=Q(payment_method='tarjeta')),
                    transfer=Sum('amount_received', filter=Q(payment_method='transferencia')),
                    total=Sum('amount_received'),
                    sales_count=Count('id')
                )
                .order_by('register__name')
            )

            registers_data = []
            total_gral = 0.0
            total_cash = 0.0
            total_card = 0.0
            total_transfer = 0.0
            total_count = 0

            for g in grouped_sales:
                c = float(g['cash'] or 0.0)
                cd = float(g['card'] or 0.0)
                tr = float(g['transfer'] or 0.0)
                tot = float(g['total'] or 0.0)
                cnt = int(g['sales_count'] or 0)

                registers_data.append({
                    'register_name': g['register__name'],
                    'cash': c,
                    'card': cd,
                    'transfer': tr,
                    'total': tot,
                    'sales_count': cnt
                })
                total_gral += tot
                total_cash += c
                total_card += cd
                total_transfer += tr
                total_count += cnt

            return {
                'meta': report_meta,
                'details': registers_data,
                'totals': {
                    'cash': total_cash,
                    'card': total_card,
                    'transfer': total_transfer,
                    'total': total_gral,
                    'sales_count': total_count
                }
            }

        # CASE 2: Consolidated Cash Register Closures
        else:
            closures_qs = CashRegisterClosureModel.objects.filter(
                tenant_id=tenant_id,
                closed_at__date__range=(start_date, end_date)
            ).select_related('register')

            if branch_id:
                closures_qs = closures_qs.filter(register__branch_id=branch_id)
            if register_id:
                from modules.pos.infrastructure.django_models import PhysicalCashRegisterModel
                p_caja = PhysicalCashRegisterModel.objects.filter(id=register_id, tenant_id=tenant_id).first()
                if p_caja:
                    closures_qs = closures_qs.filter(register__name=p_caja.name)
                    report_meta['register_name'] = p_caja.name

            closures = closures_qs.all()

            closures_data = []
            total_gral = 0.0
            total_cash = 0.0
            total_card = 0.0
            total_transfer = 0.0
            total_count = 0

            for c in closures:
                closures_data.append({
                    'closure_id': c.id,
                    'register_name': c.register.name,
                    'closed_at': c.closed_at.strftime('%Y-%m-%d %H:%M:%S') if c.closed_at else '',
                    'cash': float(c.total_cash),
                    'card': float(c.total_card),
                    'transfer': float(c.total_transfer),
                    'total': float(c.total_cash + c.total_card + c.total_transfer),
                    'sales_count': c.sales_count
                })
                total_cash += float(c.total_cash)
                total_card += float(c.total_card)
                total_transfer += float(c.total_transfer)
                total_gral += float(c.total_cash + c.total_card + c.total_transfer)
                total_count += c.sales_count

            return {
                'meta': report_meta,
                'details': closures_data,
                'totals': {
                    'cash': total_cash,
                    'card': total_card,
                    'transfer': total_transfer,
                    'total': total_gral,
                    'sales_count': total_count
                }
            }

