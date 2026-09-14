from django.apps import AppConfig


class CatalogConfig(AppConfig):
    name = "catalog"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from . import projection  # noqa: F401  registers the refresh handler
