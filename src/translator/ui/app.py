from __future__ import annotations

import os
import sys
import traceback

from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import QApplication, QMessageBox

from translator.audio.devices import list_mic_devices, list_system_devices
from translator.config import Settings, load_settings, save_settings
from translator.pipeline.events import CaptionLine, PipelineStatus, SpeakerInfo
from translator.pipeline.orchestrator import PipelineOrchestrator
from translator.pipeline.setup_models import models_ready
from translator.ui.hotkeys import OverlayHotkey
from translator.ui.overlay import OverlayWindow
from translator.ui.panel import ControlPanel
from translator.ui.setup_dialog import SetupDialog
from translator.ui.styles import APP_QSS, make_app_icon
from translator.ui.tray import AppTray


class ModelLoadWorker(QObject):
    finished = Signal(bool, str)

    def __init__(self, pipeline: PipelineOrchestrator, settings: Settings) -> None:
        super().__init__()
        self.pipeline = pipeline
        self.settings = settings

    def run(self) -> None:
        try:
            self.pipeline.load_models(self.settings)
            self.finished.emit(True, "Modelos prontos.")
        except Exception as exc:
            self.finished.emit(False, str(exc))


class TranslatorApp(QObject):
    def __init__(self, qt_app: QApplication) -> None:
        super().__init__()
        self.qt_app = qt_app
        self.settings = load_settings()
        self.pipeline = PipelineOrchestrator()
        self.panel = ControlPanel()
        self.overlay = OverlayWindow()
        self.tray = AppTray(self.panel, self.overlay, self.quit_app)
        self.hotkey = OverlayHotkey(self.panel)
        self._load_thread: QThread | None = None
        self._load_worker: ModelLoadWorker | None = None
        self._connect()
        self._hydrate()

    def _connect(self) -> None:
        self.panel.start_requested.connect(self._start)
        self.panel.stop_requested.connect(self._stop)
        self.panel.settings_changed.connect(self._persist_from_panel)
        self.panel.speaker_renamed.connect(self._rename)
        self.panel.text_translate_requested.connect(self._translate_text)
        self.panel.overlay_toggled.connect(self._toggle_overlay)
        self.pipeline.partial_line.connect(self._on_partial)
        self.pipeline.final_line.connect(self._on_final)
        self.pipeline.speakers_changed.connect(self._on_speakers)
        self.pipeline.levels_changed.connect(self._on_levels)
        self.pipeline.status_changed.connect(self._on_status)
        self.pipeline.error_occurred.connect(self._on_error)
        self.pipeline.models_loaded.connect(self._on_models_loaded)
        self.qt_app.aboutToQuit.connect(self._cleanup)

    def _hydrate(self) -> None:
        self.panel.setWindowIcon(make_app_icon())
        self.overlay.setWindowIcon(make_app_icon())
        self.panel.populate_devices(list_mic_devices(), list_system_devices())
        self.panel.apply_settings(self.settings)
        self.overlay.apply_geometry(
            self.settings.overlay_x,
            self.settings.overlay_y,
            self.settings.overlay_width,
            self.settings.overlay_height,
        )
        self.overlay.set_overlay_opacity(self.settings.overlay_opacity)
        if not self.hotkey.register():
            self.panel.status_label.setText("○ Atalho Ctrl+Shift+L indisponível")

    def show_windows(self) -> None:
        self.panel.show()
        if self.settings.overlay_visible:
            self.overlay.show()
        self.tray.show()
        try:
            self.pipeline.start_capture(self._current_settings())
        except Exception as exc:
            self._on_error(f"Falha ao abrir o áudio: {exc}")

    def maybe_setup(self) -> bool:
        if os.environ.get("TRANSLATOR_SKIP_SETUP") == "1":
            return True
        if self.settings.setup_completed and models_ready():
            return True
        dialog = SetupDialog(self.settings)
        dialog.setStyleSheet(APP_QSS)
        result = dialog.exec()
        if result and dialog.succeeded():
            self.settings.setup_completed = True
            save_settings(self.settings)
            return True
        if models_ready():
            self.settings.setup_completed = True
            save_settings(self.settings)
            return True
        answer = QMessageBox.question(
            self.panel,
            "Continuar sem setup?",
            "Os modelos ainda não foram baixados por completo. "
            "Você pode abrir o app assim mesmo e tentar iniciar a escuta.",
        )
        return answer == QMessageBox.StandardButton.Yes

    def _current_settings(self) -> Settings:
        self.settings = self.panel.collect_settings(self.settings)
        self.settings.overlay_x = self.overlay.x()
        self.settings.overlay_y = self.overlay.y()
        self.settings.overlay_width = self.overlay.width()
        self.settings.overlay_height = self.overlay.height()
        return self.settings

    def _persist_from_panel(self) -> None:
        settings = self._current_settings()
        save_settings(settings)
        if self.pipeline.is_capturing() and not self.pipeline.is_listening():
            self.pipeline.start_capture(settings)

    @Slot()
    def _start(self) -> None:
        settings = self._current_settings()
        save_settings(settings)
        if not settings.mic_enabled and not settings.system_enabled:
            QMessageBox.warning(self.panel, "Sem fonte de áudio", "Ative o microfone ou o áudio do sistema.")
            return
        self.overlay.clear_lines()
        try:
            self.pipeline.start_capture(settings)
        except Exception as exc:
            QMessageBox.critical(self.panel, "Falha no áudio", str(exc))
            return
        self.overlay.set_phase("loading")
        self.panel.set_status(
            PipelineStatus(True, "Carregando modelos… o áudio já está aberto", "—", str(settings.asr_quality), "loading")
        )
        self.panel.set_listening(True)
        self._load_thread = QThread(self)
        self._load_worker = ModelLoadWorker(self.pipeline, settings)
        self._load_worker.moveToThread(self._load_thread)
        self._load_thread.started.connect(self._load_worker.run)
        self._load_worker.finished.connect(self._after_load)
        self._load_thread.start()

    def _after_load(self, ok: bool, message: str) -> None:
        if self._load_thread is not None:
            self._load_thread.quit()
            self._load_thread.wait(3000)
            self._load_thread = None
        if not ok:
            self.panel.set_listening(False)
            QMessageBox.critical(self.panel, "Falha ao carregar modelos", message)
            return
        try:
            self.pipeline.start(self._current_settings())
        except Exception as exc:
            self.panel.set_listening(False)
            QMessageBox.critical(self.panel, "Falha ao iniciar", str(exc))

    @Slot()
    def _stop(self) -> None:
        self.pipeline.stop()
        self._persist_from_panel()

    @Slot(int, str)
    def _rename(self, speaker_id: int, name: str) -> None:
        self.pipeline.rename_speaker(speaker_id, name)
        self.overlay.rename_speaker(speaker_id, name.strip() or f"Pessoa {speaker_id}")

    @Slot(str)
    def _translate_text(self, text: str) -> None:
        try:
            if not self.pipeline.is_ready():
                self.pipeline.load_models(self._current_settings())
            result = self.pipeline.translate_text(text)
            self.panel.set_text_translation(result)
        except Exception as exc:
            self.panel.set_text_translation(f"Erro: {exc}")

    @Slot(bool)
    def _toggle_overlay(self, visible: bool) -> None:
        self.settings.overlay_visible = visible
        self.overlay.setVisible(visible)
        save_settings(self.settings)

    @Slot(object)
    def _on_partial(self, line: CaptionLine) -> None:
        self.overlay.add_partial(line)

    @Slot(object)
    def _on_final(self, line: CaptionLine) -> None:
        self.overlay.add_final(line)

    @Slot(object)
    def _on_speakers(self, speakers: list[SpeakerInfo]) -> None:
        self.panel.set_speakers(speakers)

    @Slot(float, float)
    def _on_levels(self, mic: float, system: float) -> None:
        self.panel.set_levels(mic, system)
        self.overlay.set_levels(mic, system)

    @Slot(object)
    def _on_status(self, status: PipelineStatus) -> None:
        self.panel.set_status(status)
        self.overlay.set_phase(status.phase)

    @Slot(str)
    def _on_error(self, message: str) -> None:
        self.panel.status_label.setText(f"○ {message}")
        self.overlay.set_phase("preview")
        if "áudio" in message.lower() or "loopback" in message.lower() or "microfone" in message.lower():
            QMessageBox.warning(self.panel, "Áudio", message)

    @Slot(str)
    def _on_models_loaded(self, message: str) -> None:
        if self.pipeline.is_listening():
            return
        self.panel.status_label.setText(f"○ {message}")

    def _cleanup(self) -> None:
        try:
            self.pipeline.stop()
        except Exception:
            pass
        self.hotkey.unregister()
        save_settings(self._current_settings())

    def quit_app(self) -> None:
        self._cleanup()
        self.qt_app.quit()


def run_app() -> int:
    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("Translator Live")
    qt_app.setQuitOnLastWindowClosed(False)
    qt_app.setStyleSheet(APP_QSS)
    qt_app.setWindowIcon(make_app_icon())
    app = TranslatorApp(qt_app)
    if not app.maybe_setup():
        return 0
    app.show_windows()
    app.hotkey.activated.connect(lambda: app._toggle_overlay(not app.overlay.isVisible()))
    return qt_app.exec()


def excepthook(exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
    traceback.print_exception(exc_type, exc, tb)
