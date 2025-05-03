from django.apps import AppConfig


class OrderappConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "orderApp"

    def ready(self):
        from cleaner import cleaner

        cleaner()
        return super().ready()
