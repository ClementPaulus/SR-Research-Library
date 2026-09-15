"""Account routes: signup/login/logout at top level, profile and identity controls in the workspace."""

from __future__ import annotations

from allauth.account import views as allauth_views
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotAllowed
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .models import AuthorBinding, IdentityClaim
from .services import request_identity_claim, revoke_other_sessions, start_author_registration

signup = allauth_views.signup
login = allauth_views.login
logout = allauth_views.logout


@login_required
def profile(request):
    binding = AuthorBinding.objects.filter(account=request.user).first()
    claims = IdentityClaim.objects.filter(account=request.user).order_by("-created_at")
    from catalog.projection import current_projection

    projection = current_projection()
    public_profile = projection.profiles.get(binding.author_id) if binding and binding.author_id else None
    return render(request, "accounts/profile.html", {
        "binding": binding, "claims": claims, "public_profile": public_profile,
        "verified": request.user.verified,
    })


@login_required
@require_POST
def update_profile(request):
    account = request.user
    display_name = request.POST.get("display_name", "").strip()
    if not display_name:
        messages.error(request, "A public display name is required.")
        return redirect("accounts:profile")
    account.display_name = display_name
    account.publish_email = request.POST.get("publish_email") == "on"
    account.save(update_fields=["display_name", "publish_email"])
    messages.success(request, "Profile updated. Your AuthorID is unchanged.")
    return redirect("accounts:profile")


@login_required
@require_POST
def claim_identity(request):
    author_id = request.POST.get("author_id", "").strip().upper()
    evidence = request.POST.get("evidence", "").strip()
    if not AuthorBinding._meta.get_field("author_id").validators[0].regex.match(author_id):
        messages.error(request, "Enter an existing AuthorID such as AUTH-0001.")
        return redirect("accounts:profile")
    if not evidence:
        messages.error(request, "Describe the evidence a reviewer can verify.")
        return redirect("accounts:profile")
    binding = AuthorBinding.objects.filter(account=request.user).first()
    if binding and binding.state in (AuthorBinding.REGISTERED, AuthorBinding.LINKED):
        messages.error(request, "This account already has a public author identity.")
        return redirect("accounts:profile")
    request_identity_claim(request.user, author_id, evidence)
    messages.info(request, "Your claim was recorded. Ownership is granted only after a reviewer verifies the evidence; "
                           "matching a name or ID is never enough.")
    return redirect("accounts:profile")


@login_required
@require_POST
def retry_registration(request):
    if not request.user.verified:
        messages.error(request, "Verify your email first.")
        return redirect("accounts:profile")
    start_author_registration(request.user)
    messages.info(request, "Author registration re-queued. The same identity is returned if one was already reserved.")
    return redirect("accounts:profile")


@login_required
@require_POST
def revoke_sessions(request):
    removed = revoke_other_sessions(request.user, request.session.session_key)
    messages.success(request, f"Signed out of {removed} other session(s). This session stays active.")
    return redirect("accounts:profile")


@login_required
def close_account(request):
    if request.method == "GET":
        return render(request, "accounts/close.html")
    if request.method != "POST":
        return HttpResponseNotAllowed(["GET", "POST"])
    from django.utils import timezone

    account = request.user
    account.is_active = False
    account.closed_at = timezone.now()
    account.save(update_fields=["is_active", "closed_at"])
    from core.models import record_event

    record_event("account.closed", account=account, actor=account, actor_label="researcher",
                 reason="Owner closed the account. Published research history is preserved under the withdrawal policy.")
    from django.contrib.auth import logout as dj_logout

    dj_logout(request)
    messages.info(request, "Your account is closed. Drafts are no longer accessible; previously published records remain in the library history.")
    return redirect("/")
