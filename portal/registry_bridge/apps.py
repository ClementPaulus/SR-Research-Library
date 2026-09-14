from django.apps import AppConfig


class RegistryBridgeConfig(AppConfig):
    name = "registry_bridge"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from . import publication  # noqa: F401  registers job handlers
