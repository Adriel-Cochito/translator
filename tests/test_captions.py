from __future__ import annotations

from translator.pipeline.captions import (
    is_extension,
    is_same_speech,
    is_short_continuation,
    merge_caption_text,
    prefer_caption,
)
from translator.pipeline.events import CaptionLine


def test_same_speech_detects_overlap() -> None:
    short = "got memory and we've got the loop so let's take a look"
    long = "tools we've got memory and we've got the agentic loops let's take a look at these one at a time"
    assert is_same_speech(short, long) is True


def test_different_sentences_are_not_same() -> None:
    assert is_same_speech("hello everyone", "the weather is cold today") is False


def test_extension_grows_the_same_utterance() -> None:
    assert is_extension("we've got memory", "we've got memory and we've got the loop") is True
    assert is_extension("complete sentence here", "short") is False


def test_short_continuation_merges_needs() -> None:
    previous = (
        "So we can search the project sometimes with greplight text search, "
        "sometimes with semantic search or code indexes and then just pull in only the pieces"
    )
    assert is_short_continuation(previous, "it needs") is True
    assert "pieces it needs" in merge_caption_text(previous, "it needs")


def test_prefer_system_over_mic_echo() -> None:
    mic = CaptionLine(1, "Pessoa 1", "we've got memory", False, "mic")
    system = CaptionLine(2, "Pessoa 2", "we've got memory and the loop", False, "system")
    chosen = prefer_caption(mic, system)
    assert chosen.source == "system"
    assert chosen.speaker_name == "Pessoa 2"
