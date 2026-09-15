"""Accounts: private login identity, public author binding, roles, and identity claims.

A private login account and a public author identity are distinct. The
account carries a stable private UUID from creation; a verified, unique
``AuthorBinding`` links it to exactly one public ``AUTH-NNNN``. Changing a
display name or email never allocates a new author identity. Matching a name,
email string, ORCID text, or client-supplied AuthorID never grants ownership
of an existing identity — that requires a reviewed ``IdentityClaim``.
"""

from __future__ import annotations

import re
import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

AUTHOR_ID_VALIDATOR = RegexValidator(r"^AUTH-[0-9]{4}$", "AuthorID must look like AUTH-0001")
ORCID_RE = re.compile(r"^[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]$")


class AccountManager(BaseUserManager):
    use_in_migrations = True

    def _create(self, email, password, **extra):
        if not email:
            raise ValueError("an email address is required")
        account = self.model(email=self.normalize_email(email), **extra)
        account.set_password(password)
        account.save(using=self._db)
        return account

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.update(is_staff=True, is_superuser=True, role=Account.ADMINISTRATOR)
        return self._create(email, password, **extra)


class Account(AbstractBaseUser, PermissionsMixin):
    RESEARCHER, REVIEWER, ADMINISTRATOR = "researcher", "reviewer", "administrator"
    ROLES = [(RESEARCHER, "Researcher"), (REVIEWER, "Reviewer"), (ADMINISTRATOR, "Administrator")]

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=200)
    role = models.CharField(max_length=20, choices=ROLES, default=RESEARCHER)
    orcid = models.CharField(max_length=19, blank=True, default="",
                             help_text="Optional scholarly identity metadata. A typed ORCID is not proof of control.")
    publish_email = models.BooleanField(default=False, help_text="Email stays private unless the owner opts in.")
    terms_accepted_at = models.DateTimeField(null=True, blank=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    closed_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["display_name"]
    objects = AccountManager()

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.display_name} <{self.email}>"

    @property
    def is_reviewer(self) -> bool:
        return self.role in (self.REVIEWER, self.ADMINISTRATOR)

    @property
    def is_administrator(self) -> bool:
        return self.role == self.ADMINISTRATOR

    @property
    def author_id(self) -> str | None:
        # Query fresh: the reverse one-to-one cache can hold the pre-registration instance.
        row = AuthorBinding.objects.filter(account_id=self.pk).values_list("author_id", "state").first()
        if not row:
            return None
        author_id, state = row
        return author_id if state in (AuthorBinding.RESERVED, AuthorBinding.REGISTERED, AuthorBinding.LINKED) else None

    @property
    def verified(self) -> bool:
        return self.emailaddress_set.filter(verified=True, primary=True).exists()


class AuthorBinding(models.Model):
    """Unique link between one account and one public AuthorID."""

    PENDING, RESERVED, REGISTERED, LINKED, CLAIM_REQUESTED = "pending", "reserved", "registered", "linked", "claim_requested"
    STATES = [(s, s) for s in (PENDING, RESERVED, REGISTERED, LINKED, CLAIM_REQUESTED)]

    account = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="author_binding")
    author_id = models.CharField(max_length=9, unique=True, null=True, blank=True, validators=[AUTHOR_ID_VALIDATOR])
    state = models.CharField(max_length=20, choices=STATES, default=PENDING)
    operation_key = models.UUIDField(default=uuid.uuid4, unique=True, help_text="Public-safe key of the registration operation")
    evidence = models.TextField(blank=True, default="", help_text="How the binding was established (public-safe).")
    linked_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    linked_at = models.DateTimeField(null=True, blank=True)
    publication = models.ForeignKey("registry_bridge.Publication", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.account_id} -> {self.author_id or '(pending)'} [{self.state}]"


class IdentityClaim(models.Model):
    """Request to link an account to an *existing* public AuthorID; requires reviewer verification."""

    REQUESTED, VERIFIED, DENIED = "requested", "verified", "denied"
    STATES = [(s, s) for s in (REQUESTED, VERIFIED, DENIED)]

    account = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="identity_claims")
    author_id = models.CharField(max_length=9, validators=[AUTHOR_ID_VALIDATOR])
    evidence = models.TextField(help_text="What the claimant offers as evidence of control (public-safe summary).")
    state = models.CharField(max_length=12, choices=STATES, default=REQUESTED)
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["created_at"]
        constraints = [models.UniqueConstraint(fields=["account", "author_id"], condition=models.Q(state="requested"),
                                               name="one_open_claim_per_author_per_account")]


class ReviewAssignment(models.Model):
    """Grants a reviewer read access to one submission's private materials."""

    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="review_assignments")
    submission = models.ForeignKey("submissions.Submission", on_delete=models.CASCADE, related_name="review_assignments")
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name="+")
    assigned_at = models.DateTimeField(default=timezone.now)
    condition = models.CharField(max_length=120, help_text="Documented review trigger that authorized this assignment")

    class Meta:
        unique_together = [("reviewer", "submission")]
