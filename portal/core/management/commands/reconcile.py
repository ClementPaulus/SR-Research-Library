"""Run one reconciliation pass now: re-dispatch lost/expired jobs and resume in-flight publications.

    python manage.py reconcile [--due]

The beat schedule runs this automatically every PORTAL_RECONCILE_INTERVAL_SECONDS; the command exists for
operators and for acceptance runs that need to demonstrate recovery after an interruption. With --due,
pending jobs are made immediately retryable regardless of their backoff timer.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Job
from core.tasks import reconcile


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument("--due", action="store_true", help="ignore backoff timers and retry pending jobs now")

    def handle(self, *args, **options):
        if options["due"]:
            Job.objects.filter(state__in=[Job.QUEUED, Job.FAILED]).update(next_retry_at=timezone.now(), dispatched_at=None)
        result = reconcile()
        self.stdout.write(f"redispatched {result['redispatched']} job(s); {result['publications_checked']} publication(s) re-checked")
