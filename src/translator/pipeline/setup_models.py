from __future__ import annotations

from collections.abc import Callable

from translator.asr.gpu import cuda_vram_mb, detect_device, nllb_runtime
from translator.paths import ecapa_dir, nllb_dir, silero_dir, whisper_dir
from translator.ssl_certs import ensure_tls, is_ssl_error, retry_insecure_tls
from translator.translation.nllb import NLLB_CT2_REPO, NLLB_TOKENIZER_REPO, nllb_is_ready

try:
    from huggingface_hub import snapshot_download
except ImportError:  # pragma: no cover
    snapshot_download = None  # type: ignore[assignment]

try:
    from transformers import AutoTokenizer
except ImportError:  # pragma: no cover
    AutoTokenizer = None  # type: ignore[misc, assignment]

try:
    from faster_whisper import WhisperModel
except ImportError:  # pragma: no cover
    WhisperModel = None  # type: ignore[misc, assignment]

try:
    from silero_vad import load_silero_vad
except ImportError:  # pragma: no cover
    load_silero_vad = None  # type: ignore[assignment]

try:
    from speechbrain.inference.speaker import EncoderClassifier
    from speechbrain.utils.fetching import LocalStrategy
except ImportError:  # pragma: no cover
    EncoderClassifier = None  # type: ignore[misc, assignment]
    LocalStrategy = None  # type: ignore[misc, assignment]


ProgressCallback = Callable[[str], None]


def models_ready() -> bool:
    return nllb_is_ready()


def whisper_marker_exists() -> bool:
    root = whisper_dir()
    if not root.exists():
        return False
    return any(root.iterdir())


def download_models(progress: ProgressCallback | None = None) -> None:
    log = progress or (lambda _message: None)
    ensure_tls()
    log("Detectando GPU...")
    device = detect_device()
    log(f"Dispositivo: {device.reason}")
    nllb_device, nllb_compute = nllb_runtime(device, cuda_vram_mb())
    log(f"Tradução NLLB: {nllb_device}, {nllb_compute}")

    log("Baixando modelo de tradução NLLB...")
    _download_nllb(log)

    log("Preparando Whisper (pode baixar na primeira transcrição)...")
    whisper_dir()
    log(f"Pasta do Whisper: {whisper_dir()}")

    log("Preparando pasta do detector de voz...")
    silero_dir()

    log("Preparando pasta do reconhecedor de falantes...")
    ecapa_dir()
    log("Arquivos básicos prontos. O restante baixa na primeira escuta, se faltar.")


def _run_with_ssl_retry(log: ProgressCallback, label: str, action: Callable[[], object]) -> None:
    try:
        action()
    except Exception as exc:
        if not is_ssl_error(exc):
            raise
        log(f"Certificado SSL bloqueou {label}; tentando de novo...")
        retry_insecure_tls()
        action()


def _download_nllb(log: ProgressCallback) -> None:
    if snapshot_download is None or AutoTokenizer is None:
        raise RuntimeError("huggingface-hub ou transformers não está instalado.")
    target = nllb_dir()
    if nllb_is_ready(target):
        log("NLLB já está no disco.")
    else:
        _run_with_ssl_retry(
            log,
            "NLLB",
            lambda: snapshot_download(repo_id=NLLB_CT2_REPO, local_dir=str(target)),
        )
        log("NLLB baixado.")

    tokenizer_dir = target / "tokenizer"
    tokenizer_dir.mkdir(parents=True, exist_ok=True)
    _run_with_ssl_retry(
        log,
        "tokenizer NLLB",
        lambda: AutoTokenizer.from_pretrained(NLLB_TOKENIZER_REPO, cache_dir=str(tokenizer_dir)),
    )
    log("Tokenizer NLLB pronto.")


def warmup_optional_models(log: ProgressCallback | None = None) -> None:
    callback = log or (lambda _message: None)
    try:
        if load_silero_vad is None:
            raise RuntimeError("silero-vad não instalado")
        callback("Carregando Silero VAD...")
        _run_with_ssl_retry(callback, "Silero VAD", load_silero_vad)
        callback("Silero VAD pronto.")
    except Exception as exc:
        callback(f"Silero VAD opcional falhou ({exc}). Usando VAD por energia.")

    try:
        if EncoderClassifier is None:
            raise RuntimeError("speechbrain não instalado")
        callback("Baixando embeddings de falante (ECAPA)...")
        kwargs = {
            "source": "speechbrain/spkrec-ecapa-voxceleb",
            "savedir": str(ecapa_dir()),
            "run_opts": {"device": "cpu"},
        }
        if LocalStrategy is not None:
            kwargs["local_strategy"] = LocalStrategy.COPY
        _run_with_ssl_retry(
            callback,
            "ECAPA",
            lambda: EncoderClassifier.from_hparams(**kwargs),
        )
        callback("ECAPA pronto.")
    except Exception as exc:
        callback(f"ECAPA opcional falhou ({exc}). Cada fonte vira uma pessoa.")


def prefetch_whisper(quality: str, log: ProgressCallback | None = None) -> None:
    callback = log or (lambda _message: None)
    try:
        if WhisperModel is None:
            raise RuntimeError("faster-whisper não instalado")
        device = detect_device()
        callback(f"Baixando Whisper {quality} ({device.reason})...")
        _run_with_ssl_retry(
            callback,
            f"Whisper {quality}",
            lambda: WhisperModel(
                quality,
                device=device.device,
                compute_type=device.compute_type,
                download_root=str(whisper_dir()),
            ),
        )
        callback(f"Whisper {quality} pronto.")
    except Exception as exc:
        callback(f"Whisper será baixado na primeira escuta ({exc}).")
