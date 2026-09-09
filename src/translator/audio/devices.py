from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

try:
    import sounddevice as sd
except ImportError:  # pragma: no cover
    sd = None  # type: ignore[assignment]

try:
    import pyaudiowpatch as pyaudio
except ImportError:  # pragma: no cover
    pyaudio = None  # type: ignore[assignment]


@dataclass(frozen=True)
class AudioDevice:
    id: str
    name: str
    kind: Literal["mic", "system"]
    native_id: int | None = None


def list_mic_devices() -> list[AudioDevice]:
    devices = [AudioDevice(id="mic:default", name="Microfone padrão", kind="mic", native_id=None)]
    if sd is None:
        return devices

    try:
        hostapis = sd.query_hostapis()
        raw_devices = sd.query_devices()
    except Exception:
        return devices

    seen: set[str] = set()
    for index, info in enumerate(raw_devices):
        if int(info.get("max_input_channels", 0)) <= 0:
            continue
        host_index = int(info.get("hostapi", 0))
        host_name = ""
        if 0 <= host_index < len(hostapis):
            host_name = str(hostapis[host_index].get("name", ""))
        label = f"{info.get('name', f'Dispositivo {index}')} ({host_name})"
        if label in seen:
            continue
        seen.add(label)
        devices.append(AudioDevice(id=f"mic:{index}", name=label, kind="mic", native_id=index))
    return devices


def list_system_devices() -> list[AudioDevice]:
    devices = [AudioDevice(id="sys:default", name="Saída padrão (loopback)", kind="system", native_id=None)]
    if pyaudio is None:
        return devices

    audio = None
    try:
        audio = pyaudio.PyAudio()
        count = audio.get_device_count()
        seen: set[str] = set()
        for index in range(count):
            try:
                info = audio.get_device_info_by_index(index)
            except Exception:
                continue
            if not info.get("isLoopbackDevice"):
                continue
            name = str(info.get("name", f"Loopback {index}"))
            if name in seen:
                continue
            seen.add(name)
            devices.append(AudioDevice(id=f"sys:{index}", name=name, kind="system", native_id=index))
    except Exception:
        return devices
    finally:
        if audio is not None:
            audio.terminate()
    return devices


def wasapi_hostapi_index() -> int | None:
    if sd is None:
        return None
    try:
        for index, info in enumerate(sd.query_hostapis()):
            if "wasapi" in str(info.get("name", "")).lower():
                return index
    except Exception:
        return None
    return None


def resolve_mic_index(device_id: str | None) -> int | None:
    if device_id and device_id != "mic:default" and device_id.startswith("mic:"):
        suffix = device_id.split(":", 1)[1]
        if suffix.isdigit():
            return int(suffix)
    host = wasapi_hostapi_index()
    if host is None or sd is None:
        return None
    try:
        default_in = sd.query_hostapis()[host].get("default_input_device")
        if default_in is not None and int(default_in) >= 0:
            return int(default_in)
    except Exception:
        return None
    return None


def wasapi_input_settings():
    if sd is None:
        return None
    try:
        return sd.WasapiSettings(exclusive=False)
    except Exception:
        return None


def resolve_system_index(device_id: str | None) -> int | None:
    if not device_id or device_id == "sys:default":
        return None
    if device_id.startswith("sys:"):
        suffix = device_id.split(":", 1)[1]
        if suffix.isdigit():
            return int(suffix)
    return None
