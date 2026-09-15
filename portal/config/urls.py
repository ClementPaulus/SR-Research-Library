"""Root URL configuration: public catalog, account flows, workspace, review, webhooks, health."""

from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

from core import views as core_views

urlpatterns = [
    path("", include("catalog.urls")),
    path("", include("accounts.urls")),
    path("accounts/", include("allauth.urls")),
    path("workspace", RedirectView.as_view(url="/workspace/", permanent=False)),
    path("workspace/", include("submissions.urls")),
    path("review/", include("submissions.review_urls")),
    path("integrations/", include("registry_bridge.urls")),
    path("healthz", core_views.health, name="health"),
    path("admin/", admin.site.urls),
]
