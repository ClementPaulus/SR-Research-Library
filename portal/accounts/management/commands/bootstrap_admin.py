"""Grant the administrator role to an already-verified account named explicitly by the operator.

    python manage.py bootstrap_admin --email owner@example.org [--link-author AUTH-0001 --evidence "..."]

The first public registrant is never made an administrator; this command is the only bootstrap path.
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from accounts.models import Account, AuthorBinding
from core.models import record_event


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--link-author", help="Bind this account to an existing public AuthorID (verified out of band)")
        parser.add_argument("--evidence", default="", help="How the operator verified control of the existing identity")

    def handle(self, *args, **options):
        try:
            account = Account.objects.get(email=options["email"])
        except Account.DoesNotExist as exc:
            raise CommandError("no account with that email; the owner must sign up and verify first") from exc
        if not account.verified:
            raise CommandError("the account's email is not verified; bootstrap requires a verified owner identity")
        account.role = Account.ADMINISTRATOR
        account.is_staff = True
        account.save(update_fields=["role", "is_staff"])
        record_event("account.bootstrap_admin", account=account, actor_label="operator", reason="explicit operator bootstrap")
        self.stdout.write(f"{account.email} is now an administrator")
        if options["link_author"]:
            if not options["evidence"]:
                raise CommandError("--evidence is required when linking an existing AuthorID")
            if AuthorBinding.objects.filter(author_id=options["link_author"]).exclude(account=account).exists():
                raise CommandError(f"{options['link_author']} is already bound to another account")
            binding, _ = AuthorBinding.objects.get_or_create(account=account)
            binding.author_id = options["link_author"]
            binding.state = AuthorBinding.LINKED
            binding.evidence = f"Operator-verified link: {options['evidence']}"
            binding.linked_at = timezone.now()
            binding.save()
            record_event("author.claim_decided", account=account, actor_label="operator",
                         payload={"author_id": options["link_author"], "verified": True, "operator": True})
            self.stdout.write(f"{account.email} is linked to {options['link_author']}")
