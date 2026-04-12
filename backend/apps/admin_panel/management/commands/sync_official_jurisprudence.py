from django.core.management.base import BaseCommand, CommandError

from apps.legal_indexing.services.jurisprudence_sync import (
    sync_jurisprudence_by_queries,
    sync_jurisprudence_for_prompt,
)


class Command(BaseCommand):
    help = "Syncs real jurisprudence from the official SJF web services."

    def add_arguments(self, parser):
        parser.add_argument(
            "--query",
            action="append",
            dest="queries",
            help="Jurisprudence query to execute against the official SJF web service. Repeat for multiple queries.",
        )
        parser.add_argument(
            "--prompt",
            dest="prompt",
            help="Prompt or case description used to generate jurisprudence queries automatically.",
        )
        parser.add_argument(
            "--max-results",
            dest="max_results",
            type=int,
            default=10,
            help="Maximum number of SJF search results to inspect per query.",
        )

    def handle(self, *args, **options):
        queries = options.get("queries") or []
        prompt = options.get("prompt") or ""
        max_results = options.get("max_results") or 10

        if bool(queries) == bool(prompt):
            raise CommandError("Use either --query or --prompt, but not both.")

        if prompt:
            documents = sync_jurisprudence_for_prompt(
                prompt,
                maximum_rows_per_query=max_results,
            )
        else:
            documents = sync_jurisprudence_by_queries(
                queries,
                maximum_rows_per_query=max_results,
            )

        self.stdout.write(self.style.SUCCESS(f"Synced jurisprudence documents: {len(documents)}"))
        for document in documents:
            self.stdout.write(
                f"- {document.digital_registry_number or 'sin-registro'} | {document.title}"
            )
