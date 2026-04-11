from dataclasses import dataclass

from django.conf import settings

from apps.legal_documents.models import LegalDocument

from .prompts import BASE_LEGAL_PROMPT


@dataclass
class ProviderAnswer:
    answer: str
    citations: list[dict]
    model_name: str
    prompt_template: str


class BaseLLMProvider:
    provider_name = "base"

    def generate_answer(self, consultation, retrieval_hits, matter: str, topics: list[str]):
        raise NotImplementedError


class MockLLMProvider(BaseLLMProvider):
    provider_name = "mock"

    @staticmethod
    def _is_jurisprudence_document(document_type: str) -> bool:
        return document_type in {
            LegalDocument.DocumentType.THESIS,
            LegalDocument.DocumentType.PRECEDENT,
        }

    @staticmethod
    def _format_registry_suffix(document) -> str:
        if document.digital_registry_number:
            return f" (registro digital {document.digital_registry_number})"
        return ""

    def _build_jurisprudence_line(self, fragment, snippet: str, index: int) -> str:
        document = fragment.legal_document
        reference = document.title
        if fragment.title and fragment.title != document.title:
            reference = f"{reference} - {fragment.title}"
        return (
            f"- {reference}{self._format_registry_suffix(document)}: "
            f"{snippet[:180]} [{index}]"
        )

    def generate_answer(self, consultation, retrieval_hits, matter: str, topics: list[str]):
        citations = []
        normative_lines = []
        article_lines = []
        jurisprudence_lines = []

        for index, hit in enumerate(retrieval_hits, start=1):
            fragment = hit.fragment
            article_ref = f"art. {fragment.article_number}" if fragment.article_number else fragment.title
            document = fragment.legal_document
            label = f"[{index}] {document.short_name} - {article_ref}"
            if self._is_jurisprudence_document(document.document_type):
                label += self._format_registry_suffix(document)
            snippet = fragment.content[:280].strip()
            citations.append(
                {
                    "fragment": fragment,
                    "citation_label": label,
                    "snippet_used": snippet,
                    "order_index": index,
                }
            )

            doc_type = document.document_type
            normative_line = f"- {document.title}: {fragment.title} [{index}]"
            article_line = f"- {fragment.title}: {snippet[:180]} [{index}]"
            if self._is_jurisprudence_document(doc_type):
                jurisprudence_lines.append(
                    self._build_jurisprudence_line(fragment, snippet, index)
                )
            else:
                normative_lines.append(normative_line)
                article_lines.append(article_line)

        if not normative_lines:
            normative_lines.append("- No se recupero normativa suficiente para sustentar una respuesta publicable.")
        if not jurisprudence_lines:
            jurisprudence_lines.append("- No se localizaron tesis o precedentes relevantes en el indice actual.")

        topics_text = ", ".join(topic.replace("-", " ") for topic in topics) or "sin tema especifico detectado"
        analysis_points = [
            f"- Materia detectada: {matter.replace('_', ' ')}.",
            "- La respuesta se construyo con evidencia recuperada del indice juridico actual.",
            "- Se recomienda validar hechos, fechas, incapacidades emitidas y documentos firmados por la persona trabajadora.",
        ]

        answer = "\n".join(
            [
                "1. Resumen del caso",
                f"- Consulta recibida: {consultation.prompt}",
                f"- Temas detectados: {topics_text}.",
                "",
                "2. Normativa aplicable",
                *normative_lines,
                "",
                "3. Articulos relevantes",
                *article_lines[:4],
                "",
                "4. Jurisprudencia/tesis relacionadas",
                *jurisprudence_lines[:3],
                "",
                "5. Analisis preliminar",
                *analysis_points,
                "",
                "6. Informacion faltante",
                "- Fecha exacta del incidente o del acto patronal cuestionado.",
                "- Documento de incapacidad, alta medica y cualquier renuncia o convenio firmado.",
                "- Datos sobre aviso al IMSS, testigos y comunicaciones internas.",
                "",
                "7. Fuentes citadas",
                *[f"- {citation['citation_label']}" for citation in citations],
                "",
                f"Advertencia: {settings.APP_DISCLAIMER}",
            ]
        )
        return ProviderAnswer(
            answer=answer.strip(),
            citations=citations,
            model_name=settings.CHAT_MODEL,
            prompt_template=BASE_LEGAL_PROMPT,
        )


class OpenAIProvider(BaseLLMProvider):
    provider_name = "openai"

    def generate_answer(self, consultation, retrieval_hits, matter: str, topics: list[str]):
        raise NotImplementedError(
            "TODO: conectar proveedor LLM real usando OPENAI_API_KEY y un cliente oficial."
        )


def get_provider():
    provider_name = settings.LLM_PROVIDER.lower()
    if provider_name == "openai":
        return OpenAIProvider()
    return MockLLMProvider()
