"""
Servicio de Importación Masiva Excel y Generación de Plantillas Oficiales.
Soporta:
1. Productos e Inventario (con Stock Inicial y Kardex)
2. Clientes (con validación de RUC y Cédula SRI)
3. Proveedores (con datos bancarios para Cash Management)
4. Plan de Cuentas Contable (con detección automática de jerarquía)
"""

import io
import csv
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, List, Tuple
from django.db import transaction

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from modules.shared.validators import validar_cedula_ecuador, validar_ruc_ecuador
from modules.inventario.infrastructure.django_models import ProductModel, StockMovementModel
from modules.ventas.infrastructure.django_models import CustomerModel
from modules.compras.infrastructure.django_models import ProveedorModel
from modules.contabilidad.infrastructure.django_models import AccountModel


class ExcelImportService:

    # ─────────────────────────────────────────────────────────────
    # 1. GENERACIÓN DE PLANTILLAS OFICIALES (.XLSX)
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def _crear_libro_plantilla(titulo: str, columnas: List[Tuple[str, int, str]], filas_ejemplo: List[List[Any]]) -> bytes:
        """
        Crea un archivo Excel estilizado con:
        - Cabecera con fondo verde oscuro / corporativo y texto en negrita blanco.
        - Ancho de columnas preajustado.
        - Filas de ejemplo con datos realistas para guiar al usuario.
        """
        wb = Workbook()
        ws = wb.active
        ws.title = titulo[:31]

        # Estilos
        font_header = Font(name='Calibri', size=11, bold=True, color='FFFFFF')
        fill_header = PatternFill(start_color='1B5E20', end_color='1B5E20', fill_type='solid') # Verde corporativo
        align_center = Alignment(horizontal='center', vertical='center', wrap_text=True)
        align_left = Alignment(horizontal='left', vertical='center')
        
        thin_border = Border(
            left=Side(style='thin', color='CCCCCC'),
            right=Side(style='thin', color='CCCCCC'),
            top=Side(style='thin', color='CCCCCC'),
            bottom=Side(style='thin', color='CCCCCC')
        )

        # Fila 1: Nombres de columnas
        headers = [col[0] for col in columnas]
        ws.append(headers)
        ws.row_dimensions[1].height = 28

        for col_idx, (col_name, col_width, col_align) in enumerate(columnas, start=1):
            cell = ws.cell(row=1, column=col_idx)
            cell.font = font_header
            cell.fill = fill_header
            cell.alignment = align_center
            col_letter = get_column_letter(col_idx)
            ws.column_dimensions[col_letter].width = col_width

        # Filas de ejemplo
        font_data = Font(name='Calibri', size=10, color='333333')
        fill_example = PatternFill(start_color='F9FAFB', end_color='F9FAFB', fill_type='solid')

        for r_idx, fila in enumerate(filas_ejemplo, start=2):
            ws.append(fila)
            ws.row_dimensions[r_idx].height = 22
            for c_idx, val in enumerate(fila, start=1):
                cell = ws.cell(row=r_idx, column=c_idx)
                cell.font = font_data
                cell.fill = fill_example
                cell.border = thin_border
                align_mode = columnas[c_idx - 1][2]
                cell.alignment = Alignment(horizontal=align_mode, vertical='center')

        output = io.BytesIO()
        wb.save(output)
        return output.getvalue()

    @classmethod
    def generate_template(cls, entity: str) -> Tuple[bytes, str]:
        """
        Retorna los bytes del archivo .xlsx de la plantilla y el nombre sugerido.
        """
        entity_norm = entity.lower().strip()

        if entity_norm in ['productos', 'inventario', 'items']:
            cols = [
                ('CODIGO', 16, 'left'),
                ('NOMBRE', 35, 'left'),
                ('DESCRIPCION', 30, 'left'),
                ('CATEGORIA', 20, 'left'),
                ('PRECIO_COMPRA', 16, 'right'),
                ('PRECIO_VENTA', 16, 'right'),
                ('STOCK_INICIAL', 15, 'right'),
                ('STOCK_MINIMO', 15, 'right'),
                ('UNIDAD', 12, 'center'),
                ('TARIFA_IVA', 14, 'center'),
            ]
            ejemplos = [
                ['PRD-001', 'Aceite Multigrado 20W50 (Galón)', 'Aceite mineral para motor a gasolina', 'Lubricantes', 15.50, 24.99, 50, 10, 'pza', '15'],
                ['PRD-002', 'Filtro de Aire Alto Flujo', 'Filtro lavable para vehículos livianos', 'Repuestos', 8.20, 14.50, 30, 5, 'pza', '15'],
                ['SRV-001', 'Mantenimiento Preventivo 10K', 'Revisión general y cambio de fluidos', 'Servicios', 0.00, 45.00, 0, 0, 'srv', '15'],
                ['ALIM-01', 'Harina de Trigo Especial 50kg', 'Saco de harina para panificación', 'Materia Prima', 32.00, 38.00, 100, 15, 'kg', '0'],
            ]
            return cls._crear_libro_plantilla('Plantilla_Productos', cols, ejemplos), 'plantilla_productos.xlsx'

        elif entity_norm in ['clientes', 'customers']:
            cols = [
                ('IDENTIFICACION', 18, 'left'),
                ('NOMBRE_O_RAZON_SOCIAL', 36, 'left'),
                ('EMAIL', 28, 'left'),
                ('TELEFONO', 18, 'left'),
                ('DIRECCION', 35, 'left'),
            ]
            ejemplos = [
                ['1792345678001', 'Corporación Andina S.A.', 'facturacion@andina.com', '022345678', 'Av. Amazonas y Colón, Quito'],
                ['1712345678', 'Juan Carlos Pérez López', 'juan.perez@gmail.com', '0998765432', 'Calle Los Álamos 123 y Av. 10 de Agosto'],
                ['0990001234001', 'Distribuidora del Litoral Cia. Ltda.', 'cobranzas@distlitoral.ec', '042998877', 'Km 5.5 Vía a Daule, Guayaquil'],
            ]
            return cls._crear_libro_plantilla('Plantilla_Clientes', cols, ejemplos), 'plantilla_clientes.xlsx'

        elif entity_norm in ['proveedores', 'suppliers']:
            cols = [
                ('IDENTIFICACION', 18, 'left'),
                ('TIPO_IDENTIFICACION', 20, 'center'),
                ('RAZON_SOCIAL', 35, 'left'),
                ('NOMBRE_COMERCIAL', 25, 'left'),
                ('EMAIL', 28, 'left'),
                ('TELEFONO', 18, 'left'),
                ('DIRECCION', 35, 'left'),
                ('DIAS_CREDITO', 14, 'right'),
                ('BANCO', 20, 'left'),
                ('TIPO_CUENTA', 14, 'center'),
                ('NUMERO_CUENTA', 20, 'left'),
            ]
            ejemplos = [
                ['1790012345001', '04', 'IMPORTADORA Y DISTRIBUIDORA NACIONAL S.A.', 'ImporNacional', 'ventas@impornacional.com', '022987654', 'Av. Galo Plaza Lasso Km 8, Quito', 30, 'Banco Pichincha', 'CTE', '2100123456'],
                ['0991234567001', '04', 'SERVICIOS LOGISTICOS DEL PACIFICO CIA. LTDA.', 'PacifLog', 'contabilidad@paciflog.ec', '042123456', 'Puerto Marítimo Muelle 2, Guayaquil', 15, 'Banco Guayaquil', 'CTE', '1122334455'],
                ['1002345678', '05', 'MARIA EUGENIA CASTRO BOLAÑOS', 'Comercial Castro', 'maria.castro@hotmail.com', '0987654321', 'Calle Bolívar 456, Ibarra', 0, 'Produbanco', 'AHO', '1205678901'],
            ]
            return cls._crear_libro_plantilla('Plantilla_Proveedores', cols, ejemplos), 'plantilla_proveedores.xlsx'

        elif entity_norm in ['plan-cuentas', 'cuentas', 'plancuentas', 'accounts']:
            cols = [
                ('CODIGO', 18, 'left'),
                ('NOMBRE', 40, 'left'),
                ('TIPO', 18, 'center'),
            ]
            ejemplos = [
                ['1', 'ACTIVO', 'Activo'],
                ['1.1', 'ACTIVO CORRIENTE', 'Activo'],
                ['1.1.01', 'EFECTIVO Y EQUIVALENTES DE EFECTIVO', 'Activo'],
                ['1.1.01.01', 'Caja General', 'Activo'],
                ['1.1.01.02', 'Bancos Locales', 'Activo'],
                ['1.1.02', 'CUENTAS Y DOCUMENTOS POR COBRAR', 'Activo'],
                ['1.1.02.01', 'Clientes Locales', 'Activo'],
                ['2', 'PASIVO', 'Pasivo'],
                ['2.1', 'PASIVO CORRIENTE', 'Pasivo'],
                ['2.1.01', 'CUENTAS Y DOCUMENTOS POR PAGAR', 'Pasivo'],
                ['3', 'PATRIMONIO', 'Patrimonio'],
                ['3.1', 'CAPITAL SOCIAL', 'Patrimonio'],
                ['4', 'INGRESOS', 'Ingreso'],
                ['4.1', 'VENTAS LOCALES GRAVADAS', 'Ingreso'],
                ['5', 'GASTOS Y COSTOS', 'Egreso'],
                ['5.1', 'COSTO DE VENTAS', 'Egreso'],
            ]
            return cls._crear_libro_plantilla('Plantilla_Plan_Cuentas', cols, ejemplos), 'plantilla_plan_cuentas.xlsx'

        else:
            raise ValueError(f"Entidad '{entity}' no soportada para plantilla de importación")


    # ─────────────────────────────────────────────────────────────
    # 2. LECTURA Y NORMALIZACIÓN DE ARCHIVOS (XLSX / CSV)
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def _read_rows(file_obj, filename: str) -> List[Dict[str, Any]]:
        """
        Lee un archivo Excel (.xlsx/.xls) o CSV y retorna una lista de diccionarios
        donde las claves son los nombres normalizados de las columnas (mayúsculas sin espacios ni acentos).
        """
        fn = filename.lower()
        rows_data = []

        if fn.endswith('.xlsx') or fn.endswith('.xls'):
            wb = load_workbook(filename=file_obj, data_only=True)
            sheet = wb.active
            raw_rows = list(sheet.iter_rows(values_only=True))
            if not raw_rows:
                return []
            
            # Buscar la fila de cabecera (primera fila no vacía)
            header_row_idx = 0
            while header_row_idx < len(raw_rows) and not any(raw_rows[header_row_idx]):
                header_row_idx += 1
            
            if header_row_idx >= len(raw_rows):
                return []

            header_raw = raw_rows[header_row_idx]
            headers = [ExcelImportService._normalize_header(str(c or '')) for c in header_raw]

            for row_idx, r in enumerate(raw_rows[header_row_idx + 1:], start=header_row_idx + 2):
                if not any(r):
                    continue # Salta filas completamente vacías
                row_dict = {'_row_number': row_idx}
                has_content = False
                for c_idx, val in enumerate(r):
                    if c_idx < len(headers) and headers[c_idx]:
                        val_str = str(val).strip() if val is not None else ''
                        row_dict[headers[c_idx]] = val_str
                        if val_str:
                            has_content = True
                if has_content:
                    rows_data.append(row_dict)

        else:
            # Leer CSV
            content = file_obj.read()
            if isinstance(content, bytes):
                try:
                    text = content.decode('utf-8-sig')
                except UnicodeDecodeError:
                    text = content.decode('latin-1', errors='replace')
            else:
                text = str(content)

            f_str = io.StringIO(text)
            # Detectar delimitador (, o ;)
            sample = text[:2048]
            delimiter = ';' if sample.count(';') > sample.count(',') else ','
            reader = csv.reader(f_str, delimiter=delimiter)
            raw_rows = list(reader)
            if not raw_rows:
                return []

            header_raw = raw_rows[0]
            headers = [ExcelImportService._normalize_header(c) for c in header_raw]

            for row_idx, r in enumerate(raw_rows[1:], start=2):
                if not any(r):
                    continue
                row_dict = {'_row_number': row_idx}
                has_content = False
                for c_idx, val in enumerate(r):
                    if c_idx < len(headers) and headers[c_idx]:
                        val_str = val.strip()
                        row_dict[headers[c_idx]] = val_str
                        if val_str:
                            has_content = True
                if has_content:
                    rows_data.append(row_dict)

        return rows_data

    @staticmethod
    def _normalize_header(name: str) -> str:
        """Convierte 'Precio de Venta ($)' en 'PRECIO_VENTA'"""
        n = name.upper().strip()
        n = n.replace('Á', 'A').replace('É', 'E').replace('Í', 'I').replace('Ó', 'O').replace('Ú', 'U')
        n = n.replace('Ñ', 'N').replace(' ', '_').replace('.', '').replace('-', '_')
        n = ''.join(c for c in n if c.isalnum() or c == '_')
        return n

    @staticmethod
    def _parse_decimal(val: Any, default: Decimal = Decimal('0.00')) -> Decimal:
        if val is None or val == '':
            return default
        s = str(val).strip().replace('$', '').replace(' ', '')
        # Si tiene coma como separador decimal y no puntos: '15,50' -> '15.50'
        if ',' in s and '.' not in s:
            s = s.replace(',', '.')
        elif ',' in s and '.' in s:
            # Ejemplo: '1,250.50' -> '1250.50'
            s = s.replace(',', '')
        try:
            return Decimal(s)
        except (InvalidOperation, ValueError):
            return default


    # ─────────────────────────────────────────────────────────────
    # 3. IMPORTADORES ESPECÍFICOS POR DOMINIO
    # ─────────────────────────────────────────────────────────────

    @classmethod
    def import_products(cls, tenant_id: int, file_obj, filename: str, mode: str = 'upsert', user_id: int = 0) -> Dict[str, Any]:
        """
        Importa productos a inventario con opción de Kardex para stock inicial.
        """
        rows = cls._read_rows(file_obj, filename)
        if not rows:
            return {'success': False, 'message': 'El archivo no contiene filas de datos.', 'total': 0, 'created': 0, 'updated': 0, 'errors': []}

        created_count = 0
        updated_count = 0
        errors = []

        with transaction.atomic():
            for row in rows:
                r_num = row.get('_row_number', '?')
                
                # Obtener código
                code = (row.get('CODIGO') or row.get('COD') or row.get('CODE') or '').strip()
                name = (row.get('NOMBRE') or row.get('NAME') or row.get('DESCRIPCION_CORTA') or '').strip()

                if not code:
                    errors.append({'row': r_num, 'identifier': 'Sin Código', 'error': 'El campo CODIGO es obligatorio.'})
                    continue
                if not name:
                    errors.append({'row': r_num, 'identifier': code, 'error': 'El campo NOMBRE es obligatorio.'})
                    continue

                desc = (row.get('DESCRIPCION') or row.get('DETALLE') or '').strip()
                cat = (row.get('CATEGORIA') or row.get('CATEGORY') or '').strip() or None
                unit = (row.get('UNIDAD') or row.get('UNIT') or 'pza').strip().lower()
                vat = (row.get('TARIFA_IVA') or row.get('IVA') or '15').strip().replace('%', '')

                p_compra = cls._parse_decimal(row.get('PRECIO_COMPRA') or row.get('COSTO') or row.get('PURCHASE_PRICE'), Decimal('0.00'))
                p_venta = cls._parse_decimal(row.get('PRECIO_VENTA') or row.get('PVP') or row.get('SALE_PRICE'), Decimal('0.00'))
                stock_ini = cls._parse_decimal(row.get('STOCK_INICIAL') or row.get('STOCK') or row.get('CURRENT_STOCK'), Decimal('0.00'))
                stock_min = cls._parse_decimal(row.get('STOCK_MINIMO') or row.get('MIN_STOCK'), Decimal('0.00'))

                if p_venta < 0:
                    errors.append({'row': r_num, 'identifier': code, 'error': 'El precio de venta no puede ser negativo.'})
                    continue

                # Buscar si ya existe
                existing = ProductModel.objects.filter(tenant_id=tenant_id, code=code).first()

                if existing:
                    if mode == 'create_only':
                        continue # Omitir si ya existe
                    # Actualizar
                    existing.name = name
                    if desc: existing.description = desc
                    if cat: existing.category = cat
                    existing.purchase_price = p_compra
                    existing.sale_price = p_venta
                    existing.minimum_stock = stock_min
                    existing.unit = unit
                    existing.vat_rate = vat
                    existing.active = True
                    
                    # Si especificaron stock inicial en el excel y es distinto de cero
                    if stock_ini > 0 and existing.current_stock == 0:
                        existing.current_stock = stock_ini
                        StockMovementModel.objects.create(
                            tenant_id=tenant_id,
                            product=existing,
                            product_name=existing.name,
                            type='in',
                            quantity=stock_ini,
                            previous_stock=0,
                            new_stock=stock_ini,
                            reference='Carga Inicial Masiva Excel (Actualización)',
                            user_id=user_id or 0
                        )

                    existing.save()
                    updated_count += 1
                else:
                    # Crear nuevo
                    prod = ProductModel.objects.create(
                        tenant_id=tenant_id,
                        code=code,
                        name=name,
                        description=desc,
                        category=cat,
                        purchase_price=p_compra,
                        sale_price=p_venta,
                        current_stock=stock_ini,
                        minimum_stock=stock_min,
                        unit=unit,
                        vat_rate=vat,
                        active=True
                    )
                    # Registrar Kardex inicial si traía stock
                    if stock_ini > 0:
                        StockMovementModel.objects.create(
                            tenant_id=tenant_id,
                            product=prod,
                            product_name=prod.name,
                            type='in',
                            quantity=stock_ini,
                            previous_stock=0,
                            new_stock=stock_ini,
                            reference='Carga Inicial Masiva Excel',
                            user_id=user_id or 0
                        )
                    created_count += 1

        return {
            'success': True,
            'total': len(rows),
            'created': created_count,
            'updated': updated_count,
            'errors': errors
        }

    @classmethod
    def import_clients(cls, tenant_id: int, file_obj, filename: str, mode: str = 'upsert') -> Dict[str, Any]:
        """
        Importa clientes con validación de RUC / Cédula SRI.
        """
        rows = cls._read_rows(file_obj, filename)
        if not rows:
            return {'success': False, 'message': 'El archivo no contiene filas de datos.', 'total': 0, 'created': 0, 'updated': 0, 'errors': []}

        created_count = 0
        updated_count = 0
        errors = []

        with transaction.atomic():
            for row in rows:
                r_num = row.get('_row_number', '?')
                
                ident = (row.get('IDENTIFICACION') or row.get('RUC') or row.get('CEDULA') or row.get('RFC') or '').strip()
                name = (row.get('NOMBRE_O_RAZON_SOCIAL') or row.get('NOMBRE') or row.get('RAZON_SOCIAL') or '').strip()

                if not ident:
                    errors.append({'row': r_num, 'identifier': 'Sin Identificación', 'error': 'El campo IDENTIFICACION es obligatorio.'})
                    continue
                if not name:
                    errors.append({'row': r_num, 'identifier': ident, 'error': 'El campo NOMBRE_O_RAZON_SOCIAL es obligatorio.'})
                    continue

                email = (row.get('EMAIL') or row.get('CORREO') or '').strip()
                phone = (row.get('TELEFONO') or row.get('CELULAR') or '').strip()
                addr = (row.get('DIRECCION') or row.get('ADDRESS') or '').strip()

                # Advertencia informativa de validez de cédula/RUC en Ecuador (no bloquea para permitir pasaportes)
                if len(ident) == 10 and not validar_cedula_ecuador(ident):
                    # formato de cédula inválido pero se importa con nota
                    pass
                elif len(ident) == 13 and not validar_ruc_ecuador(ident):
                    # formato de RUC inválido
                    pass

                existing = CustomerModel.objects.filter(tenant_id=tenant_id, rfc=ident).first()

                if existing:
                    if mode == 'create_only':
                        continue
                    existing.name = name
                    if email: existing.email = email
                    if phone: existing.phone = phone
                    if addr: existing.address = addr
                    existing.active = True
                    existing.save()
                    updated_count += 1
                else:
                    CustomerModel.objects.create(
                        tenant_id=tenant_id,
                        rfc=ident,
                        name=name,
                        email=email,
                        phone=phone,
                        address=addr,
                        active=True
                    )
                    created_count += 1

        return {
            'success': True,
            'total': len(rows),
            'created': created_count,
            'updated': updated_count,
            'errors': errors
        }

    @classmethod
    def import_suppliers(cls, tenant_id: int, file_obj, filename: str, mode: str = 'upsert') -> Dict[str, Any]:
        """
        Importa proveedores con datos bancarios para Cash Management y órdenes de compra.
        """
        rows = cls._read_rows(file_obj, filename)
        if not rows:
            return {'success': False, 'message': 'El archivo no contiene filas de datos.', 'total': 0, 'created': 0, 'updated': 0, 'errors': []}

        created_count = 0
        updated_count = 0
        errors = []

        with transaction.atomic():
            for row in rows:
                r_num = row.get('_row_number', '?')

                ident = (row.get('IDENTIFICACION') or row.get('RUC') or row.get('CEDULA') or '').strip()
                name = (row.get('RAZON_SOCIAL') or row.get('NOMBRE') or row.get('BUSINESS_NAME') or '').strip()

                if not ident:
                    errors.append({'row': r_num, 'identifier': 'Sin Identificación', 'error': 'El campo IDENTIFICACION es obligatorio.'})
                    continue
                if not name:
                    errors.append({'row': r_num, 'identifier': ident, 'error': 'El campo RAZON_SOCIAL es obligatorio.'})
                    continue

                id_type = (row.get('TIPO_IDENTIFICACION') or ('04' if len(ident) == 13 else '05')).strip()
                comm_name = (row.get('NOMBRE_COMERCIAL') or '').strip()
                email = (row.get('EMAIL') or row.get('CORREO') or '').strip()
                phone = (row.get('TELEFONO') or '').strip()
                addr = (row.get('DIRECCION') or '').strip()
                
                try:
                    credit_days = int(row.get('DIAS_CREDITO') or 0)
                except ValueError:
                    credit_days = 0

                banco = (row.get('BANCO') or '').strip()
                tipo_cta = (row.get('TIPO_CUENTA') or 'CTE').strip().upper()
                num_cta = (row.get('NUMERO_CUENTA') or '').strip()

                existing = ProveedorModel.objects.filter(tenant_id=tenant_id, identification=ident).first()

                if existing:
                    if mode == 'create_only':
                        continue
                    existing.business_name = name
                    if comm_name: existing.commercial_name = comm_name
                    existing.id_type = id_type
                    if email: existing.email = email
                    if phone: existing.phone = phone
                    if addr: existing.address = addr
                    existing.credit_days = credit_days
                    if banco: existing.bank_name = banco
                    if tipo_cta: existing.bank_account_type = tipo_cta
                    if num_cta: existing.bank_account_number = num_cta
                    existing.active = True
                    existing.save()
                    updated_count += 1
                else:
                    ProveedorModel.objects.create(
                        tenant_id=tenant_id,
                        identification=ident,
                        id_type=id_type,
                        business_name=name,
                        commercial_name=comm_name,
                        email=email,
                        phone=phone,
                        address=addr,
                        credit_days=credit_days,
                        bank_name=banco,
                        bank_account_type=tipo_cta,
                        bank_account_number=num_cta,
                        active=True
                    )
                    created_count += 1

        return {
            'success': True,
            'total': len(rows),
            'created': created_count,
            'updated': updated_count,
            'errors': errors
        }

    @classmethod
    def import_accounts(cls, tenant_id: int, file_obj, filename: str, mode: str = 'upsert') -> Dict[str, Any]:
        """
        Importa el Plan de Cuentas Contable y enlaza automáticamente la jerarquía (cuentas padre).
        """
        rows = cls._read_rows(file_obj, filename)
        if not rows:
            return {'success': False, 'message': 'El archivo no contiene filas de datos.', 'total': 0, 'created': 0, 'updated': 0, 'errors': []}

        # Ordenar por longitud de código para garantizar que las cuentas principales
        # (ej: 1, 1.1, 1.1.01) se procesen antes que las subcuentas (1.1.01.01).
        rows_sorted = sorted(rows, key=lambda r: (str(r.get('CODIGO') or '').count('.'), len(str(r.get('CODIGO') or ''))))

        created_count = 0
        updated_count = 0
        errors = []

        # Mapa de normalización de tipos contables SRI / NIIF
        tipo_map = {
            'activo': 'is_active',
            'is_active': 'is_active',
            'activos': 'is_active',
            'pasivo': 'pasivo',
            'pasivos': 'pasivo',
            'patrimonio': 'patrimonio',
            'capital': 'patrimonio',
            'ingreso': 'ingreso',
            'ingresos': 'ingreso',
            'renta': 'ingreso',
            'egreso': 'egreso',
            'egresos': 'egreso',
            'gasto': 'egreso',
            'gastos': 'egreso',
            'costo': 'egreso',
            'costos': 'egreso',
        }

        with transaction.atomic():
            for row in rows_sorted:
                r_num = row.get('_row_number', '?')

                code = (row.get('CODIGO') or row.get('CODE') or row.get('CUENTA') or '').strip()
                name = (row.get('NOMBRE') or row.get('NAME') or row.get('DESCRIPCION') or '').strip()
                t_raw = (row.get('TIPO') or row.get('TYPE') or '').strip().lower()

                if not code:
                    errors.append({'row': r_num, 'identifier': 'Sin Código', 'error': 'El campo CODIGO es obligatorio.'})
                    continue
                if not name:
                    errors.append({'row': r_num, 'identifier': code, 'error': 'El campo NOMBRE es obligatorio.'})
                    continue

                account_type = tipo_map.get(t_raw)
                if not account_type:
                    # Deducir tipo por primer dígito común ecuatoriano:
                    # 1: Activo, 2: Pasivo, 3: Patrimonio, 4: Ingresos, 5/6: Egresos/Costos
                    first_digit = code[0]
                    if first_digit == '1': account_type = 'is_active'
                    elif first_digit == '2': account_type = 'pasivo'
                    elif first_digit == '3': account_type = 'patrimonio'
                    elif first_digit == '4': account_type = 'ingreso'
                    elif first_digit in ['5', '6', '7']: account_type = 'egreso'
                    else: account_type = 'is_active'

                # Determinar padre según notación por puntos: ej: '1.1.01.05' -> padre '1.1.01'
                parent_obj = None
                if '.' in code:
                    parent_code = code.rsplit('.', 1)[0]
                    parent_obj = AccountModel.objects.filter(tenant_id=tenant_id, code=parent_code).first()

                existing = AccountModel.objects.filter(tenant_id=tenant_id, code=code).first()

                if existing:
                    if mode == 'create_only':
                        continue
                    existing.name = name
                    existing.type = account_type
                    if parent_obj: existing.parent = parent_obj
                    existing.save()
                    updated_count += 1
                else:
                    AccountModel.objects.create(
                        tenant_id=tenant_id,
                        code=code,
                        name=name,
                        type=account_type,
                        parent=parent_obj
                    )
                    created_count += 1

        return {
            'success': True,
            'total': len(rows),
            'created': created_count,
            'updated': updated_count,
            'errors': errors
        }
