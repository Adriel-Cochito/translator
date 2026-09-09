from __future__ import annotations

from pathlib import Path
from typing import Literal, Never

from translator.asr.gpu import (
    DeviceChoice,
    cuda_vram_mb,
    detect_device,
    is_cuda_runtime_error,
    is_out_of_memory,
    nllb_runtime,
)
from translator.paths import nllb_dir

try:
    import ctranslate2
except ImportError:  # pragma: no cover
    ctranslate2 = None  # type: ignore[assignment]

try:
    from transformers import AutoTokenizer
except ImportError:  # pragma: no cover
    AutoTokenizer = None  # type: ignore[misc, assignment]


NLLB_CT2_REPO = "entai2965/nllb-200-distilled-600M-ctranslate2"
NLLB_TOKENIZER_REPO = "facebook/nllb-200-distilled-600M"

LANG_EN = "eng_Latn"
LANG_PT = "por_Latn"

TranslationDirection = Literal["en_pt", "pt_en"]


def nllb_codes(direction: TranslationDirection) -> tuple[str, str]:
    match direction:
        case "en_pt":
            return LANG_EN, LANG_PT
        case "pt_en":
            return LANG_PT, LANG_EN
        case _:
            never: Never = direction
            raise ValueError(f"Direção inválida: {never!r}")


class NllbTranslator:
    def __init__(self, model_dir: Path | None = None, device_choice: DeviceChoice | None = None) -> None:
        self.model_dir = model_dir or nllb_dir()
        self.device_choice = device_choice
        self.runtime_reason = "CPU, int8"
        self._translator = None
        self._tokenizer = None

    def load(self) -> None:
        if ctranslate2 is None or AutoTokenizer is None:
            raise RuntimeError("ctranslate2 ou transformers não está instalado.")
        model_path = resolve_nllb_model_path(self.model_dir)
        choice = self.device_choice or detect_device()
        device, compute_type = nllb_runtime(choice, cuda_vram_mb())
        try:
            self._translator = ctranslate2.Translator(str(model_path), device=device, compute_type=compute_type)
            self.runtime_reason = f"{device}, {compute_type}"
        except Exception as exc:
            if device == "cpu" or not (is_out_of_memory(exc) or is_cuda_runtime_error(exc)):
                raise
            self._translator = ctranslate2.Translator(str(model_path), device="cpu", compute_type="int8")
            self.runtime_reason = "CPU, int8 (fallback)"
        cache = self.model_dir / "tokenizer"
        cache.mkdir(parents=True, exist_ok=True)
        self._tokenizer = AutoTokenizer.from_pretrained(NLLB_TOKENIZER_REPO, cache_dir=str(cache))

    def translate(self, text: str, direction: TranslationDirection) -> str:
        if self._translator is None or self._tokenizer is None:
            raise RuntimeError("Tradutor NLLB ainda não foi carregado.")
        cleaned = text.strip()
        if not cleaned:
            return ""
        source_lang, target_lang = nllb_codes(direction)
        tokenizer = self._tokenizer
        tokenizer.src_lang = source_lang
        token_ids = tokenizer.encode(cleaned)
        source_tokens = tokenizer.convert_ids_to_tokens(token_ids)
        results = self._translator.translate_batch(
            [source_tokens],
            target_prefix=[[target_lang]],
            beam_size=4,
            max_decoding_length=256,
        )
        output_tokens = results[0].hypotheses[0]
        if output_tokens and output_tokens[0] == target_lang:
            output_tokens = output_tokens[1:]
        output_ids = tokenizer.convert_tokens_to_ids(output_tokens)
        return tokenizer.decode(output_ids, skip_special_tokens=True).strip()


def resolve_nllb_model_path(root: Path) -> Path:
    if (root / "model.bin").exists():
        return root
    for child in root.iterdir() if root.exists() else []:
        if child.is_dir() and (child / "model.bin").exists():
            return child
    raise FileNotFoundError(
        f"Modelo NLLB não encontrado em {root}. Execute o setup inicial para baixar."
    )


def nllb_is_ready(root: Path | None = None) -> bool:
    target = root or nllb_dir()
    try:
        resolve_nllb_model_path(target)
        return True
    except FileNotFoundError:
        return False
