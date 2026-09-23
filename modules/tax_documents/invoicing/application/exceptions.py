class BusinessError(Exception):
    """
    Excepción base para errores de lógica de negocio o de validación.
    Permite enviar información estructurada a las vistas.
    """
    def __init__(self, message, field=None, code="BUSINESS_ERROR"):
        super().__init__(message)
        self.message = message
        self.field = field
        self.code = code
