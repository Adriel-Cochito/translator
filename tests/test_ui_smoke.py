from __future__ import annotations

from translator.config import AppMode, Settings
from translator.ui.overlay import OverlayWindow
from translator.ui.panel import ControlPanel


def test_control_panel_widgets(qapp) -> None:
    del qapp
    panel = ControlPanel()
    panel.apply_settings(Settings(mode=AppMode.SUBTITLE, subtitle_language="pt"))
    panel.show()
    assert panel.windowTitle() == "Translator Live"
    assert panel.start_button.text() == "Iniciar escuta"
    assert panel.mode_sub.isChecked()
    assert panel.subtitle_language.isEnabled()
    collected = panel.collect_settings(Settings())
    assert collected.mode is AppMode.SUBTITLE
    assert collected.subtitle_language == "pt"
    panel.close()


def test_overlay_placeholder(qapp) -> None:
    del qapp
    overlay = OverlayWindow()
    overlay.show()
    overlay.resize(640, 160)
    assert overlay.isVisible()
    assert overlay.visible_lines() == []
    overlay.close()
