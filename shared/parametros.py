"""
Helper global para obtener parámetros desde cualquier módulo.

Uso:
    from shared.parametros import param
    iva = param(tenant_id, 'ventas', 'iva')           # retorna 12.0
    serie = param(tenant_id, 'facturacion', 'serie')   # retorna 'FAC'
"""
from modules.parametros.infrastructure.repository_impl import DjangoParameterRepository
from modules.parametros.application.use_cases import GetParameter

_repo = DjangoParameterRepository()
_caso = GetParameter(_repo)

def param(tenant_id: int, modulo: str, clave: str, default=None):
    return _caso.execute(tenant_id, modulo, clave, default)
