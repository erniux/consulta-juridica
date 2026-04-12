from django.core.management.base import BaseCommand, CommandError

from apps.legal_indexing.services.official_sync import (
    get_supported_official_slugs,
    sync_official_documents,
)


class Command(BaseCommand):
    help = "Downloads and indexes official legal documents from supported Mexican federal sources."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sources",
            nargs="+",
            dest="sources",
            help=(
                "Optional list of source slugs to sync. "
                f"Supported values: {', '.join(get_supported_official_slugs())}."
            ),
        )

    def handle(self, *args, **options):
        try:
            documents = sync_official_documents(options.get("sources"))
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        for document in documents:
            self.stdout.write(
                self.style.SUCCESS(
                    (
                        f"Synced {document.short_name} | version {document.version_label} | "
                        f"fragmentos {document.fragments.count()}"
                    )
                )
            )
