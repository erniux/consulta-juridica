from common.text import tokenize


MATTER_RULES = {
    "occupational_risk": ["accidente", "riesgo", "incapacidad", "lesion", "caida"],
    "social_security": ["imss", "seguro", "social", "asegurado", "pension"],
    "labor_individual": ["despido", "renuncia", "patron", "salario", "jornada"],
}


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


def expand_query(prompt: str, matter: str, topics: list[str]) -> list[str]:
    expansions = [prompt]
    if matter == "occupational_risk":
        expansions.append("riesgo de trabajo incapacidad patron IMSS")
    if matter == "social_security":
        expansions.append("seguro social incapacidad trabajo imss")
    if matter == "labor_individual":
        expansions.append("relacion laboral renuncia despido derechos trabajador")
    for topic in topics:
        expansions.append(topic.replace("-", " "))
    return expansions
