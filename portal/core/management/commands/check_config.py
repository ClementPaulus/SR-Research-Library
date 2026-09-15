"""Validate deployment inputs at startup and name any missing external provisioning precisely.

    python manage.py check_config [--strict]

Exit code 1 when a required input for the active settings module is missing.
"""

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument("--strict", action="store_true", help="treat production requirements as required even in dev")

    def handle(self, *args, **options):
        production = options["strict"] or settings.SETTINGS_MODULE.endswith(".prod")
        problems, notes = [], []
        if not settings.SECRET_KEY or settings.SECRET_KEY.startswith(("insecure-", "test-only", "local-development")):
            (problems if production else notes).append("DJANGO_SECRET_KEY is a development placeholder")
        if settings.DATABASES["default"]["ENGINE"].endswith("sqlite3"):
            (problems if production else notes).append("DATABASE_URL points at SQLite; PostgreSQL is required for real deployments")
        if settings.EMAIL_BACKEND != "django.core.mail.backends.smtp.EmailBackend":
            (problems if production else notes).append(f"EMAIL_BACKEND={settings.EMAIL_BACKEND} captures mail locally; real verification email is not delivered")
        if settings.PORTAL_STORAGE_BACKEND != "s3":
            (problems if production else notes).append("PORTAL_STORAGE_BACKEND=filesystem; S3-compatible storage is required for real deployments")
        if settings.PORTAL_GITHUB_ADAPTER.endswith("FakeGitHubClient"):
            (problems if production else notes).append("PORTAL_GITHUB_ADAPTER is the git-backed test double; no real GitHub writes will occur")
        else:
            for name in ("GITHUB_REPO_OWNER", "GITHUB_REPO_NAME", "GITHUB_APP_ID", "GITHUB_APP_INSTALLATION_ID", "GITHUB_WEBHOOK_SECRET"):
                if not getattr(settings, name):
                    problems.append(f"{name} is not set (GitHub App provisioning incomplete)")
            if not (settings.GITHUB_APP_PRIVATE_KEY or settings.GITHUB_APP_PRIVATE_KEY_PATH):
                problems.append("GITHUB_APP_PRIVATE_KEY or GITHUB_APP_PRIVATE_KEY_PATH is not set")
        if not settings.PORTAL_PUBLIC_BASE_URL.startswith("https://") and production:
            problems.append("PORTAL_PUBLIC_BASE_URL must be https in production")
        if not settings.PORTAL_ADMIN_BOOTSTRAP_EMAIL:
            notes.append("PORTAL_ADMIN_BOOTSTRAP_EMAIL is unset; use `manage.py bootstrap_admin --email ...` explicitly")
        repo = settings.PORTAL_REGISTRY_REPO_PATH
        if not (repo / "validators" / "gates.py").exists():
            problems.append(f"PORTAL_REGISTRY_REPO_PATH={repo} does not contain the validators engine")
        for line in notes:
            self.stdout.write(f"note: {line}")
        for line in problems:
            self.stderr.write(f"missing: {line}")
        if problems:
            raise SystemExit(1)
        self.stdout.write("configuration complete for the active settings module")
