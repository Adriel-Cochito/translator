from __future__ import annotations

from translator.config import AppMode, Settings
from translator.pipeline.modes import asr_language, mode_label, needs_translation, translation_direction
from translator.translation.nllb import LANG_EN, LANG_PT, nllb_codes


def test_en_pt_uses_english_asr_and_translation() -> None:
    settings = Settings(mode=AppMode.EN_PT)
    assert asr_language(settings) == "en"
    assert needs_translation(settings) is True
    assert translation_direction(settings) == "en_pt"
    assert nllb_codes("en_pt") == (LANG_EN, LANG_PT)


def test_pt_en_uses_portuguese_asr_and_translation() -> None:
    settings = Settings(mode=AppMode.PT_EN)
    assert asr_language(settings) == "pt"
    assert needs_translation(settings) is True
    assert translation_direction(settings) == "pt_en"
    assert nllb_codes("pt_en") == (LANG_PT, LANG_EN)


def test_subtitle_mode_keeps_chosen_language() -> None:
    settings = Settings(mode=AppMode.SUBTITLE, subtitle_language="pt")
    assert asr_language(settings) == "pt"
    assert needs_translation(settings) is False
    assert translation_direction(settings) is None


def test_mode_labels_are_portuguese() -> None:
    assert "Inglês" in mode_label(AppMode.EN_PT)
    assert "Português" in mode_label(AppMode.PT_EN)
    assert "legenda" in mode_label(AppMode.SUBTITLE).lower()
