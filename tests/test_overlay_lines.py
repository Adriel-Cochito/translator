from __future__ import annotations

from translator.pipeline.events import CaptionLine
from translator.ui.overlay import OverlayWindow


def test_overlay_keeps_finals_and_replaces_partial(qapp) -> None:
    del qapp
    overlay = OverlayWindow()
    overlay.add_partial(CaptionLine(0, "Pessoa (microfone)", "hel", True, "mic"))
    overlay.add_partial(CaptionLine(0, "Pessoa (microfone)", "hello", True, "mic"))
    overlay.add_final(CaptionLine(1, "Pessoa 1", "hello there", False, "mic"))
    lines = overlay.visible_lines()
    assert len(lines) == 1
    assert lines[0].is_partial is False
    assert lines[0].text == "hello there"


def test_overlay_empty_message_explains_start(qapp) -> None:
    del qapp
    overlay = OverlayWindow()
    assert "Iniciar escuta" in overlay.empty_message()
    overlay.set_phase("listening")
    assert "YouTube" in overlay.empty_message()


def test_overlay_merges_echo_and_extensions(qapp) -> None:
    del qapp
    overlay = OverlayWindow()
    overlay.add_final(CaptionLine(1, "Pessoa 1", "we've got memory", False, "mic"))
    overlay.add_final(
        CaptionLine(2, "Pessoa 2", "we've got memory and we've got the loop", False, "system")
    )
    lines = overlay.visible_lines()
    assert len(lines) == 1
    assert lines[0].source == "system"
    overlay.add_final(
        CaptionLine(
            2,
            "Pessoa 2",
            "we've got memory and we've got the loop so let's look",
            False,
            "system",
        )
    )
    assert len(overlay.visible_lines()) == 1


def test_overlay_merges_short_tail(qapp) -> None:
    del qapp
    overlay = OverlayWindow()
    long_line = (
        "So we can search the project sometimes with greplight text search, "
        "sometimes with semantic search or code indexes and then just pull in only the pieces"
    )
    overlay.add_final(CaptionLine(1, "Vídeo", long_line, False, "system"))
    overlay.add_final(CaptionLine(1, "Vídeo", "it needs", False, "system"))
    lines = overlay.visible_lines()
    assert len(lines) == 1
    assert "pieces it needs" in lines[0].text


def test_overlay_rename_updates_existing_lines(qapp) -> None:
    del qapp
    overlay = OverlayWindow()
    overlay.add_final(CaptionLine(1, "Pessoa 1", "oi", False, "mic"))
    overlay.rename_speaker(1, "Você")
    assert overlay.visible_lines()[0].speaker_name == "Você"
