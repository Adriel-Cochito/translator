from __future__ import annotations

from translator.cuda_paths import register_cuda_dlls


def test_register_cuda_dlls_is_safe() -> None:
    first = register_cuda_dlls()
    second = register_cuda_dlls()
    assert isinstance(first, list)
    assert second == [] or set(second).issubset(set(first))
