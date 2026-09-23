from .permissions import get_user_from_token

class AuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.user = get_user_from_token(request)
        return self.get_response(request)
