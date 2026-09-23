from django.apps import AppConfig

class AuditoriaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'django_apps.auditoria'
    
    def ready(self):
        # Import signals so they are registered
        import modules.auditoria.infrastructure.signals
