"""Rebuild the public projection (search index, profiles, suggestions) from the committed registry.

    python manage.py reindex_registry [--sha COMMIT]
"""

from django.core.management.base import BaseCommand

from catalog.projection import refresh_projection


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument("--sha", default=None)

    def handle(self, *args, **options):
        snapshot = refresh_projection(options["sha"])
        self.stdout.write(f"projection refreshed at {snapshot.committed_sha} ({len(snapshot.search_index.get('documents', []))} documents)")
