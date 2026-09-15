from django.urls import path, re_path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.home, name="home"),
    path("research", views.research, name="research"),
    path("research/<str:object_id>", views.research_detail, name="research_detail"),
    path("sources", views.sources, name="sources"),
    path("sources/<str:source_id>", views.source_detail, name="source_detail"),
    path("governing", views.governing, name="governing"),
    path("governing/<str:governing_id>", views.governing_detail, name="governing_detail"),
    path("authors", views.authors, name="authors"),
    path("authors/<str:author_id>", views.author_detail, name="author_detail"),
    path("receipts", views.receipts, name="receipts"),
    path("receipts/<str:receipt_id>", views.receipt_detail, name="receipt_detail"),
    path("contribute", views.contribute, name="contribute"),
    # Documented redirects for the generated static-site entry points.
    re_path(r"^(?P<folder>objects|sources|governing|authors|receipts)/(?P<ident>[A-Z0-9-]+)\.html$", views.legacy_redirect, name="legacy"),
]
