from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from translator.config import AsrQuality, Settings
from translator.pipeline.setup_models import download_models, prefetch_whisper, warmup_optional_models


class SetupWorker(QObject):
    log = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, quality: AsrQuality) -> None:
        super().__init__()
        self.quality = quality

    def run(self) -> None:
        try:
            download_models(self.log.emit)
            warmup_optional_models(self.log.emit)
            prefetch_whisper(str(self.quality), self.log.emit)
            self.finished.emit(True, "Setup concluído.")
        except Exception as exc:
            self.finished.emit(False, str(exc))


class SetupDialog(QDialog):
    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self.setWindowTitle("Preparar Translator Live")
        self.setMinimumSize(560, 420)
        self.settings = settings
        self._ok = False
        self._thread: QThread | None = None
        self._worker: SetupWorker | None = None
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        title = QLabel("Primeira execução")
        title.setObjectName("title")
        body = QLabel(
            "Vou baixar os modelos locais (Whisper, NLLB e falantes) para "
            "%LOCALAPPDATA%\\TranslatorLive\\models. Isso pode levar vários minutos "
            "e usar cerca de 2–3 GB de disco."
        )
        body.setWordWrap(True)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        buttons = QHBoxLayout()
        self.start_button = QPushButton("Baixar e preparar")
        self.start_button.setObjectName("primary")
        self.close_button = QPushButton("Fechar")
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.close_button)
        layout.addWidget(title)
        layout.addWidget(body)
        layout.addWidget(self.log, 1)
        layout.addWidget(self.progress)
        layout.addLayout(buttons)
        self.start_button.clicked.connect(self._start)
        self.close_button.clicked.connect(self.reject)

    def succeeded(self) -> bool:
        return self._ok

    def _start(self) -> None:
        self.start_button.setEnabled(False)
        self.progress.show()
        self._append("Iniciando download...")
        self._thread = QThread(self)
        self._worker = SetupWorker(self.settings.asr_quality)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.log.connect(self._append)
        self._worker.finished.connect(self._done)
        self._thread.start()

    def _append(self, message: str) -> None:
        self.log.appendPlainText(message)

    def _done(self, ok: bool, message: str) -> None:
        self.progress.hide()
        self._append(message)
        self._ok = ok
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(2000)
        if ok:
            self.accept()
        else:
            self.start_button.setEnabled(True)
