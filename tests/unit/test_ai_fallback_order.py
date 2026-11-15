"""Enforces the documented advisor fallback order for backend=nim:

    NIM -> Anthropic (if configured) -> Ollama -> deterministic

Each step is exercised by marking the earlier backends not ready.
"""
from core.ai.model_router import ModelRouter


class _Stub:
    def __init__(self, ready: bool):
        self.ready = ready


def _router(nim_ready, anthropic_ready, ollama_ready):
    router = ModelRouter(
        client=_Stub(anthropic_ready),
        config={"advisor": {"backend": "nim"}},
        env={},
        ollama_client=_Stub(ollama_ready),
    )
    # Replace the NIM client built from config with a controlled stub.
    router.nim = _Stub(nim_ready)
    router._active = router._select_active()
    return router


def test_nim_is_selected_when_ready():
    r = _router(nim_ready=True, anthropic_ready=True, ollama_ready=True)
    assert r.active() is r.nim


def test_falls_back_to_anthropic_when_nim_unavailable():
    r = _router(nim_ready=False, anthropic_ready=True, ollama_ready=True)
    assert r.active() is r.client


def test_falls_back_to_ollama_when_nim_and_anthropic_unavailable():
    r = _router(nim_ready=False, anthropic_ready=False, ollama_ready=True)
    assert r.active() is r.ollama


def test_falls_back_to_deterministic_when_all_unavailable():
    r = _router(nim_ready=False, anthropic_ready=False, ollama_ready=False)
    assert r.active() is r.local
