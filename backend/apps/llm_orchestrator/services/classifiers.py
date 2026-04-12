import re

from common.text import normalize_text, tokenize


MATTER_RULES = {
    "occupational_risk": ["accidente", "riesgo", "incapacidad", "lesion", "caida"],
    "social_security": ["imss", "seguro", "social", "asegurado", "pension"],
    "labor_individual": ["despido", "renuncia", "patron", "salario", "jornada"],
}

PRECISE_LOOKUP_PATTERN = re.compile(r"\barticulo\s+\d+[a-z-]*\b", re.IGNORECASE)
PRECISE_SOURCE_HINTS = (
    "ley federal del trabajo",
    "ley del seguro social",
    "lft",
    "lss",
)


def classify_matter(prompt: str) -> str:
    tokens = set(tokenize(prompt))
    for matter, keywords in MATTER_RULES.items():
        if tokens.intersection(keywords):
            return matter
    return "labor_individual"


def detect_topics(prompt: str) -> list[str]:
    tokens = set(tokenize(prompt))
    topics = []
    if tokens.intersection({"accidente", "riesgo", "incapacidad", "caida"}):
        topics.append("riesgo-de-trabajo")
    if tokens.intersection({"renuncia", "firma", "presion"}):
        topics.append("renuncia-forzada")
    if tokens.intersection({"imss", "seguro", "social", "incapacidad"}):
        topics.append("seguridad-social")
    if tokens.intersection({"despido", "terminacion", "separacion"}):
        topics.append("despido")
    return topics


def is_precise_legal_lookup(prompt: str) -> bool:
    normalized_prompt = normalize_text(prompt)
    return bool(
        PRECISE_LOOKUP_PATTERN.search(normalized_prompt)
        or any(hint in normalized_prompt for hint in PRECISE_SOURCE_HINTS)
    )


def expand_query(prompt: str, matter: str, topics: list[str]) -> list[str]:
    expansions = [prompt]
    normalized_prompt = normalize_text(prompt)
    prompt_tokens = tokenize(prompt)

    if is_precise_legal_lookup(prompt):
        if normalized_prompt and normalized_prompt != prompt:
            expansions.append(normalized_prompt)
        return list(dict.fromkeys(expansions))

    if len(prompt_tokens) <= 5:
        if normalized_prompt and normalized_prompt != prompt:
            expansions.append(normalized_prompt)
        return list(dict.fromkeys(expansions))

    if matter == "occupational_risk":
        expansions.append("riesgo de trabajo incapacidad patron IMSS")
    if matter == "social_security":
        expansions.append("seguro social incapacidad trabajo imss")
    if matter == "labor_individual":
        expansions.append("relacion laboral renuncia despido derechos trabajador")
    for topic in topics:
        expansions.append(topic.replace("-", " "))
    return list(dict.fromkeys(expansions))
