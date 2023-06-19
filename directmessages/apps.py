from django.apps import AppConfig

Inbox = None


class AppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "directmessages"

    def ready(self):
        # For convenience
        from .services import MessagingService
        global Inbox
        Inbox = MessagingService()
