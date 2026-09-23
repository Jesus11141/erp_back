import threading

_thread_locals = threading.local()

def get_current_user_id():
    return getattr(_thread_locals, 'user_id', None)

def get_current_tenant_id():
    return getattr(_thread_locals, 'tenant_id', None)

def get_current_ip():
    return getattr(_thread_locals, 'ip', None)

class CurrentRequestMiddleware:
    """
    Middleware that captures the current user, tenant, and IP address
    and stores them in thread local storage so that Django Signals 
    (like post_save in models) can access them without having the request object.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Determine IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR', '')

        _thread_locals.ip = ip

        # tenant_id is usually set by TenantMiddleware (if it runs before this)
        if hasattr(request, 'tenant') and request.tenant:
            _thread_locals.tenant_id = request.tenant.id
        else:
            _thread_locals.tenant_id = None

        # user_id is usually set by Authentication (JWT)
        user = getattr(request, 'user', None)
        if user:
            # Handle both Django models (with is_authenticated) and Domain models (without)
            is_auth = getattr(user, 'is_authenticated', True)
            # Some DRF authentication backends might return a boolean for is_authenticated or a callable
            if callable(is_auth):
                is_auth = is_auth()
            
            if is_auth:
                _thread_locals.user_id = getattr(user, 'id', None)
            else:
                _thread_locals.user_id = None
        else:
            _thread_locals.user_id = None

        response = self.get_response(request)

        # Clean up
        if hasattr(_thread_locals, 'user_id'):
            del _thread_locals.user_id
        if hasattr(_thread_locals, 'tenant_id'):
            del _thread_locals.tenant_id
        if hasattr(_thread_locals, 'ip'):
            del _thread_locals.ip

        return response
