from django.urls import path

from . import webhooks

app_name = "registry_bridge"

urlpatterns = [
    path("github/webhook", webhooks.github_webhook, name="github_webhook"),
]
