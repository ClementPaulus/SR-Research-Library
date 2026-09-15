from django.urls import path

from . import views

app_name = "submissions"

urlpatterns = [
    path("", views.workspace, name="workspace"),
    path("submissions/new", views.new_submission, name="new"),
    path("submissions/<uuid:submission_id>", views.detail, name="detail"),
    path("submissions/<uuid:submission_id>/status.json", views.status_json, name="status"),
    path("submissions/<uuid:submission_id>/upload", views.upload, name="upload"),
    path("submissions/<uuid:submission_id>/edit", views.edit, name="edit"),
    path("submissions/<uuid:submission_id>/autosave", views.autosave, name="autosave"),
    path("submissions/<uuid:submission_id>/sources/add", views.add_source, name="add_source"),
    path("submissions/<uuid:submission_id>/relations/add", views.add_relation, name="add_relation"),
    path("submissions/<uuid:submission_id>/confirm", views.confirm, name="confirm"),
    path("submissions/<uuid:submission_id>/repair", views.repair, name="repair"),
    path("submissions/<uuid:submission_id>/ask", views.ask, name="ask"),
    path("submissions/<uuid:submission_id>/questions/<int:question_id>/respond", views.respond, name="respond"),
    path("submissions/<uuid:submission_id>/revisions/<int:number>/handoff.zip", views.export, name="export"),
    path("submissions/<uuid:submission_id>/files/<uuid:upload_id>", views.download, name="download"),
    path("questions", views.contribute_question, name="questions"),
]
