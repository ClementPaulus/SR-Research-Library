"""Signup form and allauth adapter: collect display name + terms, redirect to the workspace, start author registration."""

from __future__ import annotations

from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.forms import SignupForm
from django import forms
from django.utils import timezone


class PortalSignupForm(SignupForm):
    display_name = forms.CharField(
        max_length=200, label="Public display name",
        help_text="Shown on your public author profile and on accepted records.")
    orcid = forms.RegexField(
        regex=r"^[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]$", required=False, label="ORCID iD (optional)",
        help_text="Optional scholarly identity metadata. Typing an ORCID does not prove control of it.")
    accept_terms = forms.BooleanField(
        label="I understand that my display name and accepted contribution records are public, "
              "and that my email address stays private unless I choose to publish it.")

    field_order = ["display_name", "email", "orcid", "password1", "password2", "accept_terms"]

    def save(self, request):
        account = super().save(request)
        account.display_name = self.cleaned_data["display_name"].strip()
        account.orcid = self.cleaned_data.get("orcid") or ""
        account.terms_accepted_at = timezone.now()
        account.save(update_fields=["display_name", "orcid", "terms_accepted_at"])
        return account


class PortalAccountAdapter(DefaultAccountAdapter):
    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=False)
        user.display_name = form.cleaned_data.get("display_name", "").strip() or user.email.split("@")[0]
        if commit:
            user.save()
        return user

    def get_login_redirect_url(self, request):
        return "/workspace/"

    def get_email_verification_redirect_url(self, email_address):
        return "/workspace/"

    def confirm_email(self, request, email_address):
        super().confirm_email(request, email_address)
        from .services import start_author_registration

        start_author_registration(email_address.user)

    def is_open_for_signup(self, request):
        return True
