from __future__ import annotations

import os
import ssl
from typing import Any

try:
    import httpx
    from huggingface_hub.utils._http import (
        async_hf_request_event_hook,
        async_hf_response_event_hook,
        close_session,
        hf_request_event_hook,
        set_async_client_factory,
        set_client_factory,
    )
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore[assignment]
    async_hf_request_event_hook = None  # type: ignore[assignment]
    async_hf_response_event_hook = None  # type: ignore[assignment]
    close_session = None  # type: ignore[assignment]
    hf_request_event_hook = None  # type: ignore[assignment]
    set_async_client_factory = None  # type: ignore[assignment]
    set_client_factory = None  # type: ignore[assignment]

try:
    import truststore
except ImportError:  # pragma: no cover
    truststore = None  # type: ignore[assignment]

_configured = False


def configure_tls(*, insecure: bool = False) -> None:
    """Use the Windows certificate store, or skip verify if the AV MITM still fails."""
    global _configured
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    verify: Any
    if insecure:
        ssl._create_default_https_context = ssl._create_unverified_context
        verify = False
    elif truststore is not None:
        truststore.inject_into_ssl()
        verify = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    else:
        ssl._create_default_https_context = ssl._create_unverified_context
        verify = False
    _configure_huggingface_http(verify)
    _configured = True


def ensure_tls() -> None:
    if not _configured:
        configure_tls()


def retry_insecure_tls() -> None:
    configure_tls(insecure=True)


def is_ssl_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    markers = (
        "certificate_verify_failed",
        "sslcertverificationerror",
        "unable to get local issuer certificate",
        "ssl: certificate_verify_failed",
        "[ssl:",
    )
    return any(marker in text for marker in markers)


def _configure_huggingface_http(verify: Any) -> None:
    if (
        httpx is None
        or set_client_factory is None
        or set_async_client_factory is None
        or close_session is None
        or hf_request_event_hook is None
        or async_hf_request_event_hook is None
        or async_hf_response_event_hook is None
    ):
        return

    def factory() -> httpx.Client:
        return httpx.Client(
            event_hooks={"request": [hf_request_event_hook]},
            follow_redirects=True,
            timeout=None,
            verify=verify,
        )

    def async_factory() -> httpx.AsyncClient:
        return httpx.AsyncClient(
            event_hooks={
                "request": [async_hf_request_event_hook],
                "response": [async_hf_response_event_hook],
            },
            follow_redirects=True,
            timeout=None,
            verify=verify,
        )

    set_client_factory(factory)
    set_async_client_factory(async_factory)
    close_session()
