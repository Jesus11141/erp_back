from rest_framework.permissions import BasePermission
from rest_framework_simplejwt.tokens import AccessToken
from .repository_impl import DjangoUserRepository

class RequiresPermission(BasePermission):
    def __init__(self, permission: str):
        self.permission = permission

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        if not user:
            return False
        return user.has_permission(self.permission)

def get_user_from_token(request):
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return None
    try:
        token = AccessToken(auth.split(' ')[1])
        repo = DjangoUserRepository()
        return repo.find_by_id(token['user_id'])
    except Exception:
        return None
