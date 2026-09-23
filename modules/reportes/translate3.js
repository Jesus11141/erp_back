const fs = require('fs');
const path = require('path');

const repDir = "c:\\Users\\Raul\\Downloads\\erp\\backend\\modules\\reportes";

const replacements = {
    "pedidos_pendientes": "pending_orders",
    "total_empleados": "total_employees",
    "cotizacion": "quote",
    "clientes": "clients",
    "nomina": "payroll",
    "factura_data": "invoice_data",
    "numero": "number",
    "fecha": "date",
    "estado": "status",
    "cliente_identificacion": "client_identification",
    "cliente_direccion": "client_address",
    "cliente_email": "client_email",
    "Empresa no encontrada": "Company not found",
    "nombre": "name"
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
