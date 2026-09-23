import os
import re

rep_dir = r"c:\Users\Raul\Downloads\erp\backend\modules\reportes"

replacements = {
    "get_cierre_caja_resumen_report": "get_cash_register_closure_summary_report",
    "get_cierre_caja_report": "get_cash_register_closure_report",
    "GetCierreCajaResumenReport": "GetCashRegisterClosureSummaryReport",
    "GetCierreCajaReport": "GetCashRegisterClosureReport",
    "CierreCajaExcelView": "CashClosureExcelView",
    "FacturaPDFView": "InvoicePDFView",
    "CierreCajaResumen": "CashClosureSummary",
    "CierreCaja": "CashClosure",
    "cierre_caja": "cash_register_closure",
    "fecha_inicio": "start_date",
    "fecha_fin": "end_date",
    "monto_inicial": "initial_amount",
    "monto_final": "final_amount",
    "ingresos": "income",
    "egresos": "expenses",
    "ganancia": "profit",
    "margen": "margin",
    "factura": "invoice",
    "Factura": "Invoice",
    "producto": "product",
    "Producto": "Product",
    "inventario": "inventory",
    "Inventario": "Inventory",
    "cliente": "client",
    "Cliente": "Client",
    "usuario": "user",
    "Usuario": "User",
    "cierre": "closure",
    "Caja": "CashRegister",
    "caja": "cash_register",
    "ventas": "sales",
    "Ventas": "Sales",
    "compras": "purchases",
    "Compras": "Purchases",
    "total_ventas": "total_sales",
    "total_pedidos": "total_orders",
    "cotizaciones": "quotes",
    "pedidos": "orders",
    "pendientes": "pending",
    "resumen": "summary",
    "Resumen": "Summary"
}

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    for k, v in replacements.items():
        content = re.sub(r'\b' + k + r'\b', v, content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

for root, dirs, files in os.walk(rep_dir):
    for file in files:
        if file.endswith('.py') and file != 'translate.py':
            process_file(os.path.join(root, file))

# Rename files
old_f1 = os.path.join(rep_dir, 'application', 'get_cierre_caja_report.py')
new_f1 = os.path.join(rep_dir, 'application', 'get_cash_register_closure_report.py')
if os.path.exists(old_f1):
    os.rename(old_f1, new_f1)

old_f2 = os.path.join(rep_dir, 'application', 'get_cierre_caja_resumen_report.py')
new_f2 = os.path.join(rep_dir, 'application', 'get_cash_register_closure_summary_report.py')
if os.path.exists(old_f2):
    os.rename(old_f2, new_f2)

print("Done")
