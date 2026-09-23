const fs = require('fs');
const path = require('path');

const repDir = "c:\\Users\\Raul\\Downloads\\erp\\backend\\modules\\reportes";

const replacements = {
    "CierreCajaPDFView": "CashClosurePDFView",
    "CierreCajaResumenExcelView": "CashClosureSummaryExcelView",
    "CierreCajaResumenPDFView": "CashClosureSummaryPDFView",
    "CotizacionPDFView": "QuotePDFView",
    "VentasExcelView": "SalesExcelView",
    "InventarioExcelView": "InventoryExcelView",
    "ClientesExcelView": "ClientsExcelView",
    "NominaExcelView": "PayrollExcelView",
    "factura_id": "invoice_id",
    "cotizacion_id": "quote_id",
    "total_cotizaciones": "total_quotes",
    "total_productos": "total_products",
    "productos_bajo_stock": "low_stock_products",
    "valor_inventario": "inventory_value",
    "nomina_mensual": "monthly_payroll",
    "asistencias_hoy": "attendances_today",
    "_verificar_tenant": "_verify_tenant",
    "_obtener_params": "_get_params",
    "Empresa no encontrada": "Company not found",
    "descripcion": "description",
    "cantidad": "quantity",
    "precio_unitario": "unit_price",
    "descuento": "discount",
    "tarifa_iva": "vat_rate",
    "color_primario": "primary_color",
    "color_secundario": "secondary_color",
    "rrhh": "hr"
};

function processFile(filepath) {
    let content = fs.readFileSync(filepath, 'utf8');
    
    for (const [k, v] of Object.entries(replacements)) {
        if (k.includes(" ")) {
            content = content.replace(new RegExp(k, 'g'), v);
        } else {
            const regex = new RegExp(`\\b${k}\\b`, 'g');
            content = content.replace(regex, v);
        }
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
            if (fullPath.endsWith('.py')) {
                processFile(fullPath);
            }
        }
    }
}

walkDir(repDir);

console.log("Done");
