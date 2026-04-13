from django.core.management.base import BaseCommand, CommandError

from apps.legal_indexing.services.jurisprudence_sync import (
    get_jurisprudence_pack_queries,
    list_jurisprudence_packs,
    sync_jurisprudence_by_queries,
    sync_jurisprudence_for_prompt,
)


class Command(BaseCommand):
    help = "Syncs real jurisprudence from the official SCJN repositories."

    def add_arguments(self, parser):
        parser.add_argument(
            "--query",
            action="append",
            dest="queries",
            help="Jurisprudence query to execute against the official SCJN repository API. Repeat for multiple queries.",
        )
        parser.add_argument(
            "--pack",
            action="append",
            dest="packs",
            help="Predefined jurisprudence query pack to sync. Repeat for multiple packs.",
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
            help="Maximum number of SCJN search results to inspect per query.",
        )
        parser.add_argument(
            "--list-packs",
            action="store_true",
            dest="list_packs",
            help="Lists the predefined jurisprudence packs available for sync.",
        )

    def handle(self, *args, **options):
        queries = options.get("queries") or []
        packs = options.get("packs") or []
        prompt = options.get("prompt") or ""
        max_results = options.get("max_results") or 10
        should_list_packs = options.get("list_packs", False)

        if should_list_packs:
            for pack_name, config in sorted(list_jurisprudence_packs().items()):
                self.stdout.write(f"- {pack_name}: {config['description']}")
            return

        selected_modes = sum(bool(mode) for mode in (queries, packs, prompt))
        if selected_modes != 1:
            raise CommandError("Use exactly one of --query, --pack or --prompt.")

        if prompt:
            documents = sync_jurisprudence_for_prompt(
                prompt,
                maximum_rows_per_query=max_results,
            )
        elif packs:
            try:
                pack_queries = get_jurisprudence_pack_queries(packs)
            except ValueError as exc:
                raise CommandError(str(exc)) from exc
            documents = sync_jurisprudence_by_queries(
                pack_queries,
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
