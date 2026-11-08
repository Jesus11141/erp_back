"""
Generador de Excel parametrizado y profesional.
Usa los colores y parámetros de la empresa para dar formato ejecutivo premium.
"""
from io import BytesIO
from datetime import date
from openpyxl import Workbook
from openpyxl.styles import (
    Font, PatternFill, Alignment, Border, Side
)
from openpyxl.utils import get_column_letter


def _hex_to_openpyxl(hex_str: str) -> str:
    """Convierte #RRGGBB a RRGGBB para openpyxl."""
    return hex_str.lstrip('#').upper()


def _estilo_encabezado(color_hex: str):
    """Retorna estilos para la fila de encabezado de tabla."""
    fill = PatternFill(start_color=color_hex, end_color=color_hex, fill_type='solid')
    font = Font(bold=True, color='FFFFFF', size=11, name='Segoe UI')
    alineacion = Alignment(horizontal='center', vertical='center', wrap_text=True)
    return fill, font, alineacion


def _borde_delgado():
    lado = Side(style='thin', color='E0E0E0')
    return Border(left=lado, right=lado, top=lado, bottom=lado)


def _borde_total():
    """Borde estilo contable: línea superior delgada, línea inferior doble."""
    top_side = Side(style='thin', color='A0A0A0')
    bottom_side = Side(style='double', color='1A1A1A')
    return Border(top=top_side, bottom=bottom_side)


def _autoajustar_columnas(ws):
    """Auto-ajusta las columnas del Excel con un margin seguro para evitar '###'."""
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.value is not None:
                # Si el valor tiene formato de moneda, estimar longitud con formato
                val_str = str(cell.value)
                if isinstance(cell.value, float) or isinstance(cell.value, int):
                    val_str = f"${cell.value:,.2f}"
                max_len = max(max_len, len(val_str))
        ws.column_dimensions[col_letter].width = max(max_len + 4, 11)


def _aplicar_banner_titulo(ws, color_hex: str, titulo: str, num_columnas: int):
    """Aplica un banner de título corporativo elegante en las primeras 2 filas."""
    col_fin = get_column_letter(num_columnas)
    ws.merge_cells(f'A1:{col_fin}1')
    ws.merge_cells(f'A2:{col_fin}2')
    
    fill_banner = PatternFill(start_color=color_hex, end_color=color_hex, fill_type='solid')
    font_titulo = Font(bold=True, size=15, color='FFFFFF', name='Segoe UI')
    font_sub = Font(size=9.5, color='F0F0F0', italic=True, name='Segoe UI')
    align_center = Alignment(horizontal='center', vertical='center')
    
    # Rellenar todas las celdas del rango del banner para que el fondo sea uniforme
    for row in (1, 2):
        for col in range(1, num_columnas + 1):
            celda = ws.cell(row=row, column=col)
            celda.fill = fill_banner
            
    ws['A1'] = titulo.upper()
    ws['A1'].font = font_titulo
    ws['A1'].alignment = align_center
    
    ws['A2'] = f"Reporte Gerencial · Fecha de emisión: {date.today().strftime('%d/%m/%Y')} · Moneda: USD"
    ws['A2'].font = font_sub
    ws['A2'].alignment = align_center
    
    ws.row_dimensions[1].height = 28
    ws.row_dimensions[2].height = 18


def generate_sales_excel_report(sales: list, params: dict, tenant: dict) -> bytes:
    """Genera Excel ejecutivo de sales."""
    color_hex = _hex_to_openpyxl(tenant.get('primary_color', '#1976D2'))
    simbolo = params.get('general', {}).get('moneda_simbolo', {}).get('valor', '$')
    empresa = params.get('general', {}).get('empresa_nombre', {}).get('valor', tenant.get('name', ''))

    wb = Workbook()
    ws = wb.active
    ws.title = 'Sales'
    
    # Opciones de cuadrícula visibles
    ws.views.sheetView[0].showGridLines = True

    # 1. Banner corporativo
    _aplicar_banner_titulo(ws, color_hex, f"Reporte Detallado de Sales - {empresa}", 11)

    # 2. Encabezados de tabla
    encabezados = [
        '#', 'Fecha', 'Vendedor', 'Client', 
        'Subtotal Bruto', 'Descuento', 'Subtotal Neto', 'IVA', 'Total Venta', 
        'Método Pago', 'Estado'
    ]
    fill_header, font_header, align_header = _estilo_encabezado(color_hex)
    
    for col_idx, titulo in enumerate(encabezados, 1):
        celda = ws.cell(row=4, column=col_idx, value=titulo)
        celda.fill = fill_header
        celda.font = font_header
        celda.alignment = align_header
        celda.border = _borde_delgado()
    ws.row_dimensions[4].height = 25

    # 3. Rellenar Datos
    totales = {
        'bruto': 0.0,
        'discount': 0.0,
        'neto': 0.0,
        'iva': 0.0,
        'total': 0.0
    }
    
    for idx, v in enumerate(sales, 5):
        bruto = float(v.get('subtotal_bruto', 0.0))
        discount = float(v.get('discount', 0.0))
        neto = float(v.get('subtotal_neto', 0.0))
        iva = float(v.get('iva', 0.0))
        total = float(v.get('total', 0.0))
        
        totales['bruto'] += bruto
        totales['discount'] += discount
        totales['neto'] += neto
        totales['iva'] += iva
        totales['total'] += total

        datos_fila = [
            idx - 4,
            v.get('date', ''),
            v.get('vendedor', ''),
            v.get('client', ''),
            bruto,
            discount,
            neto,
            iva,
            total,
            v.get('metodo_pago', ''),
            v.get('status', '').upper()
        ]
        
        color_fila = 'F9FBFD' if idx % 2 == 0 else 'FFFFFF' # Zebra azulado muy suave
        fill_data = PatternFill(start_color=color_fila, end_color=color_fila, fill_type='solid')
        
        for col_idx, valor in enumerate(datos_fila, 1):
            celda = ws.cell(row=idx, column=col_idx, value=valor)
            celda.fill = fill_data
            celda.border = _borde_delgado()
            celda.font = Font(size=9.5, name='Segoe UI')
            
            # Alineaciones
            if col_idx in (1, 2, 10, 11):
                celda.alignment = Alignment(horizontal='center', vertical='center')
            else:
                celda.alignment = Alignment(horizontal='left', vertical='center')
                
            # Formatos de moneda
            if col_idx in (5, 6, 7, 8, 9):
                celda.number_format = f'"{simbolo}"#,##0.00'
                celda.alignment = Alignment(horizontal='right', vertical='center')
                
        ws.row_dimensions[idx].height = 20

    # 4. Fila de Totales Generales
    total_row = len(sales) + 5
    
    # Rellenar fondo de la fila de totales
    fill_total = PatternFill(start_color='F2F2F2', end_color='F2F2F2', fill_type='solid')
    for col_idx in range(1, 12):
        celda = ws.cell(row=total_row, column=col_idx)
        celda.fill = fill_total
        celda.border = _borde_total()
        
    ws.cell(row=total_row, column=4, value='TOTALES GENERALES').font = Font(bold=True, size=10, name='Segoe UI')
    ws.cell(row=total_row, column=4).alignment = Alignment(horizontal='right', vertical='center')
    
    col_totales = {5: 'bruto', 6: 'discount', 7: 'neto', 8: 'iva', 9: 'total'}
    for col_idx, key in col_totales.items():
        celda = ws.cell(row=total_row, column=col_idx, value=totales[key])
        celda.font = Font(bold=True, size=10.5, name='Segoe UI', color=color_hex)
        celda.number_format = f'"{simbolo}"#,##0.00'
        celda.alignment = Alignment(horizontal='right', vertical='center')
        
    ws.row_dimensions[total_row].height = 24

    _autoajustar_columnas(ws)
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def generate_inventory_excel_report(productos: list, params: dict, tenant: dict) -> bytes:
    """Genera Excel ejecutivo de inventory con valorizaciones de activos."""
    color_hex = _hex_to_openpyxl(tenant.get('primary_color', '#1976D2'))
    simbolo = params.get('general', {}).get('moneda_simbolo', {}).get('valor', '$')
    empresa = params.get('general', {}).get('empresa_nombre', {}).get('valor', tenant.get('name', ''))

    wb = Workbook()
    ws = wb.active
    ws.title = 'Inventory'
    ws.views.sheetView[0].showGridLines = True

    # 1. Banner
    _aplicar_banner_titulo(ws, color_hex, f"Reporte y Valoración de Inventory - {empresa}", 10)

    # 2. Encabezados
    encabezados = [
        'Código', 'Nombre del Product', 'Categoría', 'Stock Actual', 'Stock Mínimo',
        'Costo Unitario', 'Precio Venta', 'Total Costo Activo', 'Total Valor Venta', 'Estado'
    ]
    fill_header, font_header, align_header = _estilo_encabezado(color_hex)
    
    for col_idx, titulo in enumerate(encabezados, 1):
        celda = ws.cell(row=4, column=col_idx, value=titulo)
        celda.fill = fill_header
        celda.font = font_header
        celda.alignment = align_header
        celda.border = _borde_delgado()
    ws.row_dimensions[4].height = 25

    # 3. Rellenar Datos
    totales = {
        'stock': 0.0,
        'costo_activo': 0.0,
        'valor_venta': 0.0
    }
    
    for idx, prod in enumerate(productos, 5):
        stock_actual = float(prod.get('stock_actual', 0.0))
        stock_minimo = float(prod.get('stock_minimo', 0.0))
        p_compra = float(prod.get('precio_compra', 0.0))
        p_venta = float(prod.get('precio_venta', 0.0))
        
        costo_activo = stock_actual * p_compra
        valor_venta = stock_actual * p_venta
        
        bajo_stock = stock_actual <= stock_minimo
        status = '⚠️ BAJO STOCK' if bajo_stock else 'OK'
        
        totales['stock'] += stock_actual
        totales['costo_activo'] += costo_activo
        totales['valor_venta'] += valor_venta

        datos_fila = [
            prod.get('codigo', ''),
            prod.get('name', ''),
            prod.get('categoria', 'General'),
            stock_actual,
            stock_minimo,
            p_compra,
            p_venta,
            costo_activo,
            valor_venta,
            status
        ]
        
        # Color suave de alerta para bajo stock, de lo contrario zebra estándar
        if bajo_stock:
            color_fila = 'FFF5E6' # Naranja pastel suave
        else:
            color_fila = 'F9FBFD' if idx % 2 == 0 else 'FFFFFF'
            
        fill_data = PatternFill(start_color=color_fila, end_color=color_fila, fill_type='solid')
        
        for col_idx, valor in enumerate(datos_fila, 1):
            celda = ws.cell(row=idx, column=col_idx, value=valor)
            celda.fill = fill_data
            celda.border = _borde_delgado()
            celda.font = Font(size=9.5, name='Segoe UI')
            
            if col_idx in (1, 3, 10):
                celda.alignment = Alignment(horizontal='center', vertical='center')
            else:
                celda.alignment = Alignment(horizontal='left', vertical='center')
                
            if col_idx in (4, 5):
                celda.number_format = '#,##0.00'
                celda.alignment = Alignment(horizontal='right', vertical='center')
                
            if col_idx in (6, 7, 8, 9):
                celda.number_format = f'"{simbolo}"#,##0.00'
                celda.alignment = Alignment(horizontal='right', vertical='center')
                
            if col_idx == 10 and bajo_stock:
                celda.font = Font(bold=True, color='D35400', size=9.5, name='Segoe UI')
                
        ws.row_dimensions[idx].height = 20

    # 4. Fila de Totales
    total_row = len(productos) + 5
    fill_total = PatternFill(start_color='F2F2F2', end_color='F2F2F2', fill_type='solid')
    
    for col_idx in range(1, 11):
        celda = ws.cell(row=total_row, column=col_idx)
        celda.fill = fill_total
        celda.border = _borde_total()
        
    ws.cell(row=total_row, column=3, value='VALORIZACIÓN TOTAL').font = Font(bold=True, size=10, name='Segoe UI')
    ws.cell(row=total_row, column=3).alignment = Alignment(horizontal='right', vertical='center')
    
    # Stock total
    celda_stock = ws.cell(row=total_row, column=4, value=totales['stock'])
    celda_stock.font = Font(bold=True, size=10, name='Segoe UI')
    celda_stock.number_format = '#,##0.00'
    celda_stock.alignment = Alignment(horizontal='right', vertical='center')
    
    # Costo activo total
    celda_costo = ws.cell(row=total_row, column=8, value=totales['costo_activo'])
    celda_costo.font = Font(bold=True, size=10.5, name='Segoe UI', color=color_hex)
    celda_costo.number_format = f'"{simbolo}"#,##0.00'
    celda_costo.alignment = Alignment(horizontal='right', vertical='center')
    
    # Valor venta total
    celda_venta = ws.cell(row=total_row, column=9, value=totales['valor_venta'])
    celda_venta.font = Font(bold=True, size=10.5, name='Segoe UI', color=color_hex)
    celda_venta.number_format = f'"{simbolo}"#,##0.00'
    celda_venta.alignment = Alignment(horizontal='right', vertical='center')
    
    ws.row_dimensions[total_row].height = 24

    _autoajustar_columnas(ws)
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def generate_clients_excel_report(clients: list, params: dict, tenant: dict) -> bytes:
    """Genera Excel corporativo de Clientes."""
    color_hex = _hex_to_openpyxl(tenant.get('primary_color', '#1976D2'))
    empresa = params.get('general', {}).get('empresa_nombre', {}).get('valor', tenant.get('name', ''))

    wb = Workbook()
    ws = wb.active
    ws.title = 'Clientes'
    ws.views.sheetView[0].showGridLines = True

    # 1. Banner
    _aplicar_banner_titulo(ws, color_hex, f"Reporte General de Clientes - {empresa}", 6)

    # 2. Encabezados
    encabezados = ['Nombre del Client', 'Email / Correo', 'Teléfono', 'RUC / Cédula', 'Dirección', 'Estado']
    fill_header, font_header, align_header = _estilo_encabezado(color_hex)
    
    for col_idx, titulo in enumerate(encabezados, 1):
        celda = ws.cell(row=4, column=col_idx, value=titulo)
        celda.fill = fill_header
        celda.font = font_header
        celda.alignment = align_header
        celda.border = _borde_delgado()
    ws.row_dimensions[4].height = 25

    # 3. Rellenar Datos
    for idx, c in enumerate(clients, 5):
        color_fila = 'F9FBFD' if idx % 2 == 0 else 'FFFFFF'
        fill_data = PatternFill(start_color=color_fila, end_color=color_fila, fill_type='solid')
        
        datos_fila = [
            c.get('name', ''),
            c.get('email', ''),
            c.get('telefono', ''),
            c.get('rfc', ''),
            c.get('direccion', ''),
            c.get('activo', 'Activo')
        ]
        
        for col_idx, valor in enumerate(datos_fila, 1):
            celda = ws.cell(row=idx, column=col_idx, value=valor)
            celda.fill = fill_data
            celda.border = _borde_delgado()
            celda.font = Font(size=9.5, name='Segoe UI')
            
            if col_idx in (3, 4, 6):
                celda.alignment = Alignment(horizontal='center', vertical='center')
            else:
                celda.alignment = Alignment(horizontal='left', vertical='center')
                
            if col_idx == 6:
                es_activo = valor == 'Activo'
                celda.font = Font(bold=True, color='27AE60' if es_activo else '95A5A6', size=9.5, name='Segoe UI')
                
        ws.row_dimensions[idx].height = 20

    _autoajustar_columnas(ws)
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def generate_payroll_excel_report(nominas: list, params: dict, tenant: dict) -> bytes:
    """Genera Excel ejecutivo de nóminas y pagos RRHH."""
    color_hex = _hex_to_openpyxl(tenant.get('primary_color', '#1976D2'))
    simbolo = params.get('general', {}).get('moneda_simbolo', {}).get('valor', '$')
    empresa = params.get('general', {}).get('empresa_nombre', {}).get('valor', tenant.get('name', ''))

    wb = Workbook()
    ws = wb.active
    ws.title = 'Nóminas'
    ws.views.sheetView[0].showGridLines = True

    # 1. Banner
    _aplicar_banner_titulo(ws, color_hex, f"Reporte Consolidado de Nómina - {empresa}", 7)

    # 2. Encabezados
    encabezados = ['Empleado', 'Período Inicio', 'Período Fin', 'Salario Base', 'Bonos', 'Deducciones', 'Neto a Recibir']
    fill_header, font_header, align_header = _estilo_encabezado(color_hex)
    
    for col_idx, titulo in enumerate(encabezados, 1):
        celda = ws.cell(row=4, column=col_idx, value=titulo)
        celda.fill = fill_header
        celda.font = font_header
        celda.alignment = align_header
        celda.border = _borde_delgado()
    ws.row_dimensions[4].height = 25

    # 3. Rellenar Datos
    totales = {
        'salario': 0.0,
        'bonos': 0.0,
        'deducciones': 0.0,
        'neto': 0.0
    }
    
    for idx, n in enumerate(nominas, 5):
        s_base = float(n.get('salario_base', 0.0))
        bonos = float(n.get('bonos', 0.0))
        deducciones = float(n.get('deducciones', 0.0))
        neto = float(n.get('total_neto', 0.0))
        
        totales['salario'] += s_base
        totales['bonos'] += bonos
        totales['deducciones'] += deducciones
        totales['neto'] += neto

        datos_fila = [
            n.get('empleado', ''),
            n.get('periodo_inicio', ''),
            n.get('periodo_fin', ''),
            s_base,
            bonos,
            deducciones,
            neto
        ]
        
        color_fila = 'F9FBFD' if idx % 2 == 0 else 'FFFFFF'
        fill_data = PatternFill(start_color=color_fila, end_color=color_fila, fill_type='solid')
        
        for col_idx, valor in enumerate(datos_fila, 1):
            celda = ws.cell(row=idx, column=col_idx, value=valor)
            celda.fill = fill_data
            celda.border = _borde_delgado()
            celda.font = Font(size=9.5, name='Segoe UI')
            
            if col_idx in (2, 3):
                celda.alignment = Alignment(horizontal='center', vertical='center')
            else:
                celda.alignment = Alignment(horizontal='left', vertical='center')
                
            if col_idx in (4, 5, 6, 7):
                celda.number_format = f'"{simbolo}"#,##0.00'
                celda.alignment = Alignment(horizontal='right', vertical='center')
                
        ws.row_dimensions[idx].height = 20

    # 4. Fila de Totales
    total_row = len(nominas) + 5
    fill_total = PatternFill(start_color='F2F2F2', end_color='F2F2F2', fill_type='solid')
    
    for col_idx in range(1, 8):
        celda = ws.cell(row=total_row, column=col_idx)
        celda.fill = fill_total
        celda.border = _borde_total()
        
    ws.cell(row=total_row, column=3, value='TOTAL DESEMBOLSADO').font = Font(bold=True, size=10, name='Segoe UI')
    ws.cell(row=total_row, column=3).alignment = Alignment(horizontal='right', vertical='center')
    
    col_totales = {4: 'salario', 5: 'bonos', 6: 'deducciones', 7: 'neto'}
    for col_idx, key in col_totales.items():
        celda = ws.cell(row=total_row, column=col_idx, value=totales[key])
        celda.font = Font(bold=True, size=10.5, name='Segoe UI', color=color_hex)
        celda.number_format = f'"{simbolo}"#,##0.00'
        celda.alignment = Alignment(horizontal='right', vertical='center')
        
    ws.row_dimensions[total_row].height = 24

    _autoajustar_columnas(ws)
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def generate_profit_excel_report(datos: list, params: dict, tenant: dict) -> bytes:
    """Genera reporte ejecutivo de Utilidad y Margen de Ganancias."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Ganancias y Margen"
    
    color_hex = _hex_to_openpyxl(tenant.get('primary_color', '#1976D2'))
    simbolo = params.get('general', {}).get('moneda_simbolo', {}).get('valor', '$')
    
    _aplicar_banner_titulo(ws, color_hex, "REPORTE DE UTILIDAD Y MARGEN DE GANANCIA", 9)
    
    headers = [
        "Venta ID", "Fecha", "Código Product", "Descripción", 
        "Cant.", "Ingreso Neto", "Costo Total", "Ganancia", "Margen %"
    ]
    
    # Encabezados
    fill, font, align = _estilo_encabezado(color_hex)
    for col_idx, text in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col_idx, value=text)
        cell.fill = fill
        cell.font = font
        cell.alignment = align
    ws.row_dimensions[4].height = 28
    
    # Datos
    borde = _borde_delgado()
    total_ingreso = 0
    total_costo = 0
    total_ganancia = 0
    
    for idx, row in enumerate(datos, 5):
        total_ingreso += row['revenue']
        total_costo += row['cost']
        total_ganancia += row['profit']
        
        ws.cell(row=idx, column=1, value=row['sale_id']).alignment = Alignment(horizontal='center')
        ws.cell(row=idx, column=2, value=row['date']).alignment = Alignment(horizontal='center')
        ws.cell(row=idx, column=3, value=row['product_code']).alignment = Alignment(horizontal='center')
        ws.cell(row=idx, column=4, value=row['product_name'])
        
        c_qty = ws.cell(row=idx, column=5, value=row['quantity'])
        c_qty.number_format = '#,##0.00'
        c_qty.alignment = Alignment(horizontal='right')
        
        c_rev = ws.cell(row=idx, column=6, value=row['revenue'])
        c_rev.number_format = f'"{simbolo}"#,##0.00'
        c_rev.alignment = Alignment(horizontal='right')
        
        c_cost = ws.cell(row=idx, column=7, value=row['cost'])
        c_cost.number_format = f'"{simbolo}"#,##0.00'
        c_cost.alignment = Alignment(horizontal='right')
        
        c_prof = ws.cell(row=idx, column=8, value=row['profit'])
        c_prof.number_format = f'"{simbolo}"#,##0.00'
        c_prof.alignment = Alignment(horizontal='right')
        
        c_marg = ws.cell(row=idx, column=9, value=row['margin'])
        c_marg.number_format = '0.00"%"'
        c_marg.alignment = Alignment(horizontal='right')
        
        for col in range(1, 10):
            ws.cell(row=idx, column=col).border = borde
            ws.cell(row=idx, column=col).font = Font(name='Segoe UI', size=9.5)
        ws.row_dimensions[idx].height = 20

    # Fila de Totales
    total_row = len(datos) + 5
    fill_total = PatternFill(start_color='F2F2F2', end_color='F2F2F2', fill_type='solid')
    for col_idx in range(1, 10):
        cell = ws.cell(row=total_row, column=col_idx)
        cell.fill = fill_total
        cell.border = _borde_total()
        
    ws.cell(row=total_row, column=4, value='TOTAL GENERAL').font = Font(bold=True, size=10, name='Segoe UI')
    ws.cell(row=total_row, column=4).alignment = Alignment(horizontal='right', vertical='center')
    
    totales = {6: total_ingreso, 7: total_costo, 8: total_ganancia}
    for col_idx, val in totales.items():
        cell = ws.cell(row=total_row, column=col_idx, value=val)
        cell.font = Font(bold=True, size=10.5, name='Segoe UI', color=color_hex)
        cell.number_format = f'"{simbolo}"#,##0.00'
        cell.alignment = Alignment(horizontal='right', vertical='center')
        
    avg_margin = (total_ganancia / total_ingreso * 100) if total_ingreso > 0 else 0
    cell_avg = ws.cell(row=total_row, column=9, value=avg_margin)
    cell_avg.font = Font(bold=True, size=10.5, name='Segoe UI', color=color_hex)
    cell_avg.number_format = '0.00"%"'
    cell_avg.alignment = Alignment(horizontal='right', vertical='center')
    
    ws.row_dimensions[total_row].height = 24
    _autoajustar_columnas(ws)
    
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def generate_top_products_excel_report(datos: list, params: dict, tenant: dict) -> bytes:
    """Genera reporte de Ranking de los Productos más Vendidos."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Ranking Productos"
    
    color_hex = _hex_to_openpyxl(tenant.get('primary_color', '#1976D2'))
    simbolo = params.get('general', {}).get('moneda_simbolo', {}).get('valor', '$')
    
    _aplicar_banner_titulo(ws, color_hex, "RANKING DE PRODUCTOS MÁS VENDIDOS (TOP)", 5)
    
    headers = ["Nro.", "Código", "Descripción", "Cantidad Vendida", "Total Recaudado"]
    
    fill, font, align = _estilo_encabezado(color_hex)
    for col_idx, text in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col_idx, value=text)
        cell.fill = fill
        cell.font = font
        cell.alignment = align
    ws.row_dimensions[4].height = 28
    
    borde = _borde_delgado()
    total_qty = 0
    total_rev = 0
    
    for idx, row in enumerate(datos, 5):
        total_qty += row['quantity']
        total_rev += row['revenue']
        
        ws.cell(row=idx, column=1, value=idx-4).alignment = Alignment(horizontal='center')
        ws.cell(row=idx, column=2, value=row['code']).alignment = Alignment(horizontal='center')
        ws.cell(row=idx, column=3, value=row['name'])
        
        c_qty = ws.cell(row=idx, column=4, value=row['quantity'])
        c_qty.number_format = '#,##0.00'
        c_qty.alignment = Alignment(horizontal='right')
        
        c_rev = ws.cell(row=idx, column=5, value=row['revenue'])
        c_rev.number_format = f'"{simbolo}"#,##0.00'
        c_rev.alignment = Alignment(horizontal='right')
        
        for col in range(1, 6):
            ws.cell(row=idx, column=col).border = borde
            ws.cell(row=idx, column=col).font = Font(name='Segoe UI', size=9.5)
        ws.row_dimensions[idx].height = 20

    # Totales
    total_row = len(datos) + 5
    fill_total = PatternFill(start_color='F2F2F2', end_color='F2F2F2', fill_type='solid')
    for col_idx in range(1, 6):
        cell = ws.cell(row=total_row, column=col_idx)
        cell.fill = fill_total
        cell.border = _borde_total()
        
    ws.cell(row=total_row, column=3, value='TOTAL').font = Font(bold=True, size=10, name='Segoe UI')
    ws.cell(row=total_row, column=3).alignment = Alignment(horizontal='right', vertical='center')
    
    c_tot_qty = ws.cell(row=total_row, column=4, value=total_qty)
    c_tot_qty.font = Font(bold=True, size=10.5, name='Segoe UI', color=color_hex)
    c_tot_qty.number_format = '#,##0.00'
    c_tot_qty.alignment = Alignment(horizontal='right', vertical='center')
    
    c_tot_rev = ws.cell(row=total_row, column=5, value=total_rev)
    c_tot_rev.font = Font(bold=True, size=10.5, name='Segoe UI', color=color_hex)
    c_tot_rev.number_format = f'"{simbolo}"#,##0.00'
    c_tot_rev.alignment = Alignment(horizontal='right', vertical='center')
    
    ws.row_dimensions[total_row].height = 24
    _autoajustar_columnas(ws)
    
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def generate_cash_closure_excel(closing: dict, params: dict, tenant: dict) -> bytes:
    """Genera reporte ejecutivo en Excel para auditoría de Cierre de CashRegister."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Cierre de CashRegister"
    
    color_hex = _hex_to_openpyxl(tenant.get('primary_color', '#1976D2'))
    simbolo = params.get('general', {}).get('moneda_simbolo', {}).get('valor', '$')
    
    _aplicar_banner_titulo(ws, color_hex, "REPORTE DE CIERRE Y AUDITORÍA DE CAJA", 4)
    
    # Datos generales
    ws.cell(row=4, column=1, value="Caja:").font = Font(bold=True, name='Segoe UI')
    ws.cell(row=4, column=2, value=closing['caja_nombre'])
    ws.cell(row=4, column=3, value="Cajero:").font = Font(bold=True, name='Segoe UI')
    ws.cell(row=4, column=4, value=closing['cajero'])
    
    ws.cell(row=5, column=1, value="Fecha Apertura:").font = Font(bold=True, name='Segoe UI')
    ws.cell(row=5, column=2, value=closing['fecha_apertura'])
    ws.cell(row=5, column=3, value="Fecha Cierre:").font = Font(bold=True, name='Segoe UI')
    ws.cell(row=5, column=4, value=closing['fecha_cierre'])
    
    # Separador
    for r in range(4, 6):
        ws.row_dimensions[r].height = 20
        
    # Tabla de balance
    headers = ["Concepto de Transacción", "Monto"]
    fill, font, align = _estilo_encabezado(color_hex)
    for col_idx, text in enumerate(headers, 1):
        cell = ws.cell(row=7, column=col_idx, value=text)
        cell.fill = fill
        cell.font = font
        cell.alignment = align
    ws.row_dimensions[7].height = 28
    
    total_ingresos = float(closing.get('total_ingresos') or 0.0)
    total_egresos = float(closing.get('total_egresos') or 0.0)
    
    conceptos = [
        ("Saldo Inicial de Apertura", closing['saldo_inicial']),
        ("(+) Ventas en Efectivo", closing['total_efectivo']),
        ("(+) Ventas con Tarjeta de Crédito", closing['total_tarjeta']),
        ("(+) Ventas por Transferencia Bancaria", closing['total_transferencia']),
        ("TOTAL VENTAS REGISTRADAS", closing['total_sales']),
        ("(+) Ingresos / Entradas Manuales de Caja", total_ingresos),
        ("(-) Retiros / Salidas Manuales de Caja", total_egresos),
        ("SALDO ESPERADO EN CAJA (Inicial + Efec. + Ing. - Sal.)", closing['saldo_esperado']),
        ("SALDO CONTADO FÍSICAMENTE", closing['saldo_contado']),
    ]
    
    borde = _borde_delgado()
    for idx, (label, val) in enumerate(conceptos, 8):
        ws.cell(row=idx, column=1, value=label)
        c_val = ws.cell(row=idx, column=2, value=val)
        c_val.number_format = f'"{simbolo}"#,##0.00'
        c_val.alignment = Alignment(horizontal='right')
        
        ws.cell(row=idx, column=1).border = borde
        ws.cell(row=idx, column=2).border = borde
        ws.row_dimensions[idx].height = 20
        
        if label.startswith("TOTAL VENTAS") or label.startswith("SALDO "):
            ws.cell(row=idx, column=1).font = Font(bold=True, name='Segoe UI')
            ws.cell(row=idx, column=2).font = Font(bold=True, name='Segoe UI', color=color_hex)
            
    next_row = 8 + len(conceptos)
    
    # Fila de diferencia
    ws.cell(row=next_row, column=1, value="DIFERENCIA DE CUADRE:").font = Font(bold=True, name='Segoe UI')
    c_dif = ws.cell(row=next_row, column=2, value=closing['diferencia'])
    c_dif.font = Font(bold=True, name='Segoe UI', color='C62828' if closing['diferencia'] < 0 else ('2E7D32' if closing['diferencia'] == 0 else 'E65100'))
    c_dif.number_format = f'"{simbolo}"#,##0.00'
    c_dif.alignment = Alignment(horizontal='right')
    ws.cell(row=next_row, column=1).border = _borde_total()
    ws.cell(row=next_row, column=2).border = _borde_total()
    ws.row_dimensions[next_row].height = 24
    
    next_row += 2
    
    # Desglose de efectivo
    closing_breakdown = closing.get('closing_breakdown') or {}
    efectivo_desglose = closing_breakdown.get('efectivo_desglose')
    if efectivo_desglose:
        bills = efectivo_desglose.get('bills', {})
        coins = efectivo_desglose.get('coins', {})
        if bills or coins:
            ws.cell(row=next_row, column=1, value="Desglose Físico de Efectivo:").font = Font(bold=True, name='Segoe UI', color=color_hex)
            next_row += 1
            ws.cell(row=next_row, column=1, value="Denominación").font = font
            ws.cell(row=next_row, column=1).fill = fill
            ws.cell(row=next_row, column=2, value="Cantidad").font = font
            ws.cell(row=next_row, column=2).fill = fill
            ws.cell(row=next_row, column=3, value="Subtotal").font = font
            ws.cell(row=next_row, column=3).fill = fill
            next_row += 1
            
            total_desglose = 0.0
            for k, v in bills.items():
                if int(v) > 0:
                    sub = float(k) * int(v)
                    total_desglose += sub
                    ws.cell(row=next_row, column=1, value=f"Billete {simbolo}{k}")
                    ws.cell(row=next_row, column=2, value=int(v)).alignment = Alignment(horizontal='center')
                    c_sub = ws.cell(row=next_row, column=3, value=sub)
                    c_sub.number_format = f'"{simbolo}"#,##0.00'
                    c_sub.alignment = Alignment(horizontal='right')
                    next_row += 1
            for k, v in coins.items():
                if int(v) > 0:
                    sub = float(k) * int(v)
                    total_desglose += sub
                    ws.cell(row=next_row, column=1, value=f"Moneda {simbolo}{k}")
                    ws.cell(row=next_row, column=2, value=int(v)).alignment = Alignment(horizontal='center')
                    c_sub = ws.cell(row=next_row, column=3, value=sub)
                    c_sub.number_format = f'"{simbolo}"#,##0.00'
                    c_sub.alignment = Alignment(horizontal='right')
                    next_row += 1
            
            ws.cell(row=next_row, column=1, value="TOTAL EFECTIVO CONTADO").font = Font(bold=True, name='Segoe UI')
            c_tot = ws.cell(row=next_row, column=3, value=total_desglose)
            c_tot.font = Font(bold=True, name='Segoe UI', color=color_hex)
            c_tot.number_format = f'"{simbolo}"#,##0.00'
            c_tot.alignment = Alignment(horizontal='right')
            next_row += 2
            
    # Observaciones
    ws.cell(row=next_row, column=1, value="Observaciones de Cierre:").font = Font(bold=True, name='Segoe UI', color=color_hex)
    ws.cell(row=next_row+1, column=1, value=str(closing.get('observaciones') or 'Sin observaciones registradas.'))
    
    _autoajustar_columnas(ws)
    
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def generate_closure_summary_excel(report_data: dict, params: dict, tenant: dict) -> bytes:
    color_hex = _hex_to_openpyxl(tenant.get('primary_color', '#1976D2'))
    simbolo = params.get('general', {}).get('moneda_simbolo', {}).get('valor', '$')
    meta = report_data['meta']
    details = report_data['details']
    totals = report_data['totals']

    wb = Workbook()
    ws = wb.active
    ws.title = 'Summary Cierres'
    ws.views.sheetView[0].showGridLines = True

    # 1. Banner
    title_text = "Reporte de Cierres de Caja"
    if meta['is_employee_report']:
        title_text = f"Reporte de Ventas por Trabajador: {meta['employee_name']}"
    _aplicar_banner_titulo(ws, color_hex, title_text, 14 if not meta['is_employee_report'] else 6)

    # 2. Metadata Info Rows
    ws['A4'] = "Filtros Aplicados:"
    ws['A4'].font = Font(bold=True, size=10, name='Segoe UI')
    ws['B4'] = f"Temporalidad: {meta['period_type'].upper()} | Rango: {meta['start_date']} al {meta['end_date']}"
    ws['B4'].font = Font(size=10, name='Segoe UI')
    
    ws['A5'] = "Local / Caja:"
    ws['A5'].font = Font(bold=True, size=10, name='Segoe UI')
    ws['B5'] = f"{meta['branch_name']} / {meta['register_name']}"
    ws['B5'].font = Font(size=10, name='Segoe UI')

    ws.row_dimensions[4].height = 18
    ws.row_dimensions[5].height = 18

    # 3. Table Header
    borde = _borde_delgado()
    fill_hdr, font_hdr, align_hdr = _estilo_encabezado(color_hex)
    
    start_row = 7
    
    if meta['is_employee_report']:
        encabezados = ["CashRegister Física / Turno", "Ef. Sales", "Tj. Sales", "Tr. Sales", "Cant. Sales", "Total Recaudado"]
        for idx, h in enumerate(encabezados, 1):
            cell = ws.cell(row=start_row, column=idx, value=h)
            cell.fill = fill_hdr
            cell.font = font_hdr
            cell.alignment = align_hdr
            cell.border = borde
        
        ws.row_dimensions[start_row].height = 24
        
        # Write rows
        current_row = start_row + 1
        for d in details:
            ws.cell(row=current_row, column=1, value=d['register_name']).alignment = Alignment(horizontal='left')
            
            c_ef = ws.cell(row=current_row, column=2, value=d['cash'])
            c_ef.number_format = f'"{simbolo}"#,##0.00'
            c_ef.alignment = Alignment(horizontal='right')
            
            c_tj = ws.cell(row=current_row, column=3, value=d['card'])
            c_tj.number_format = f'"{simbolo}"#,##0.00'
            c_tj.alignment = Alignment(horizontal='right')
            
            c_tr = ws.cell(row=current_row, column=4, value=d['transfer'])
            c_tr.number_format = f'"{simbolo}"#,##0.00'
            c_tr.alignment = Alignment(horizontal='right')
            
            c_cant = ws.cell(row=current_row, column=5, value=d['sales_count'])
            c_cant.alignment = Alignment(horizontal='center')
            
            c_tot = ws.cell(row=current_row, column=6, value=d['total'])
            c_tot.number_format = f'"{simbolo}"#,##0.00'
            c_tot.alignment = Alignment(horizontal='right')
            
            for col in range(1, 7):
                ws.cell(row=current_row, column=col).border = borde
                ws.cell(row=current_row, column=col).font = Font(name='Segoe UI', size=10)
                
            ws.row_dimensions[current_row].height = 20
            current_row += 1
            
        # Write totals row
        ws.cell(row=current_row, column=1, value="TOTALES").font = Font(bold=True, name='Segoe UI')
        
        c_ef = ws.cell(row=current_row, column=2, value=totals['cash'])
        c_ef.number_format = f'"{simbolo}"#,##0.00'
        c_ef.alignment = Alignment(horizontal='right')
        c_ef.font = Font(bold=True, name='Segoe UI')
        
        c_tj = ws.cell(row=current_row, column=3, value=totals['card'])
        c_tj.number_format = f'"{simbolo}"#,##0.00'
        c_tj.alignment = Alignment(horizontal='right')
        c_tj.font = Font(bold=True, name='Segoe UI')
        
        c_tr = ws.cell(row=current_row, column=4, value=totals['transfer'])
        c_tr.number_format = f'"{simbolo}"#,##0.00'
        c_tr.alignment = Alignment(horizontal='right')
        c_tr.font = Font(bold=True, name='Segoe UI')
        
        c_cant = ws.cell(row=current_row, column=5, value=totals['sales_count'])
        c_cant.alignment = Alignment(horizontal='center')
        c_cant.font = Font(bold=True, name='Segoe UI')
        
        c_tot = ws.cell(row=current_row, column=6, value=totals['total'])
        c_tot.number_format = f'"{simbolo}"#,##0.00'
        c_tot.alignment = Alignment(horizontal='right')
        c_tot.font = Font(bold=True, name='Segoe UI', color=color_hex)
        
        for col in range(1, 7):
            ws.cell(row=current_row, column=col).border = _borde_total()
            
        ws.row_dimensions[current_row].height = 24
        
    else:
        headers = ["Caja", "Cajero", "Apertura", "Cierre", "Saldo Inicial", "Efectivo", "Tarjeta", "Transferencia", "Total Ventas", "Núm Ventas", "Esperado", "Contado", "Diferencia", "Observaciones"]
        for idx, h in enumerate(headers, 1):
            cell = ws.cell(row=start_row, column=idx, value=h)
            cell.fill = fill_hdr
            cell.font = font_hdr
            cell.alignment = align_hdr
            cell.border = borde
            
        ws.row_dimensions[start_row].height = 24
        
        # Write rows
        current_row = start_row + 1
        for d in details:
            ws.cell(row=current_row, column=1, value=d['register_name'])
            ws.cell(row=current_row, column=2, value=d['cashier_name'])
            ws.cell(row=current_row, column=3, value=d['opened_at']).alignment = Alignment(horizontal='center')
            ws.cell(row=current_row, column=4, value=d['closed_at']).alignment = Alignment(horizontal='center')
            
            c_ini = ws.cell(row=current_row, column=5, value=d['initial_balance'])
            c_ini.number_format = f'"{simbolo}"#,##0.00'
            c_ini.alignment = Alignment(horizontal='right')
            
            c_ef = ws.cell(row=current_row, column=6, value=d['total_cash'])
            c_ef.number_format = f'"{simbolo}"#,##0.00'
            c_ef.alignment = Alignment(horizontal='right')
            
            c_tj = ws.cell(row=current_row, column=7, value=d['total_card'])
            c_tj.number_format = f'"{simbolo}"#,##0.00'
            c_tj.alignment = Alignment(horizontal='right')
            
            c_tr = ws.cell(row=current_row, column=8, value=d['total_transfer'])
            c_tr.number_format = f'"{simbolo}"#,##0.00'
            c_tr.alignment = Alignment(horizontal='right')
            
            c_tot = ws.cell(row=current_row, column=9, value=d['total_sales'])
            c_tot.number_format = f'"{simbolo}"#,##0.00'
            c_tot.alignment = Alignment(horizontal='right')
            
            c_num = ws.cell(row=current_row, column=10, value=d['sales_count'])
            c_num.alignment = Alignment(horizontal='center')
            
            c_esp = ws.cell(row=current_row, column=11, value=d['expected_balance'])
            c_esp.number_format = f'"{simbolo}"#,##0.00'
            c_esp.alignment = Alignment(horizontal='right')
            
            c_con = ws.cell(row=current_row, column=12, value=d['counted_balance'])
            c_con.number_format = f'"{simbolo}"#,##0.00'
            c_con.alignment = Alignment(horizontal='right')
            
            c_dif = ws.cell(row=current_row, column=13, value=d['difference'])
            c_dif.number_format = f'"{simbolo}"#,##0.00'
            c_dif.alignment = Alignment(horizontal='right')
            c_dif.font = Font(bold=True, name='Segoe UI', color='C62828' if d['difference'] < 0 else ('2E7D32' if d['difference'] == 0 else 'E65100'))
            
            ws.cell(row=current_row, column=14, value=d['observations'])
            
            for col in range(1, 15):
                ws.cell(row=current_row, column=col).border = borde
                if col != 13:
                    ws.cell(row=current_row, column=col).font = Font(name='Segoe UI', size=10)
                
            ws.row_dimensions[current_row].height = 20
            current_row += 1
            
        # Write totals row
        ws.cell(row=current_row, column=1, value="TOTALES").font = Font(bold=True, name='Segoe UI')
        ws.cell(row=current_row, column=2, value="")
        ws.cell(row=current_row, column=3, value="")
        ws.cell(row=current_row, column=4, value="")
        
        c_ini = ws.cell(row=current_row, column=5, value=totals['initial_balance'])
        c_ini.number_format = f'"{simbolo}"#,##0.00'
        c_ini.alignment = Alignment(horizontal='right')
        c_ini.font = Font(bold=True, name='Segoe UI')
        
        c_ef = ws.cell(row=current_row, column=6, value=totals['total_cash'])
        c_ef.number_format = f'"{simbolo}"#,##0.00'
        c_ef.alignment = Alignment(horizontal='right')
        c_ef.font = Font(bold=True, name='Segoe UI')
        
        c_tj = ws.cell(row=current_row, column=7, value=totals['total_card'])
        c_tj.number_format = f'"{simbolo}"#,##0.00'
        c_tj.alignment = Alignment(horizontal='right')
        c_tj.font = Font(bold=True, name='Segoe UI')
        
        c_tr = ws.cell(row=current_row, column=8, value=totals['total_transfer'])
        c_tr.number_format = f'"{simbolo}"#,##0.00'
        c_tr.alignment = Alignment(horizontal='right')
        c_tr.font = Font(bold=True, name='Segoe UI')
        
        c_tot = ws.cell(row=current_row, column=9, value=totals['total_sales'])
        c_tot.number_format = f'"{simbolo}"#,##0.00'
        c_tot.alignment = Alignment(horizontal='right')
        c_tot.font = Font(bold=True, name='Segoe UI')
        
        c_num = ws.cell(row=current_row, column=10, value=totals['sales_count'])
        c_num.alignment = Alignment(horizontal='center')
        c_num.font = Font(bold=True, name='Segoe UI')
        
        c_esp = ws.cell(row=current_row, column=11, value=totals['expected_balance'])
        c_esp.number_format = f'"{simbolo}"#,##0.00'
        c_esp.alignment = Alignment(horizontal='right')
        c_esp.font = Font(bold=True, name='Segoe UI')
        
        c_con = ws.cell(row=current_row, column=12, value=totals['counted_balance'])
        c_con.number_format = f'"{simbolo}"#,##0.00'
        c_con.alignment = Alignment(horizontal='right')
        c_con.font = Font(bold=True, name='Segoe UI')
        
        c_dif = ws.cell(row=current_row, column=13, value=totals['difference'])
        c_dif.number_format = f'"{simbolo}"#,##0.00'
        c_dif.alignment = Alignment(horizontal='right')
        c_dif.font = Font(bold=True, name='Segoe UI', color='C62828' if totals['difference'] < 0 else ('2E7D32' if totals['difference'] == 0 else 'E65100'))
        
        ws.cell(row=current_row, column=14, value="")
        
        for col in range(1, 15):
            ws.cell(row=current_row, column=col).border = _borde_total()
            
        ws.row_dimensions[current_row].height = 24

    _autoajustar_columnas(ws)
    
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def generate_chart_of_accounts_excel(accounts: list, params: dict, tenant: dict) -> bytes:
    """Genera Excel ejecutivo del Plan de Cuentas Contable con formato profesional."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Plan de Cuentas"
    ws.views.sheetView[0].showGridLines = True
    
    color_hex = _hex_to_openpyxl(tenant.get('primary_color', '#1976D2'))
    empresa = params.get('general', {}).get('empresa_nombre', {}).get('valor', tenant.get('name', 'ERP'))
    
    # 1. Banner
    _aplicar_banner_titulo(ws, color_hex, f"PLAN DE CUENTAS - {empresa}", 4)
    
    # 2. Encabezados
    headers = ["Código Contable", "Nombre de la Cuenta", "Tipo de Cuenta", "Nivel"]
    fill_header, font_header, align_header = _estilo_encabezado(color_hex)
    
    for col_idx, text in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col_idx, value=text)
        cell.fill = fill_header
        cell.font = font_header
        cell.alignment = align_header
        cell.border = _borde_delgado()
    ws.row_dimensions[4].height = 26
    
    # 3. Datos
    borde = _borde_delgado()
    tipo_map = {
        'is_active': 'Activo',
        'activo': 'Activo',
        'pasivo': 'Pasivo',
        'patrimonio': 'Patrimonio',
        'ingreso': 'Ingreso',
        'egreso': 'Egreso',
        'costo': 'Costo',
    }
    
    for idx, acc in enumerate(accounts, 5):
        code = str(acc.get('code', ''))
        name = str(acc.get('name', ''))
        raw_type = str(acc.get('type', '')).lower()
        tipo_label = tipo_map.get(raw_type, raw_type.capitalize())
        
        dots = code.count('.')
        nivel = f"Nivel {dots + 1}"
        es_base = code.endswith('.00.00') or dots == 0
        
        color_fila = 'F1F5F9' if es_base else ('F8FAFC' if idx % 2 == 0 else 'FFFFFF')
        fill_row = PatternFill(start_color=color_fila, end_color=color_fila, fill_type='solid')
        
        # Celda Código (Formato Texto explícito '@' para preservar ceros iniciales como 0000 o 01)
        cell_code = ws.cell(row=idx, column=1, value=code)
        cell_code.number_format = '@'
        cell_code.alignment = Alignment(horizontal='left', vertical='center', indent=dots)
        
        # Celda Nombre
        cell_name = ws.cell(row=idx, column=2, value=name)
        cell_name.alignment = Alignment(horizontal='left', vertical='center')
        
        # Celda Tipo
        cell_tipo = ws.cell(row=idx, column=3, value=tipo_label)
        cell_tipo.alignment = Alignment(horizontal='center', vertical='center')
        
        # Celda Nivel
        cell_nivel = ws.cell(row=idx, column=4, value=nivel)
        cell_nivel.alignment = Alignment(horizontal='center', vertical='center')
        
        font_style = Font(name='Segoe UI', size=10, bold=es_base)
        for col_idx in range(1, 5):
            c = ws.cell(row=idx, column=col_idx)
            c.font = font_style
            c.fill = fill_row
            c.border = borde
            
        ws.row_dimensions[idx].height = 22
        
    _autoajustar_columnas(ws)
    
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
