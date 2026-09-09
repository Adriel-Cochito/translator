from __future__ import annotations

from translator.audio.devices import list_mic_devices, list_system_devices, resolve_mic_index, resolve_system_index


def test_device_lists_include_defaults() -> None:
    mics = list_mic_devices()
    systems = list_system_devices()
    assert mics[0].id == "mic:default"
    assert systems[0].id == "sys:default"
    assert mics[0].kind == "mic"
    assert systems[0].kind == "system"


def test_resolve_device_ids() -> None:
    default_index = resolve_mic_index("mic:default")
    assert default_index is None or default_index >= 0
    assert resolve_mic_index("mic:4") == 4
    assert resolve_system_index("sys:default") is None
    assert resolve_system_index("sys:9") == 9
