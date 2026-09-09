from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Never

import numpy as np

from translator.asr.cleanup import clean_asr_text
from translator.asr.gpu import DeviceChoice, detect_device, is_cuda_runtime_error, is_out_of_memory
from translator.config import AsrQuality
from translator.paths import whisper_dir

try:
    from faster_whisper import WhisperModel
except ImportError:  # pragma: no cover - optional until setup
    WhisperModel = None  # type: ignore[misc, assignment]


@dataclass
class AsrResult:
    text: str
    language: str


class AsrEngine:
    def __init__(
        self,
        quality: AsrQuality,
        download_root: Path | None = None,
        device_choice: DeviceChoice | None = None,
    ) -> None:
        self.quality = quality
        self.download_root = download_root or whisper_dir()
        self.device_choice = device_choice or detect_device()
        self.used_quality = quality
        self.fallback_message: str | None = None
        self._model = None

    def load(self) -> None:
        self._model = self._load_quality(self.quality)
        if self.fallback_message is None:
            self.used_quality = self.quality
        self._probe()

    def transcribe(
        self,
        audio: np.ndarray,
        language: str,
        *,
        partial: bool = False,
        prompt: str = "",
    ) -> AsrResult:
        if self._model is None:
            raise RuntimeError("Modelo Whisper ainda não foi carregado.")
        min_samples = 16000 if partial else 20000
        if audio.size < min_samples:
            return AsrResult(text="", language=language)

        # Normaliza áudio baixo do loopback (YouTube/fone) sem estourar.
        samples = audio.astype(np.float32, copy=False)
        peak = float(np.max(np.abs(samples))) if samples.size else 0.0
        if 1e-4 < peak < 0.18:
            samples = np.clip(samples * min(0.85 / peak, 3.5), -1.0, 1.0)

        beam = 1 if partial else 5
        options = {
            "language": language,
            "task": "transcribe",
            "beam_size": beam,
            "best_of": 1 if partial else 5,
            "temperature": 0.0 if partial else [0.0, 0.2],
            "vad_filter": False,
            "condition_on_previous_text": False,
            "without_timestamps": True,
            "compression_ratio_threshold": 2.0,
            "log_prob_threshold": -0.6,
            "no_speech_threshold": 0.55,
            "repetition_penalty": 1.15,
            "no_repeat_ngram_size": 4,
        }
        cleaned_prompt = " ".join(prompt.split())[-180:]
        if cleaned_prompt:
            options["initial_prompt"] = cleaned_prompt
        segments, _info = self._model.transcribe(samples, **options)
        parts: list[str] = []
        for segment in segments:
            piece = clean_asr_text(segment.text or "", partial=partial, previous=cleaned_prompt)
            if piece:
                parts.append(piece)
        return AsrResult(
            text=clean_asr_text(" ".join(parts), partial=partial, previous=cleaned_prompt),
            language=language,
        )

    def _load_quality(self, quality: AsrQuality):
        if WhisperModel is None:
            raise RuntimeError("faster-whisper não está instalado.")
        try:
            return WhisperModel(
                str(quality),
                device=self.device_choice.device,
                compute_type=self.device_choice.compute_type,
                download_root=str(self.download_root),
            )
        except Exception as exc:
            lighter = _lighter_quality(quality)
            if lighter is not quality and (is_out_of_memory(exc) or is_cuda_runtime_error(exc)):
                self.fallback_message = f"VRAM insuficiente para {quality}; usando {lighter}."
                self.used_quality = lighter
                return WhisperModel(
                    str(lighter),
                    device=self.device_choice.device,
                    compute_type=self.device_choice.compute_type,
                    download_root=str(self.download_root),
                )
            if self.device_choice.device == "cuda":
                self.device_choice = DeviceChoice("cpu", "int8", "CPU (falha na GPU)")
                self.fallback_message = f"GPU indisponível ({exc}). Usando CPU — vai ficar mais lento."
                cpu_quality = AsrQuality.SMALL if quality is AsrQuality.TURBO else quality
                self.used_quality = cpu_quality
                return WhisperModel(
                    str(cpu_quality),
                    device="cpu",
                    compute_type="int8",
                    download_root=str(self.download_root),
                )
            raise

    def _probe(self) -> None:
        silence = np.zeros(16000, dtype=np.float32)
        try:
            self.transcribe(silence, "en", partial=True)
        except Exception as exc:
            if self.device_choice.device != "cuda" or not is_cuda_runtime_error(exc):
                raise
            if WhisperModel is None:
                raise
            self.device_choice = DeviceChoice("cpu", "int8", "CPU (falha na GPU)")
            self.fallback_message = f"GPU indisponível ({exc}). Usando CPU — vai ficar mais lento."
            self.used_quality = _lighter_quality(self.quality)
            self._model = WhisperModel(
                str(self.used_quality),
                device="cpu",
                compute_type="int8",
                download_root=str(self.download_root),
            )


def _lighter_quality(quality: AsrQuality) -> AsrQuality:
    match quality:
        case AsrQuality.TURBO:
            return AsrQuality.MEDIUM
        case AsrQuality.MEDIUM:
            return AsrQuality.SMALL
        case AsrQuality.SMALL:
            return AsrQuality.SMALL
        case _:
            never: Never = quality
            raise ValueError(f"Qualidade inválida: {never!r}")

