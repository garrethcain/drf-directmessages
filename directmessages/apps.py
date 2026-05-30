from django.apps import AppConfig as BaseAppConfig

Inbox = None


class DirectmessagesConfig(BaseAppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "directmessages"

    def ready(self):
        from .services import MessagingService

        global Inbox
        Inbox = MessagingService()
