from __future__ import annotations

from translator.asr.gpu import (
    DeviceChoice,
    is_high_vram,
    nllb_runtime,
    pick_cuda_compute_type,
)
from translator.ssl_certs import is_ssl_error


def test_high_vram_prefers_float16() -> None:
    supported = {"int8", "int8_float16", "float16"}
    assert pick_cuda_compute_type(supported, 8192) == "float16"
    assert pick_cuda_compute_type(supported, None) == "float16"


def test_low_vram_prefers_int8() -> None:
    supported = {"int8", "int8_float16", "float16"}
    assert pick_cuda_compute_type(supported, 4096) == "int8"


def test_nllb_stays_on_cpu_when_vram_is_tight() -> None:
    cuda = DeviceChoice("cuda", "float16", "CUDA")
    assert nllb_runtime(cuda, 4096) == ("cpu", "int8")
    assert nllb_runtime(cuda, 8192) == ("cuda", "float16")
    assert nllb_runtime(DeviceChoice("cpu", "int8", "CPU"), 8192) == ("cpu", "int8")


def test_high_vram_threshold() -> None:
    assert is_high_vram(8192) is True
    assert is_high_vram(4096) is False
    assert is_high_vram(None) is True


def test_ssl_error_detection() -> None:
    assert is_ssl_error(Exception("ConnectError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed"))
    assert not is_ssl_error(Exception("model.bin missing"))
