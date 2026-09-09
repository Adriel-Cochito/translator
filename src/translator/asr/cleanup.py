from __future__ import annotations

import re


_JUNK_PHRASES = (
    "thanks for watching",
    "thank you for watching",
    "thank you",
    "thanks",
    "please subscribe",
    "like and subscribe",
    "subscribe to",
    "see you next time",
    "legendas pela",
    "inscreva-se",
    "obrigado por assistir",
    "obrigado",
    "perform a song",
    "in touch",
    "[music]",
    "(music)",
    "[applause]",
    "(applause)",
    "♪",
)

_SHORT_JUNK = {
    "thank you",
    "thanks",
    "obrigado",
    "ok",
    "okay",
    "yeah",
    "yes",
    "no",
    "hmm",
    "uh",
    "um",
    "ah",
    "oh",
    "in touch",
    "perform a song",
}

_REPEAT_TOKEN = re.compile(r"\b(\w+)(?:\s+\1){4,}\b", re.IGNORECASE)
_WORD = re.compile(r"[A-Za-zÀ-ÿ0-9']+")


def word_count(text: str) -> int:
    return len(_WORD.findall(text or ""))


def clean_asr_text(text: str, *, partial: bool = False, previous: str = "") -> str:
    cleaned = " ".join((text or "").replace("\n", " ").split()).strip(" .,!?;:-")
    cleaned = " ".join(cleaned.split()).strip()
    if not cleaned:
        return ""
    if _is_hallucination(cleaned):
        return ""
    words = word_count(cleaned)
    if previous and _is_short_tail(previous, cleaned) and words <= 5:
        return cleaned
    minimum = 6 if partial else 5
    if words < minimum:
        return ""
    return cleaned


def _is_short_tail(previous: str, incoming: str) -> bool:
    before = previous.strip()
    after = incoming.strip()
    if not before or not after:
        return False
    incoming_words = after.split()
    if len(incoming_words) > 5:
        return False
    if after.casefold() in before.casefold():
        return False
    if before[-1:] in ".!?…":
        return False
    last = before.split()[-1].casefold().strip(",;:")
    dangling = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "to",
        "of",
        "in",
        "on",
        "for",
        "with",
        "that",
        "just",
        "kind",
        "pieces",
        "only",
        "o",
        "de",
        "do",
        "da",
        "e",
        "que",
        "para",
    }
    return last in dangling or len(before.split()) >= 8


def _is_hallucination(text: str) -> bool:
    lowered = text.casefold().strip(" .,!?;:")
    tokens = [token for token in lowered.split() if token]
    if lowered in _SHORT_JUNK:
        return True
    if any(phrase == lowered for phrase in _JUNK_PHRASES):
        return True
    if any(phrase in lowered for phrase in _JUNK_PHRASES) and len(tokens) <= 10:
        return True
    if len(tokens) <= 2 and any(token in _SHORT_JUNK for token in tokens):
        return True
    if _REPEAT_TOKEN.search(text):
        return True
    words = [token for token in re.findall(r"\w+", lowered) if len(token) > 1]
    if words:
        top = max(words.count(token) for token in set(words))
        if top >= 5 and top / len(words) >= 0.45:
            return True
    letters = [char for char in text if char.isalpha()]
    if letters and len(set(char.casefold() for char in letters)) <= 2 and len(letters) >= 12:
        return True
    return False
