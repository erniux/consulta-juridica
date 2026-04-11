import hashlib
import math
import re
import unicodedata
from collections import Counter


STOPWORDS = {
    "a",
    "al",
    "ante",
    "como",
    "con",
    "contra",
    "de",
    "del",
    "el",
    "en",
    "entre",
    "es",
    "esta",
    "este",
    "la",
    "las",
    "lo",
    "los",
    "mi",
    "para",
    "por",
    "que",
    "se",
    "sin",
    "su",
    "sus",
    "un",
    "una",
    "y",
}


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_text = ascii_text.lower()
    ascii_text = re.sub(r"[^a-z0-9\s/.-]", " ", ascii_text)
    return re.sub(r"\s+", " ", ascii_text).strip()


def tokenize(value: str) -> list[str]:
    return [
        token
        for token in normalize_text(value).split()
        if token and token not in STOPWORDS and len(token) > 2
    ]


def keyword_overlap_score(query: str, content: str) -> float:
    query_tokens = tokenize(query)
    if not query_tokens:
        return 0.0

    query_counter = Counter(query_tokens)
    content_counter = Counter(tokenize(content))
    matched = sum(min(count, content_counter[token]) for token, count in query_counter.items())
    return matched / max(len(query_tokens), 1)


def deterministic_embedding(value: str, dimensions: int = 16) -> list[float]:
    normalized = normalize_text(value)
    if not normalized:
        return [0.0] * dimensions

    digest = hashlib.sha256(normalized.encode("utf-8")).digest()
    vector = []
    for index in range(dimensions):
        byte = digest[index % len(digest)]
        centered = (byte / 255.0) * 2 - 1
        vector.append(round(centered, 6))
    return vector


def cosine_similarity(left: list[float] | None, right: list[float] | None) -> float:
    if left is None or right is None:
        return 0.0

    left_values = [float(value) for value in left]
    right_values = [float(value) for value in right]
    if not left_values or not right_values:
        return 0.0

    dot_product = sum(a * b for a, b in zip(left_values, right_values))
    left_norm = math.sqrt(sum(a * a for a in left_values))
    right_norm = math.sqrt(sum(b * b for b in right_values))
    if not left_norm or not right_norm:
        return 0.0
    return dot_product / (left_norm * right_norm)
