from __future__ import annotations

from translator.config import AsrQuality, load_settings
from translator.pipeline.setup_models import download_models, prefetch_whisper, warmup_optional_models


def main() -> None:
    settings = load_settings()
    quality = settings.asr_quality if isinstance(settings.asr_quality, AsrQuality) else AsrQuality.SMALL

    def log(message: str) -> None:
        print(message, flush=True)

    download_models(log)
    warmup_optional_models(log)
    prefetch_whisper(str(quality), log)


if __name__ == "__main__":
    main()
