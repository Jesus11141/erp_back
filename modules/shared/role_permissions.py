from rest_framework.response import Response
from rest_framework import status


def admin_only(request):
    """
    Permite solo a roles 'admin' y 'superadmin'.
    Devuelve una Response de error si el usuario no tiene permiso,
    o None si puede continuar.
    """
    usuario = getattr(request, 'user', None)
    if not usuario:
        return Response({'status': 'auth_error', 'message': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
    is_admin = False
    if usuario.role in ('admin', 'superadmin'):
        is_admin = True
    elif hasattr(usuario, 'has_permission') and usuario.has_permission('*'):
        is_admin = True
        
    if not is_admin:
        return Response(
            {'status': 'auth_error', 'message': f'You do not have permission for this action. Administrator role required (your role: {usuario.role}).'},
            status=status.HTTP_403_FORBIDDEN
        )
    return None
