from __future__ import annotations

import threading
import time

from PySide6.QtCore import QObject, Signal

from translator.asr.engine import AsrEngine
from translator.asr.gpu import detect_device
from translator.asr.streaming import UtteranceCollector, UtteranceEvent
from translator.asr.vad import create_speech_scorer
from translator.audio.mixer import AudioMixer
from translator.audio.types import AudioSource
from translator.config import AsrQuality, Settings
from translator.diarization.speakers import SpeakerRegistry, create_speaker_encoder
from translator.pipeline.captions import is_extension, is_same_speech
from translator.pipeline.events import CaptionLine, PipelineStatus, SpeakerInfo
from translator.pipeline.modes import asr_language, needs_translation, translation_direction
from translator.translation.nllb import NllbTranslator


class PipelineOrchestrator(QObject):
    partial_line = Signal(object)
    final_line = Signal(object)
    speakers_changed = Signal(object)
    levels_changed = Signal(float, float)
    status_changed = Signal(object)
    error_occurred = Signal(str)
    models_loaded = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._settings = Settings()
        self._mixer = AudioMixer(on_error=self._on_audio_error)
        self._collector: UtteranceCollector | None = None
        self._asr: AsrEngine | None = None
        self._translator: NllbTranslator | None = None
        self._speakers = SpeakerRegistry()
        self._running = False
        self._processing = False
        self._loaded = False
        self._requested_quality: AsrQuality | None = None
        self._lock = threading.Lock()
        self._worker: threading.Thread | None = None
        self._last_system_speech = 0.0
        self._recent_texts: list[tuple[float, str]] = []
        self._asr_prompt = ""

    def settings(self) -> Settings:
        return self._settings

    def update_settings(self, settings: Settings) -> None:
        self._settings = settings

    def is_listening(self) -> bool:
        return self._processing

    def is_capturing(self) -> bool:
        return self._running

    def is_ready(self) -> bool:
        return self._loaded

    def speaker_snapshot(self) -> list[SpeakerInfo]:
        return [
            SpeakerInfo(speaker.speaker_id, speaker.name, speaker.source)
            for speaker in self._speakers.speakers()
        ]

    def rename_speaker(self, speaker_id: int, name: str) -> None:
        self._speakers.rename(speaker_id, name)
        self.speakers_changed.emit(self.speaker_snapshot())

    def reset_speakers(self) -> None:
        self._speakers.reset()
        self.speakers_changed.emit(self.speaker_snapshot())

    def translate_text(self, text: str) -> str:
        if not self._loaded or self._translator is None:
            raise RuntimeError("O tradutor ainda não está pronto.")
        direction = translation_direction(self._settings)
        if direction is None:
            direction = "en_pt" if self._settings.subtitle_language == "en" else "pt_en"
        return self._translator.translate(text, direction)

    def load_models(self, settings: Settings) -> None:
        self._settings = settings
        self._requested_quality = settings.asr_quality
        device = detect_device()
        self._emit_status(True, "Carregando modelos… o áudio já está aberto", device.reason, str(settings.asr_quality), "loading")
        self._asr = AsrEngine(settings.asr_quality, device_choice=device)
        self._asr.load()
        self._translator = NllbTranslator()
        try:
            self._translator.load()
        except Exception as exc:
            self._translator = None
            if needs_translation(settings):
                raise RuntimeError(
                    f"Não foi possível carregar o tradutor NLLB: {exc}"
                ) from exc
        self._speakers = SpeakerRegistry(
            encoder=create_speaker_encoder(detect_multiple_voices=settings.detect_multiple_voices)
        )
        self._collector = UtteranceCollector(scorer=create_speech_scorer())
        self._loaded = True
        note = self._asr.fallback_message or f"Pronto ({self._asr.device_choice.reason})"
        if self._translator is None:
            note += " · tradução de texto indisponível até o setup"
        self.models_loaded.emit(note)
        phase = "listening" if self._processing else "stopped"
        self._emit_status(self._processing, note, self._asr.device_choice.reason, str(self._asr.used_quality), phase)

    def start_capture(self, settings: Settings) -> None:
        self._settings = settings
        self._mixer.start(
            settings.mic_enabled,
            settings.system_enabled,
            settings.mic_device,
            settings.system_device,
        )
        if not self._running:
            self._running = True
            self._worker = threading.Thread(target=self._loop, name="pipeline-worker", daemon=True)
            self._worker.start()
        if self._processing:
            self._emit_status(True, "Ouvindo…", self._device_label(), self._model_label(), "listening")
        else:
            self._emit_status(False, "Áudio aberto — clique em Iniciar escuta", self._device_label(), self._model_label(), "preview")

    def start(self, settings: Settings) -> None:
        self._settings = settings
        self.start_capture(settings)
        if not self._loaded:
            self.load_models(settings)
        elif self._asr is not None and self._requested_quality != settings.asr_quality:
            self._requested_quality = settings.asr_quality
            self._asr = AsrEngine(settings.asr_quality, device_choice=self._asr.device_choice)
            self._asr.load()
        if self._collector is None:
            self._collector = UtteranceCollector(scorer=create_speech_scorer())
        self._collector.reset()
        self._speakers.reset()
        self._speakers = SpeakerRegistry(
            encoder=create_speaker_encoder(detect_multiple_voices=settings.detect_multiple_voices)
        )
        self._last_system_speech = 0.0
        self._recent_texts = []
        self._asr_prompt = ""
        self.speakers_changed.emit(self.speaker_snapshot())
        self._processing = True
        self._emit_status(True, "Ouvindo… fale ou toque o YouTube", self._device_label(), self._model_label(), "listening")

    def stop(self) -> None:
        self._processing = False
        self._running = False
        self._mixer.stop()
        if self._worker is not None:
            self._worker.join(timeout=2.5)
            self._worker = None
        self._emit_status(False, "Parado", self._device_label(), self._model_label(), "stopped")
        self.levels_changed.emit(0.0, 0.0)

    def _loop(self) -> None:
        while self._running:
            chunk = self._mixer.poll(0.05)
            mic_level, system_level = self._mixer.levels()
            self.levels_changed.emit(mic_level, system_level)
            if chunk is None or not self._processing or self._collector is None:
                continue
            try:
                events = self._collector.feed(chunk)
                for event in events:
                    self._handle_event(event)
            except Exception as exc:
                self.error_occurred.emit(str(exc))

    def _device_label(self) -> str:
        if self._asr is not None:
            return self._asr.device_choice.reason
        return detect_device().reason

    def _model_label(self) -> str:
        if self._asr is not None:
            return str(self._asr.used_quality)
        return str(self._settings.asr_quality)

    def _handle_event(self, event: UtteranceEvent) -> None:
        with self._lock:
            if self._is_echo(event):
                return
            language = asr_language(self._settings)
            if event.kind == "partial":
                text = self._transcribe(event.audio, language, partial=True)
                if not text or self._is_recent_duplicate(text):
                    return
                speaker = self._speakers.last_for_source(event.source)
                speaker_id = speaker.speaker_id if speaker else 0
                name = speaker.name if speaker else self._provisional_name(event.source)
                self.partial_line.emit(
                    CaptionLine(speaker_id, name, text, True, event.source)
                )
                return
            if event.kind == "final":
                text = self._transcribe(event.audio, language, partial=False)
                if not text or self._is_recent_duplicate(text):
                    return
                speaker = self._speakers.assign(event.audio, event.source)
                display = text
                if needs_translation(self._settings) and self._translator is not None:
                    direction = translation_direction(self._settings)
                    if direction is not None:
                        display = self._translator.translate(text, direction) or text
                if event.source == "system":
                    self._last_system_speech = time.monotonic()
                self._asr_prompt = text
                self._remember(display)
                self.final_line.emit(
                    CaptionLine(speaker.speaker_id, speaker.name, display, False, event.source)
                )
                self.speakers_changed.emit(self.speaker_snapshot())
                return
            never_kind = event.kind
            raise ValueError(f"Evento de fala inválido: {never_kind!r}")

    def _is_echo(self, event: UtteranceEvent) -> bool:
        if event.source != "mic":
            return False
        if not self._settings.system_enabled:
            return False
        # O microfone escuta a caixa/fone e vira uma "segunda pessoa" falsa.
        if (time.monotonic() - self._last_system_speech) < 3.5:
            return True
        _mic_level, system_level = self._mixer.levels()
        return system_level > 0.008

    def _is_recent_duplicate(self, text: str) -> bool:
        now = time.monotonic()
        self._recent_texts = [(stamp, saved) for stamp, saved in self._recent_texts if now - stamp < 12.0]
        for _stamp, saved in self._recent_texts:
            if is_extension(saved, text):
                return False
            if is_same_speech(text, saved) and len(text) <= len(saved) + 8:
                return True
        return False

    def _remember(self, text: str) -> None:
        kept = [
            (stamp, saved)
            for stamp, saved in self._recent_texts
            if not is_same_speech(saved, text)
        ]
        kept.append((time.monotonic(), text))
        self._recent_texts = kept[-8:]

    def _transcribe(self, audio, language: str, *, partial: bool) -> str:
        if self._asr is None:
            return ""
        return self._asr.transcribe(audio, language, partial=partial, prompt=self._asr_prompt).text

    def _provisional_name(self, source: AudioSource) -> str:
        if source == "mic":
            return "Microfone"
        return "Vídeo"

    def _emit_status(
        self,
        listening: bool,
        message: str,
        device: str,
        model: str,
        phase: str = "stopped",
    ) -> None:
        self.status_changed.emit(PipelineStatus(listening, message, device, model, phase))

    def _on_audio_error(self, message: str) -> None:
        self.error_occurred.emit(message)
