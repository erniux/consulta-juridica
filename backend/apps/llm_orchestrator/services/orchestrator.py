from .providers import get_provider


def generate_consultation_answer(consultation, retrieval_hits, matter: str, topics: list[str]):
    provider = get_provider()
    return provider.generate_answer(consultation, retrieval_hits, matter, topics)
