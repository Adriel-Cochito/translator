from __future__ import annotations

from typing import Never

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from translator.audio.devices import AudioDevice
from translator.config import AppMode, AsrQuality, Settings
from translator.pipeline.events import PipelineStatus, SpeakerInfo
from translator.pipeline.modes import mode_label
from translator.ui.styles import speaker_color


class ControlPanel(QMainWindow):
    start_requested = Signal()
    stop_requested = Signal()
    settings_changed = Signal()
    speaker_renamed = Signal(int, str)
    text_translate_requested = Signal(str)
    overlay_toggled = Signal(bool)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Translator Live")
        self.setMinimumSize(480, 620)
        self.resize(540, 780)
        self._speaker_ids: dict[int, int] = {}
        self._build()

    def _build(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Translator Live")
        title.setObjectName("title")
        subtitle = QLabel("Legendas e tradução local · EN ↔ PT")
        subtitle.setObjectName("status")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.status_label = QLabel("Parado")
        self.status_label.setObjectName("status")
        self.device_label = QLabel("Dispositivo: —")
        self.device_label.setObjectName("status")
        layout.addWidget(self.status_label)
        layout.addWidget(self.device_label)

        layout.addWidget(self._mode_group())
        layout.addWidget(self._audio_group())
        layout.addWidget(self._quality_group())
        layout.addWidget(self._speaker_group())
        layout.addWidget(self._text_group())
        layout.addStretch(1)

        buttons = QHBoxLayout()
        self.start_button = QPushButton("Iniciar escuta")
        self.start_button.setObjectName("primary")
        self.stop_button = QPushButton("Parar")
        self.stop_button.setObjectName("danger")
        self.stop_button.setEnabled(False)
        self.overlay_box = QCheckBox("Mostrar overlay de legendas")
        self.overlay_box.setChecked(True)
        buttons.addWidget(self.start_button, 1)
        buttons.addWidget(self.stop_button)
        layout.addLayout(buttons)
        layout.addWidget(self.overlay_box)

        hint = QLabel(
            "O YouTube só entra se o áudio do sistema estiver ligado e o dispositivo de "
            "loopback for o mesmo da caixa de som/fone onde o vídeo está tocando. "
            "As barrinhas azuis (mic) e amarelas (sistema) precisam se mexer."
        )
        hint.setWordWrap(True)
        hint.setObjectName("status")
        layout.addWidget(hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(root)
        self.setCentralWidget(scroll)
        self.start_button.clicked.connect(self.start_requested.emit)
        self.stop_button.clicked.connect(self.stop_requested.emit)
        self.overlay_box.toggled.connect(self.overlay_toggled.emit)
        self.mode_en_pt.toggled.connect(self._on_mode_toggled)
        self.mode_pt_en.toggled.connect(self._on_mode_toggled)
        self.mode_sub.toggled.connect(self._on_mode_toggled)
        self.subtitle_language.currentIndexChanged.connect(self._emit_settings)
        self.quality_turbo.toggled.connect(self._emit_settings)
        self.quality_medium.toggled.connect(self._emit_settings)
        self.quality_small.toggled.connect(self._emit_settings)
        self.mic_enabled.toggled.connect(self._emit_settings)
        self.system_enabled.toggled.connect(self._emit_settings)
        self.detect_voices.toggled.connect(self._emit_settings)
        self.mic_combo.currentIndexChanged.connect(self._emit_settings)
        self.system_combo.currentIndexChanged.connect(self._emit_settings)
        self.translate_button.clicked.connect(self._request_text_translate)
        self.rename_button.clicked.connect(self._rename_selected)

    def _mode_group(self) -> QGroupBox:
        box = QGroupBox("Modo")
        layout = QVBoxLayout(box)
        self.mode_group = QButtonGroup(self)
        self.mode_en_pt = QRadioButton(mode_label(AppMode.EN_PT))
        self.mode_pt_en = QRadioButton(mode_label(AppMode.PT_EN))
        self.mode_sub = QRadioButton(mode_label(AppMode.SUBTITLE))
        self.mode_en_pt.setChecked(True)
        for button in (self.mode_en_pt, self.mode_pt_en, self.mode_sub):
            self.mode_group.addButton(button)
            layout.addWidget(button)
        lang_row = QHBoxLayout()
        lang_row.addWidget(QLabel("Idioma da legenda:"))
        self.subtitle_language = QComboBox()
        self.subtitle_language.addItem("Inglês", "en")
        self.subtitle_language.addItem("Português", "pt")
        self.subtitle_language.setEnabled(False)
        lang_row.addWidget(self.subtitle_language, 1)
        layout.addLayout(lang_row)
        return box

    def _audio_group(self) -> QGroupBox:
        box = QGroupBox("Fontes de áudio")
        layout = QVBoxLayout(box)
        self.mic_enabled = QCheckBox("Microfone (só se você for falar)")
        self.mic_enabled.setChecked(False)
        self.mic_combo = QComboBox()
        self.mic_combo.setMinimumHeight(28)
        self.mic_level = QProgressBar()
        self.mic_level.setRange(0, 100)
        self.mic_level.setTextVisible(False)
        self.mic_level.setMinimumHeight(10)
        self.system_enabled = QCheckBox("Áudio do sistema")
        self.system_enabled.setChecked(True)
        self.system_combo = QComboBox()
        self.system_combo.setMinimumHeight(28)
        self.system_level = QProgressBar()
        self.system_level.setRange(0, 100)
        self.system_level.setTextVisible(False)
        self.system_level.setMinimumHeight(10)
        layout.addWidget(self.mic_enabled)
        layout.addWidget(self.mic_combo)
        layout.addWidget(self.mic_level)
        layout.addWidget(self.system_enabled)
        layout.addWidget(self.system_combo)
        layout.addWidget(self.system_level)
        tip = QLabel("Para YouTube/vídeo: deixe só o áudio do sistema ligado.")
        tip.setObjectName("status")
        tip.setWordWrap(True)
        layout.addWidget(tip)
        return box

    def _quality_group(self) -> QGroupBox:
        box = QGroupBox("Qualidade do reconhecimento")
        layout = QVBoxLayout(box)
        self.quality_turbo = QRadioButton("Turbo (rápido, ~1.5 GB VRAM)")
        self.quality_medium = QRadioButton("Medium (recomendado — mais preciso)")
        self.quality_small = QRadioButton("Small (mais leve)")
        self.quality_medium.setChecked(True)
        layout.addWidget(self.quality_turbo)
        layout.addWidget(self.quality_medium)
        layout.addWidget(self.quality_small)
        return box

    def _speaker_group(self) -> QGroupBox:
        box = QGroupBox("Pessoas nesta sessão")
        layout = QVBoxLayout(box)
        self.detect_voices = QCheckBox("Detectar várias vozes na mesma fonte")
        self.detect_voices.setChecked(False)
        self.detect_voices.setToolTip(
            "Desligado: 1 rótulo por fonte (Microfone / Vídeo). "
            "Ligado: tenta separar Pessoa 1, Pessoa 2… na mesma fonte."
        )
        self.speaker_list = QListWidget()
        self.speaker_list.setMinimumHeight(90)
        rename_row = QHBoxLayout()
        self.rename_edit = QLineEdit()
        self.rename_edit.setPlaceholderText("Novo nome")
        self.rename_button = QPushButton("Renomear")
        rename_row.addWidget(self.rename_edit, 1)
        rename_row.addWidget(self.rename_button)
        layout.addWidget(self.detect_voices)
        layout.addWidget(self.speaker_list)
        layout.addLayout(rename_row)
        return box

    def _text_group(self) -> QGroupBox:
        box = QGroupBox("Traduzir texto")
        layout = QVBoxLayout(box)
        self.text_input = QPlainTextEdit()
        self.text_input.setPlaceholderText("Cole ou digite uma frase para traduzir no modo atual.")
        self.text_input.setMinimumHeight(56)
        self.translate_button = QPushButton("Traduzir agora")
        self.text_output = QPlainTextEdit()
        self.text_output.setReadOnly(True)
        self.text_output.setMinimumHeight(56)
        self.text_output.setPlaceholderText("A tradução aparece aqui.")
        layout.addWidget(self.text_input)
        layout.addWidget(self.translate_button)
        layout.addWidget(self.text_output)
        return box

    def populate_devices(self, mics: list[AudioDevice], systems: list[AudioDevice]) -> None:
        self._fill_combo(self.mic_combo, mics)
        self._fill_combo(self.system_combo, systems)

    def apply_settings(self, settings: Settings) -> None:
        self._set_mode(settings.mode)
        index = self.subtitle_language.findData(settings.subtitle_language)
        if index >= 0:
            self.subtitle_language.setCurrentIndex(index)
        self.quality_turbo.setChecked(settings.asr_quality is AsrQuality.TURBO)
        self.quality_medium.setChecked(settings.asr_quality is AsrQuality.MEDIUM)
        self.quality_small.setChecked(settings.asr_quality is AsrQuality.SMALL)
        self.mic_enabled.setChecked(settings.mic_enabled)
        self.system_enabled.setChecked(settings.system_enabled)
        self.detect_voices.setChecked(settings.detect_multiple_voices)
        self._select_device(self.mic_combo, settings.mic_device)
        self._select_device(self.system_combo, settings.system_device)
        self.overlay_box.setChecked(settings.overlay_visible)

    def collect_settings(self, current: Settings) -> Settings:
        current.mode = self._current_mode()
        language = self.subtitle_language.currentData()
        current.subtitle_language = language if language in ("en", "pt") else "en"
        current.asr_quality = self._current_quality()
        current.mic_enabled = self.mic_enabled.isChecked()
        current.system_enabled = self.system_enabled.isChecked()
        current.detect_multiple_voices = self.detect_voices.isChecked()
        current.mic_device = self.mic_combo.currentData()
        current.system_device = self.system_combo.currentData()
        current.overlay_visible = self.overlay_box.isChecked()
        return current

    def set_listening(self, listening: bool) -> None:
        self.start_button.setEnabled(not listening)
        self.stop_button.setEnabled(listening)
        self.quality_turbo.setEnabled(not listening)
        self.quality_medium.setEnabled(not listening)
        self.quality_small.setEnabled(not listening)

    def set_status(self, status: PipelineStatus) -> None:
        prefix = "● " if status.listening else "○ "
        self.status_label.setText(f"{prefix}{status.message}")
        self.device_label.setText(f"Dispositivo: {status.device}  ·  ASR: {status.asr_model}")
        self.set_listening(status.listening)

    def set_levels(self, mic: float, system: float) -> None:
        self.mic_level.setValue(int(min(1.0, mic * 12.0) * 100))
        self.system_level.setValue(int(min(1.0, system * 12.0) * 100))

    def set_speakers(self, speakers: list[SpeakerInfo]) -> None:
        self.speaker_list.clear()
        self._speaker_ids.clear()
        for speaker in speakers:
            item = QListWidgetItem(f"{speaker.name}  ·  {self._source_label(speaker.source)}")
            item.setData(Qt.ItemDataRole.UserRole, speaker.speaker_id)
            item.setForeground(Qt.GlobalColor.white)
            item.setToolTip(speaker_color(speaker.speaker_id))
            self.speaker_list.addItem(item)
            self._speaker_ids[self.speaker_list.count() - 1] = speaker.speaker_id

    def set_text_translation(self, text: str) -> None:
        self.text_output.setPlainText(text)

    def _current_quality(self) -> AsrQuality:
        if self.quality_medium.isChecked():
            return AsrQuality.MEDIUM
        if self.quality_small.isChecked():
            return AsrQuality.SMALL
        return AsrQuality.TURBO

    def _current_mode(self) -> AppMode:
        if self.mode_pt_en.isChecked():
            return AppMode.PT_EN
        if self.mode_sub.isChecked():
            return AppMode.SUBTITLE
        return AppMode.EN_PT

    def _set_mode(self, mode: AppMode) -> None:
        match mode:
            case AppMode.EN_PT:
                self.mode_en_pt.setChecked(True)
            case AppMode.PT_EN:
                self.mode_pt_en.setChecked(True)
            case AppMode.SUBTITLE:
                self.mode_sub.setChecked(True)
            case _:
                never: Never = mode
                raise ValueError(f"Modo inválido: {never!r}")
        self.subtitle_language.setEnabled(mode is AppMode.SUBTITLE)

    def _on_mode_toggled(self) -> None:
        self.subtitle_language.setEnabled(self.mode_sub.isChecked())
        self._emit_settings()

    def _emit_settings(self) -> None:
        self.settings_changed.emit()

    def _request_text_translate(self) -> None:
        self.text_translate_requested.emit(self.text_input.toPlainText())

    def _rename_selected(self) -> None:
        item = self.speaker_list.currentItem()
        if item is None:
            return
        speaker_id = int(item.data(Qt.ItemDataRole.UserRole))
        self.speaker_renamed.emit(speaker_id, self.rename_edit.text())

    def _fill_combo(self, combo: QComboBox, devices: list[AudioDevice]) -> None:
        current = combo.currentData()
        combo.blockSignals(True)
        combo.clear()
        for device in devices:
            combo.addItem(device.name, device.id)
        self._select_device(combo, current)
        combo.blockSignals(False)

    def _select_device(self, combo: QComboBox, device_id: str | None) -> None:
        if device_id is None:
            return
        index = combo.findData(device_id)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _source_label(self, source: str) -> str:
        if source == "mic":
            return "microfone"
        return "sistema"
