from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "accounts"

urlpatterns = [
    path("signup", views.signup, name="signup"),
    path("login", views.login, name="login"),
    path("logout", views.logout, name="logout"),
    path("password/reset", RedirectView.as_view(pattern_name="account_reset_password", permanent=False), name="password_reset"),
    path("verify", RedirectView.as_view(pattern_name="account_email_verification_sent", permanent=False), name="verify"),
    path("workspace/profile", views.profile, name="profile"),
    path("workspace/profile/update", views.update_profile, name="update_profile"),
    path("workspace/profile/claim", views.claim_identity, name="claim_identity"),
    path("workspace/profile/retry-registration", views.retry_registration, name="retry_registration"),
    path("workspace/profile/sessions/revoke", views.revoke_sessions, name="revoke_sessions"),
    path("workspace/profile/close", views.close_account, name="close_account"),
]
