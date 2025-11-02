from django.apps import AppConfig


class SaasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'saas'

    def ready(self):
        import saas.signals\
        
    # Ensures signal handlers are connected when the app is ready

