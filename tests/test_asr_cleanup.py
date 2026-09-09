from __future__ import annotations

from translator.asr.cleanup import clean_asr_text


def test_keeps_normal_speech() -> None:
    text = "We've got memory and the loop here with tools"
    assert clean_asr_text(f"  {text}. ") == text


def test_drops_watch_end_card() -> None:
    assert clean_asr_text("Thanks for watching") == ""


def test_drops_lonely_thank_you() -> None:
    assert clean_asr_text("Thank you.") == ""


def test_drops_short_hallucinations() -> None:
    assert clean_asr_text("perform a song") == ""
    assert clean_asr_text("in touch") == ""
    assert clean_asr_text("it knays") == ""


def test_keeps_short_tail_when_previous_incomplete() -> None:
    previous = (
        "So we can search the project sometimes with greplight text search, "
        "sometimes with semantic search or code indexes and then just pull in only the pieces"
    )
    assert clean_asr_text("it needs", previous=previous) == "it needs"


def test_drops_repeated_word() -> None:
    assert clean_asr_text("you you you you you you") == ""
