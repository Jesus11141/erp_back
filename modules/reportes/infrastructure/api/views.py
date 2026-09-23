from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from modules.reportes.infrastructure.pdf_generator import generate_invoice_pdf, generate_quote_pdf
from modules.reportes.infrastructure.excel_generator import (
    generate_sales_excel_report,
    generate_inventory_excel_report,
    generate_clients_excel_report,
    generate_payroll_excel_report,
)
from modules.parametros.infrastructure.repository_impl import DjangoParameterRepository
from modules.parametros.application.use_cases import GetAllParameters

def _verify_tenant(request):
    if not request.tenant:
        return Response({'error': 'Company not found'}, status=status.HTTP_404_NOT_FOUND)
    return None

def _get_params(tenant_id: int) -> dict:
    repo = DjangoParameterRepository()
    return GetAllParameters(repo).execute(tenant_id)

def _tenant_dict(tenant) -> dict:
    return {
        'name': tenant.name,
        'primary_color': tenant.primary_color,
        'secondary_color': tenant.secondary_color,
        'logo_url': tenant.logo_url,
    }

# ── PDF ──────────────────────────────────────────────────────────

class InvoicePDFView(APIView):

    def get(self, request, invoice_id: int):
        if error := _verify_tenant(request): return error
        try:
            from modules.tax_documents.invoicing.infrastructure.persistence.django_models import InvoiceModel
            m = InvoiceModel.objects.get(id=invoice_id, tenant_id=request.tenant.id)
            items = [
                {
                    'description': i.description,
                    'quantity': str(i.quantity),
                    'unit_price': str(i.unit_price),
                    'discount': str(i.discount or '0'),
                    'vat_rate': str(i.vat_rate or '15'),
                }
                for i in m.items.all()
            ]
            invoice_data = {
                'number': m.number,
                'date': str(m.date),
                'status': m.status,
                'client': m.client,
                'client_identification': m.client_identification,
                'client_address': m.client_address,
                'client_email': m.client_email,
                'items': items,
            }
            params = _get_params(request.tenant.id)
            pdf = generate_invoice_pdf(invoice_data, params, _tenant_dict(request.tenant))
            response = HttpResponse(pdf, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="invoice-{m.number}.pdf"'
            return response
        except InvoiceModel.DoesNotExist:
            return Response({'error': 'Invoice no encontrada'}, status=status.HTTP_404_NOT_FOUND)

class QuotePDFView(APIView):

    def get(self, request, quote_id: int):
        if error := _verify_tenant(request): return error
        try:
            from modules.ventas.infrastructure.django_models import QuotationModel
            m = QuotationModel.objects.get(id=quote_id, tenant_id=request.tenant.id)
            items = [
                {
                    'description': i.description,
                    'quantity': str(i.quantity),
                    'unit_price': str(i.unit_price),
                    'discount': str(i.discount or '0'),
                }
                for i in m.items.all()
            ]
            
            # Obtener datos extendidos del client
            client_identification = ''
            client_email = ''
            cliente_telefono = ''
            client_address = ''
            if m.customer:
                client_identification = m.customer.id_number or ''
                client_email = m.customer.email or ''
                cliente_telefono = m.customer.phone or ''
                client_address = m.customer.address or ''
                
            cotizacion_data = {
                'date': str(m.date),
                'status': m.status,
                'cliente_nombre': m.customer_name,
                'client_identification': client_identification,
                'client_email': client_email,
                'cliente_telefono': cliente_telefono,
                'client_address': client_address,
                'notas': m.notes,
                'items': items,
            }
            params = _get_params(request.tenant.id)
            pdf = generate_quote_pdf(cotizacion_data, params, _tenant_dict(request.tenant))
            response = HttpResponse(pdf, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="quote-{m.id}.pdf"'
            return response
        except QuotationModel.DoesNotExist:
            return Response({'error': 'Cotización no encontrada'}, status=status.HTTP_404_NOT_FOUND)

# ── EXCEL ─────────────────────────────────────────────────────────

class SalesExcelView(APIView):

    def get(self, request):
        if error := _verify_tenant(request): return error
        from decimal import Decimal
        datos = []

        # 1. Cargar Sales del POS
        from modules.pos.infrastructure.django_models import POSSaleModel
        ventas_pos = POSSaleModel.objects.filter(tenant_id=request.tenant.id, status='completada')
        for v in ventas_pos:
            total_bruto = sum(i.quantity * i.unit_price for i in v.items.all())
            total_bruto = Decimal(str(total_bruto))
            total_descuento = sum(i.quantity * i.unit_price * (i.discount / 100) for i in v.items.all())
            total_descuento = Decimal(str(total_descuento))
            subtotal = total_bruto - total_descuento
            tasa_iva = Decimal(str(v.vat_rate or '0.15'))
            iva = (subtotal * tasa_iva).quantize(Decimal('0.01'))
            total = subtotal + iva
            
            from django.utils.timezone import localtime
            fecha_str = localtime(v.created_at).strftime('%Y-%m-%d %H:%M:%S') if v.created_at else ''
            
            datos.append({
                'client': v.customer_name or 'CONSUMIDOR FINAL',
                'date': fecha_str,
                'subtotal_bruto': float(total_bruto),
                'discount': float(total_descuento),
                'subtotal_neto': float(subtotal),
                'iva': float(iva),
                'total': float(total),
                'status': v.status,
                'metodo_pago': v.payment_method.capitalize(),
                'vendedor': f"POS Reg #{v.register_id}",
            })

        # 2. Cargar Pedidos de Sales Manuales
        from modules.ventas.infrastructure.django_models import OrderModel
        orders = OrderModel.objects.filter(tenant_id=request.tenant.id)
        for p in orders:
            total_bruto = sum(i.quantity * i.unit_price for i in p.items.all())
            total_bruto = Decimal(str(total_bruto))
            total_descuento = sum(i.quantity * i.unit_price * (i.discount / 100) for i in p.items.all())
            total_descuento = Decimal(str(total_descuento))
            subtotal = total_bruto - total_descuento
            iva = (subtotal * Decimal('0.15')).quantize(Decimal('0.01'))
            total = subtotal + iva
            
            datos.append({
                'client': p.customer_name,
                'date': str(p.date),
                'subtotal_bruto': float(total_bruto),
                'discount': float(total_descuento),
                'subtotal_neto': float(subtotal),
                'iva': float(iva),
                'total': float(total),
                'status': p.status,
                'metodo_pago': 'Otros / Crédito',
                'vendedor': 'Sales Manual',
            })

        params = _get_params(request.tenant.id)
        excel = generate_sales_excel_report(datos, params, _tenant_dict(request.tenant))
        response = HttpResponse(excel, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="reporte-sales.xlsx"'
        return response

class InventoryExcelView(APIView):

    def get(self, request):
        if error := _verify_tenant(request): return error
        from modules.inventario.infrastructure.django_models import ProductModel
        productos = ProductModel.objects.filter(tenant_id=request.tenant.id, active=True)
        datos = [
            {
                'codigo': p.code, 'name': p.name,
                'categoria': '', 'stock_actual': str(p.current_stock),
                'stock_minimo': str(p.minimum_stock),
                'precio_compra': str(p.purchase_price),
                'precio_venta': str(p.sale_price),
            }
            for p in productos
        ]
        params = _get_params(request.tenant.id)
        excel = generate_inventory_excel_report(datos, params, _tenant_dict(request.tenant))
        response = HttpResponse(excel, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="reporte-inventory.xlsx"'
        return response

class ClientsExcelView(APIView):

    def get(self, request):
        if error := _verify_tenant(request): return error
        from modules.ventas.infrastructure.django_models import CustomerModel
        clients = CustomerModel.objects.filter(tenant_id=request.tenant.id, active=True)
        datos = [
            {
                'name': c.name, 'email': c.email,
                'telefono': c.phone, 'rfc': c.rfc,
                'direccion': c.address, 'activo': c.active,
            }
            for c in clients
        ]
        params = _get_params(request.tenant.id)
        excel = generate_clients_excel_report(datos, params, _tenant_dict(request.tenant))
        response = HttpResponse(excel, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="reporte-clients.xlsx"'
        return response

class PayrollExcelView(APIView):

    def get(self, request):
        if error := _verify_tenant(request): return error
        from modules.rrhh.infrastructure.django_models import PayrollModel
        from decimal import Decimal
        nominas = PayrollModel.objects.filter(tenant_id=request.tenant.id)
        datos = [
            {
                'empleado': n.employee_name,
                'periodo_inicio': str(n.period_start),
                'periodo_fin': str(n.period_end),
                'salario_base': str(n.base_salary),
                'bonos': str(n.bonuses),
                'deducciones': str(n.deductions),
                'total_neto': str(n.net_salary),
            }
            for n in nominas
        ]
        params = _get_params(request.tenant.id)
        excel = generate_payroll_excel_report(datos, params, _tenant_dict(request.tenant))
        response = HttpResponse(excel, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="reporte-payroll.xlsx"'
        return response


class ProfitMarginExcelView(APIView):
    def get(self, request):
        if error := _verify_tenant(request): return error
        from ...application.use_cases import GetProfitMarginReport
        from ..repository_impl import DjangoReportRepository
        from ..excel_generator import generate_profit_excel_report
        
        repo = DjangoReportRepository()
        data = GetProfitMarginReport(repo).execute(request.tenant.id)
        params = _get_params(request.tenant.id)
        excel = generate_profit_excel_report(data, params, _tenant_dict(request.tenant))
        
        response = HttpResponse(excel, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="reporte-utilidades.xlsx"'
        return response


class ProfitMarginPDFView(APIView):
    def get(self, request):
        if error := _verify_tenant(request): return error
        from ...application.use_cases import GetProfitMarginReport
        from ..repository_impl import DjangoReportRepository
        from ..pdf_generator import generate_report_pdf
        
        repo = DjangoReportRepository()
        data = GetProfitMarginReport(repo).execute(request.tenant.id)
        
        columns = ["Venta ID", "Fecha", "Código", "Descripción", "Cant.", "Ingreso", "Costo", "Ganancia", "Margen"]
        rows = [
            [
                str(r.get('sale_id') or ''),
                str(r.get('date') or ''),
                str(r.get('product_code') or 'N/D'),
                str(r.get('product_name') or 'Sin descripción'),
                f"{float(r.get('quantity') or 0.0):.2f}",
                f"${float(r.get('revenue') or 0.0):.2f}",
                f"${float(r.get('cost') or 0.0):.2f}",
                f"${float(r.get('profit') or 0.0):.2f}",
                f"{float(r.get('margin') or 0.0):.2f}%"
            ]
            for r in data
        ]
        
        params = _get_params(request.tenant.id)
        pdf = generate_report_pdf("Reporte de Utilidades y Margen", columns, rows, params, _tenant_dict(request.tenant))
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="reporte-utilidades.pdf"'
        return response


class TopProductsExcelView(APIView):
    def get(self, request):
        if error := _verify_tenant(request): return error
        from ...application.use_cases import GetTopSellingProductsReport
        from ..repository_impl import DjangoReportRepository
        from ..excel_generator import generate_top_products_excel_report
        
        repo = DjangoReportRepository()
        data = GetTopSellingProductsReport(repo).execute(request.tenant.id)
        params = _get_params(request.tenant.id)
        excel = generate_top_products_excel_report(data, params, _tenant_dict(request.tenant))
        
        response = HttpResponse(excel, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="reporte-top-productos.xlsx"'
        return response


class TopProductsPDFView(APIView):
    def get(self, request):
        if error := _verify_tenant(request): return error
        from ...application.use_cases import GetTopSellingProductsReport
        from ..repository_impl import DjangoReportRepository
        from ..pdf_generator import generate_report_pdf
        
        repo = DjangoReportRepository()
        data = GetTopSellingProductsReport(repo).execute(request.tenant.id)
        
        columns = ["Ranking", "Código", "Descripción", "Cantidad Vendida", "Total Recaudado"]
        rows = [
            [
                str(idx),
                str(r.get('code') or 'N/D'),
                str(r.get('name') or 'Sin descripción'),
                f"{float(r.get('quantity') or 0.0):.2f}",
                f"${float(r.get('revenue') or 0.0):.2f}"
            ]
            for idx, r in enumerate(data, 1)
        ]
        
        params = _get_params(request.tenant.id)
        pdf = generate_report_pdf("Ranking de Productos Más Vendidos", columns, rows, params, _tenant_dict(request.tenant))
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="reporte-top-productos.pdf"'
        return response


class CashClosureExcelView(APIView):
    def get(self, request, closure_id: int):
        if error := _verify_tenant(request): return error
        from ...application.use_cases import GetCashRegisterClosureReport
        from ..repository_impl import DjangoReportRepository
        from ..excel_generator import generate_cash_closure_excel
        
        try:
            repo = DjangoReportRepository()
            data = GetCashRegisterClosureReport(repo).execute(request.tenant.id, closure_id)
            params = _get_params(request.tenant.id)
            excel = generate_cash_closure_excel(data, params, _tenant_dict(request.tenant))
            response = HttpResponse(excel, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename="closing-cash_register-{closure_id}.xlsx"'
            return response
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)


class CashClosurePDFView(APIView):
    def get(self, request, closure_id: int):
        if error := _verify_tenant(request): return error
        from ...application.use_cases import GetCashRegisterClosureReport
        from ..repository_impl import DjangoReportRepository
        from ..pdf_generator import generate_cash_closure_pdf
        
        try:
            repo = DjangoReportRepository()
            data = GetCashRegisterClosureReport(repo).execute(request.tenant.id, closure_id)
            params = _get_params(request.tenant.id)
            pdf = generate_cash_closure_pdf(data, params, _tenant_dict(request.tenant))
            response = HttpResponse(pdf, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="closing-cash_register-{closure_id}.pdf"'
            return response
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)


class CashClosureSummaryExcelView(APIView):
    def get(self, request):
        if error := _verify_tenant(request): return error
        from ...application.use_cases import GetCashRegisterClosureSummaryReport
        from ..excel_generator import generate_closure_summary_excel
        from datetime import date
        from rest_framework import status
        
        period_type = request.query_params.get('period_type', 'day')
        date_val = request.query_params.get('date', date.today().strftime('%Y-%m-%d'))
        branch_id = request.query_params.get('branch_id')
        register_id = request.query_params.get('register_id')
        employee_id = request.query_params.get('employee_id')

        try:
            bid = int(branch_id) if branch_id else None
            rid = int(register_id) if register_id else None
            eid = int(employee_id) if employee_id else None
        except ValueError:
            return Response({'error': 'Parámetros numéricos inválidos'}, status=status.HTTP_400_BAD_REQUEST)

        from ..repository_impl import DjangoReportRepository
        repo = DjangoReportRepository()
        report_data = GetCashRegisterClosureSummaryReport(repo).execute(
            tenant_id=request.tenant.id,
            period_type=period_type,
            date_str=date_val,
            branch_id=bid,
            register_id=rid,
            employee_id=eid
        )
        
        params = _get_params(request.tenant.id)
        excel = generate_closure_summary_excel(report_data, params, _tenant_dict(request.tenant))
        
        response = HttpResponse(excel, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="summary-cierres-cash_register.xlsx"'
        return response


class CashClosureSummaryPDFView(APIView):
    def get(self, request):
        if error := _verify_tenant(request): return error
        from ...application.use_cases import GetCashRegisterClosureSummaryReport
        from ..pdf_generator import generate_closure_summary_pdf
        from datetime import date
        from rest_framework import status
        
        period_type = request.query_params.get('period_type', 'day')
        date_val = request.query_params.get('date', date.today().strftime('%Y-%m-%d'))
        branch_id = request.query_params.get('branch_id')
        register_id = request.query_params.get('register_id')
        employee_id = request.query_params.get('employee_id')

        try:
            bid = int(branch_id) if branch_id else None
            rid = int(register_id) if register_id else None
            eid = int(employee_id) if employee_id else None
        except ValueError:
            return Response({'error': 'Parámetros numéricos inválidos'}, status=status.HTTP_400_BAD_REQUEST)

        from ..repository_impl import DjangoReportRepository
        repo = DjangoReportRepository()
        report_data = GetCashRegisterClosureSummaryReport(repo).execute(
            tenant_id=request.tenant.id,
            period_type=period_type,
            date_str=date_val,
            branch_id=bid,
            register_id=rid,
            employee_id=eid
        )
        
        params = _get_params(request.tenant.id)
        pdf = generate_closure_summary_pdf(report_data, params, _tenant_dict(request.tenant))
        
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="summary-cierres-cash_register.pdf"'
        return response





