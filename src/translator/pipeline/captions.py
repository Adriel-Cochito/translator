from __future__ import annotations

from translator.pipeline.events import CaptionLine


def normalize_caption(text: str) -> str:
    return " ".join(text.casefold().split())


def token_set(text: str) -> set[str]:
    return {token for token in normalize_caption(text).split() if len(token) > 2}


def is_same_speech(left: str, right: str) -> bool:
    first = normalize_caption(left)
    second = normalize_caption(right)
    if not first or not second:
        return False
    if first in second or second in first:
        return True
    left_tokens = token_set(left)
    right_tokens = token_set(right)
    if not left_tokens or not right_tokens:
        return False
    overlap = len(left_tokens & right_tokens) / float(min(len(left_tokens), len(right_tokens)))
    return overlap >= 0.72


def is_extension(previous: str, incoming: str) -> bool:
    before = normalize_caption(previous)
    after = normalize_caption(incoming)
    return bool(before) and before in after and len(after) > len(before)


def looks_incomplete(text: str) -> bool:
    cleaned = text.strip()
    if not cleaned:
        return True
    if cleaned[-1] in ".!?…":
        return False
    words = cleaned.split()
    if len(words) < 8:
        return True
    last = words[-1].casefold().strip(",;:")
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
        "o",
        "a",
        "de",
        "do",
        "da",
        "e",
        "que",
        "para",
    }
    return last in dangling


def is_short_continuation(previous: str, incoming: str) -> bool:
    """Junta '…pieces' + 'it needs' em uma linha só."""
    before = previous.strip()
    after = incoming.strip()
    if not before or not after:
        return False
    incoming_words = after.split()
    if len(incoming_words) > 5:
        return False
    if is_same_speech(before, after):
        return False
    if before.casefold().endswith(after.casefold()):
        return False
    return looks_incomplete(before) or len(incoming_words) <= 3


def merge_caption_text(previous: str, incoming: str) -> str:
    before = previous.strip()
    after = incoming.strip()
    if not before:
        return after
    if not after:
        return before
    if after.casefold() in before.casefold():
        return before
    if before.casefold() in after.casefold():
        return after
    if is_extension(before, after):
        return after
    return f"{before} {after}".strip()


def prefer_caption(previous: CaptionLine, incoming: CaptionLine) -> CaptionLine:
    if incoming.source == "system" and previous.source == "mic":
        return incoming
    if previous.source == "system" and incoming.source == "mic":
        if len(incoming.text) > len(previous.text) + 24:
            return incoming
        return previous
    if is_short_continuation(previous.text, incoming.text):
        merged = merge_caption_text(previous.text, incoming.text)
        return CaptionLine(
            incoming.speaker_id,
            incoming.speaker_name,
            merged,
            False,
            incoming.source,
        )
    return incoming if len(incoming.text) >= len(previous.text) else previous
