from dataclasses import dataclass
from typing import Any

# Complete parameter catalog with default values
CATALOG = {
    'general': {
        'logo_url':              {'label': 'Logo de la empresa',         'type': 'image',   'default': ''},
        'empresa_nombre':        {'label': 'Nombre de la empresa',      'type': 'text',    'default': ''},
        'empresa_rfc':           {'label': 'RFC / RUC',                  'type': 'text',    'default': ''},
        'empresa_representante': {'label': 'Director / Representante',   'type': 'text',    'default': ''},
        'empresa_contador':      {'label': 'Contador Público (Nombre)', 'type': 'text',    'default': ''},
        'empresa_contador_ruc':  {'label': 'RUC / Matrícula Contador',  'type': 'text',    'default': ''},
        'empresa_direccion':     {'label': 'Dirección',                  'type': 'text',    'default': ''},
        'empresa_telefono':      {'label': 'Teléfonos de contacto',     'type': 'text',    'default': ''},
        'empresa_email':         {'label': 'Email',                      'type': 'text',    'default': ''},
        'moneda':                {'label': 'Moneda',                     'type': 'text',    'default': 'USD'},
        'moneda_simbolo':        {'label': 'Símbolo de moneda',          'type': 'text',    'default': '$'},
        'decimales_precio':      {'label': 'Decimales en precios',       'type': 'number',  'default': '2'},
        'zona_horaria':          {'label': 'Zona horaria',               'type': 'text',    'default': 'America/Guayaquil'},
    },
    'ventas': {
        'iva':                {'label': 'IVA / Impuesto por defecto (%)', 'type': 'number',   'default': '15'},
        'tarifas_iva':        {'label': 'Tarifas de IVA disponibles (%)', 'type': 'list',     'default': '0, 5, 8, 15'},
        'dias_credito':       {'label': 'Días de crédito',            'type': 'number',   'default': '30'},
        'dias_cotizacion':    {'label': 'Validez de cotización (días)','type': 'number',   'default': '15'},
        'permitir_descuento': {'label': 'Permitir descuentos',          'type': 'boolean',  'default': 'true'},
        'descuento_maximo':   {'label': 'Descuento máximo (%)',         'type': 'number',   'default': '20'},
        'stock_negativo':     {'label': 'Permitir stock negativo',      'type': 'boolean',  'default': 'false'},
        'precio_editable':    {'label': 'Editar precio en venta',       'type': 'boolean',  'default': 'false'},
    },
    'facturacion': {
        'ruc_emisor':          {'label': 'RUC Emisor',                'type': 'text',    'default': ''},
        'establecimiento':     {'label': 'Código Establecimiento (ej. 001)', 'type': 'text', 'default': '001'},
        'punto_emision':       {'label': 'Punto de Emisión (ej. 001)', 'type': 'text',    'default': '001'},
        'ultima_factura':      {'label': 'Último secuencial usado (SRI)', 'type': 'number', 'default': '0'},
        'ambiente_sri':        {'label': 'Ambiente SRI',              'type': 'options', 'default': '1',
                                'options': ['1', '2']},
        'obligado_contabilidad': {'label': 'Obligado a llevar contabilidad', 'type': 'options', 'default': 'NO',
                                'options': ['SI', 'NO']},
        'contribuyente_especial': {'label': 'Nro. Contribuyente Especial', 'type': 'text', 'default': ''},
        'serie':              {'label': 'Serie de factura (Interna)', 'type': 'text',    'default': 'FAC'},
        'pie_factura':        {'label': 'Mensaje al pie de la factura','type': 'text',    'default': 'Gracias por su compra'},
        'dias_vencimiento':   {'label': 'Días para vencimiento',      'type': 'number',   'default': '30'},
        'signature_file':     {'label': 'Firma Electrónica (.p12)',   'type': 'file',     'default': ''},
        'signature_password': {'label': 'Contraseña de Firma',        'type': 'password', 'default': ''},
    },
    'pos': {
        'impresion_automatica': {'label': 'Impresión automática de recibos', 'type': 'boolean', 'default': 'true'},
        'formato_recibo':       {'label': 'Formato de recibo', 'type': 'options', 'default': '80mm', 'options': ['58mm', '80mm', 'A4']},
        'apertura_caja_obligatoria': {'label': 'Obligar apertura de caja al iniciar', 'type': 'boolean', 'default': 'true'},
        'enable_notas_venta': {'label': 'Activar nota de venta en POS', 'type': 'boolean', 'default': 'false'},
        'notas_venta_sri':    {'label': 'Notas de Venta atadas al SRI', 'type': 'boolean', 'default': 'false'},
    },
    'inventario': {
        'alerta_stock':       {'label': 'Alertas de stock mínimo',    'type': 'boolean',  'default': 'true'},
        'metodo_costeo':      {'label': 'Método de costeo',           'type': 'options', 'default': 'promedio',
                               'options': ['promedio', 'fifo', 'lifo']},
        'manejo_lotes':       {'label': 'Control por lotes',          'type': 'boolean',  'default': 'false'},
        'multibodega':        {'label': 'Múltiples bodegas',          'type': 'boolean',  'default': 'false'},
        'unidades_medida':    {'label': 'Unidades de Medida',         'type': 'list',     'default': 'Pieza, Kilogramo, Litro, Caja, Metro, Par'},
        'categorias_productos': {'label': 'Categorías de Productos',  'type': 'list',     'default': 'General, Alimentos, Bebidas, Electrónica, Ropa'},
    },
    'rrhh': {
        'deduccion_iess':        {'label': 'Aporte Personal IESS (%)',    'type': 'number',   'default': '9.45'},
        'aporte_patronal_iess':  {'label': 'Aporte Patronal IESS (%)',    'type': 'number',   'default': '11.15'},
        'fondos_reserva':        {'label': 'Fondos de Reserva (%)',       'type': 'number',   'default': '8.33'},
        'sbu_ecuador':           {'label': 'Salario Básico Unificado (SBU)', 'type': 'number', 'default': '460'},
        'mensualizar_decimo_tercero': {'label': 'Mensualizar Décimo Tercer Sueldo', 'type': 'boolean', 'default': 'true'},
        'mensualizar_decimo_cuarto':  {'label': 'Mensualizar Décimo Cuarto Sueldo',  'type': 'boolean', 'default': 'true'},
        'mensualizar_fondos_reserva':  {'label': 'Mensualizar Fondos de Reserva',     'type': 'boolean', 'default': 'true'},
        'dias_vacaciones':    {'label': 'Días vacaciones por año',    'type': 'number',   'default': '15'},
        'periodicidad_nomina':{'label': 'Periodicidad nómina',        'type': 'options', 'default': 'mensual',
                               'options': ['semanal', 'quincenal', 'mensual']},
        'hora_entrada':       {'label': 'Hora entrada default',       'type': 'text',    'default': '08:00'},
        'hora_salida':        {'label': 'Hora salida default',        'type': 'text',    'default': '17:00'},
    },
    'contabilidad': {
        'mes_cierre':         {'label': 'Mes de cierre fiscal',       'type': 'options', 'default': '12', 'options': ['1','2','3','4','5','6','7','8','9','10','11','12']},
        'forzar_partida_doble': {'label': 'Forzar partida doble estricta', 'type': 'boolean', 'default': 'true'},
    },
    'clinica': {
        'duracion_cita':      {'label': 'Duración promedio de cita (minutos)', 'type': 'number', 'default': '30'},
        'recordatorios_email':{'label': 'Enviar recordatorios por email', 'type': 'boolean', 'default': 'true'},
    },
    'technical_service': {
        'tipos_dispositivos': {'label': 'Tipos de Dispositivos', 'type': 'list', 'default': 'Celular, Computadora, Tablet, Consola'}
    },
    'correo': {
        'smtp_host':          {'label': 'Servidor SMTP (ej. smtp.gmail.com)', 'type': 'text',     'default': ''},
        'smtp_port':          {'label': 'Puerto SMTP (ej. 587 o 465)',         'type': 'number',   'default': '587'},
        'smtp_user':          {'label': 'Usuario / Correo Remitente',          'type': 'text',     'default': ''},
        'smtp_password':      {'label': 'Contraseña / Token de Aplicación',    'type': 'password', 'default': ''},
        'smtp_use_tls':       {'label': 'Usar TLS / STARTTLS',                'type': 'boolean',  'default': 'true'},
        'smtp_use_ssl':       {'label': 'Usar SSL directo (Puerto 465)',       'type': 'boolean',  'default': 'false'},
        'smtp_from_name':     {'label': 'Nombre Visible del Remitente',        'type': 'text',     'default': ''},
        'enviar_automatico':  {'label': 'Enviar comprobante automáticamente al autorizar', 'type': 'boolean', 'default': 'true'},
    },
    'restaurantes': {
        'modalidad_cobro': {
            'label': 'Modalidad de Cobro',
            'type': 'options',
            'default': 'post_pago',
            'options': ['post_pago', 'pre_pago']
        },
    }
}

@dataclass
class Parameter:
    tenant_id: int
    module: str
    key: str
    value: str

    def typed_value(self) -> Any:
        info = CATALOG.get(self.module, {}).get(self.key, {})
        param_type = info.get('type', 'text')
        if param_type == 'boolean':
            return self.value.lower() == 'true'
        if param_type == 'number':
            try:
                return float(self.value)
            except ValueError:
                return 0
        return self.value
