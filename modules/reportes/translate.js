const fs = require('fs');
const path = require('path');

const repDir = "c:\\Users\\Raul\\Downloads\\erp\\backend\\modules\\reportes";

const replacements = {
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
};

function processFile(filepath) {
    let content = fs.readFileSync(filepath, 'utf8');
    
    for (const [k, v] of Object.entries(replacements)) {
        const regex = new RegExp(`\\b${k}\\b`, 'g');
        content = content.replace(regex, v);
    }
    
    fs.writeFileSync(filepath, content, 'utf8');
}

function walkDir(dir) {
    const files = fs.readdirSync(dir);
    for (const file of files) {
        const fullPath = path.join(dir, file);
        if (fs.statSync(fullPath).isDirectory()) {
            if (file !== '__pycache__') {
                walkDir(fullPath);
            }
        } else {
            if (fullPath.endsWith('.py') && file !== 'translate.js' && file !== 'translate.py') {
                processFile(fullPath);
            }
        }
    }
}

walkDir(repDir);

const oldF1 = path.join(repDir, 'application', 'get_cierre_caja_report.py');
const newF1 = path.join(repDir, 'application', 'get_cash_register_closure_report.py');
if (fs.existsSync(oldF1)) fs.renameSync(oldF1, newF1);

const oldF2 = path.join(repDir, 'application', 'get_cierre_caja_resumen_report.py');
const newF2 = path.join(repDir, 'application', 'get_cash_register_closure_summary_report.py');
if (fs.existsSync(oldF2)) fs.renameSync(oldF2, newF2);

console.log("Done");
