import re

from common.text import normalize_text, tokenize


MATTER_RULES = {
    "occupational_risk": [
        "accidente",
        "riesgo",
        "incapacidad",
        "lesion",
        "caida",
        "amputacion",
        "dedo",
        "dedos",
        "mano",
        "falange",
        "perdida",
        "fractura",
        "indemnizacion",
    ],
    "social_security": ["imss", "seguro", "social", "asegurado", "pension", "buzon"],
    "labor_individual": ["despido", "renuncia", "patron", "salario", "jornada"],
}

JURISPRUDENCE_FACET_RULES = {
    "occupational_risk_hand_injury": {
        "keywords": {
            "accidente",
            "riesgo",
            "dedo",
            "dedos",
            "mano",
            "amputacion",
            "falange",
            "incapacidad",
            "indemnizacion",
        },
        "queries": [
            "riesgo de trabajo amputacion dedos mano incapacidad permanente parcial indemnizacion patron",
            "accidente de trabajo perdida de dedos mano obligaciones patronales imss indemnizacion",
        ],
    },
    "pregnancy_dismissal": {
        "keywords": {
            "embarazo",
            "embarazada",
            "maternidad",
            "gestacion",
            "lactancia",
            "despido",
            "despidieron",
            "corrio",
        },
        "queries": [
            "despido embarazo trabajadora embarazada discriminacion maternidad estabilidad laboral",
            "proteccion reforzada maternidad despido embarazo reinstalacion indemnizacion",
        ],
    },
    "honorarios_subordination": {
        "keywords": {
            "honorarios",
            "subordinacion",
            "asimilados",
            "factura",
            "recibos",
            "jefe",
            "horario",
            "prestacion",
        },
        "queries": [
            "honorarios subordinacion relacion laboral simulacion prestaciones despido",
            "contrato por honorarios relacion laboral subordinada jurisprudencia trabajador",
        ],
    },
    "psychological_harm": {
        "keywords": {
            "estres",
            "stress",
            "psicologico",
            "psicologica",
            "emocional",
            "ansiedad",
            "depresion",
            "hostigamiento",
            "acoso",
            "mobbing",
            "burnout",
        },
        "queries": [
            "despido dano psicologico dano emocional estres laboral hostigamiento acoso",
            "dano moral trabajador afectacion psicologica despido hostigamiento laboral",
        ],
    },
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
    if tokens.intersection(
        {"accidente", "riesgo", "incapacidad", "caida", "amputacion", "dedo", "dedos", "mano", "falange"}
    ):
        topics.append("riesgo-de-trabajo")
    if tokens.intersection({"renuncia", "firma", "presion"}):
        topics.append("renuncia-forzada")
    if tokens.intersection({"imss", "seguro", "social", "incapacidad"}):
        topics.append("seguridad-social")
    if tokens.intersection({"despido", "terminacion", "separacion"}):
        topics.append("despido")
    if tokens.intersection({"indemnizacion", "porcentaje", "valuacion", "amputacion", "dedos", "mano"}):
        topics.append("indemnizacion-riesgo-trabajo")
    if tokens.intersection({"embarazo", "embarazada", "maternidad", "gestacion", "lactancia"}):
        topics.append("despido-embarazo")
    if tokens.intersection({"honorarios", "subordinacion", "asimilados", "factura", "jefe", "horario"}):
        topics.append("honorarios-subordinacion")
    if tokens.intersection({"estres", "stress", "psicologico", "psicologica", "emocional", "ansiedad", "depresion"}):
        topics.append("dano-psicologico")
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


def generate_jurisprudence_queries(prompt: str, matter: str, topics: list[str]) -> list[str]:
    normalized_prompt = normalize_text(prompt)
    prompt_tokens = set(tokenize(prompt))
    queries = [prompt]

    if normalized_prompt and normalized_prompt != prompt:
        queries.append(normalized_prompt)

    for facet in JURISPRUDENCE_FACET_RULES.values():
        if prompt_tokens.intersection(facet["keywords"]):
            queries.extend(facet["queries"])

    if matter == "occupational_risk":
        queries.append("riesgo de trabajo obligaciones patronales imss indemnizacion incapacidad")
    if matter == "social_security":
        queries.append("seguridad social trabajador prestaciones imss criterio jurisprudencial")
    if matter == "labor_individual":
        queries.append("relacion laboral despido prestaciones subordinacion criterio jurisprudencial")

    topic_query_map = {
        "riesgo-de-trabajo": "accidente de trabajo incapacidad permanente parcial indemnizacion jurisprudencia",
        "seguridad-social": "imss prestaciones trabajador seguridad social jurisprudencia",
        "renuncia-forzada": "renuncia forzada presion patronal eficacia probatoria jurisprudencia",
        "despido": "despido injustificado reinstalacion indemnizacion jurisprudencia laboral",
        "indemnizacion-riesgo-trabajo": "indemnizacion riesgo de trabajo valuacion dano incapacidad permanente",
        "despido-embarazo": "embarazo maternidad despido discriminacion estabilidad reforzada",
        "honorarios-subordinacion": "honorarios subordinacion relacion laboral simulada",
        "dano-psicologico": "dano psicologico estres acoso laboral dano moral trabajador",
    }
    for topic in topics:
        query = topic_query_map.get(topic)
        if query:
            queries.append(query)

    return list(dict.fromkeys(query for query in queries if query))
