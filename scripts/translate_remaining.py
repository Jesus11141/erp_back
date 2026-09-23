import os
import re

directories = [
    r'c:\Users\Raul\Downloads\erp\backend\modules\facturacion',
    r'c:\Users\Raul\Downloads\erp\backend\modules\inventario',
    r'c:\Users\Raul\Downloads\erp\backend\modules\planes'
]

translations = {
    r"'autorizada'": r"'authorized'",
    r"'no_autorizada'": r"'not_authorized'",
    r"'pendiente'": r"'pending'",
    r"'en_transito'": r"'in_transit'",
    r"'completada'": r"'completed'",
    r"'anulada'": r"'canceled'",
    r"'entrada'": r"'in'",
    r"'salida'": r"'out'",
    r"'ajuste'": r"'adjustment'",
    r"'devolucion'": r"'return'",
    r"'descuento'": r"'discount'",
    r"'anulacion'": r"'cancellation'",
    r"'facturacion'": r"'billing'",
    r"'ventas'": r"'sales'",
    r"'inventario'": r"'inventory'",
    r"'compras'": r"'purchases'",
    r"'contabilidad'": r"'accounting'",
    r"'basico'": r"'basic'",
    r"'profesional'": r"'professional'",
    r"raise ValueError\(['\"](.*)Stock insuficiente(.*)['\"]\)" : r"raise ValueError('\1Insufficient stock\2')",
}

def translate_files():
    for d in directories:
        for root, _, files in os.walk(d):
            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    original_content = content
                    for es, en in translations.items():
                        if es.startswith('raise'):
                            content = re.sub(es, en, content)
                        else:
                            # Replace exact string matches only for these enums
                            content = re.sub(es, en, content)
                            
                    if content != original_content:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(content)
                        print(f"Updated {filepath}")

if __name__ == '__main__':
    translate_files()
