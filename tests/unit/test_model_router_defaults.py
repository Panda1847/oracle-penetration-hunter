from core.ai.model_router import ModelRouter

def test_nim_is_default_backend_and_deterministic_fallback():
    router = ModelRouter(config={"advisor": {}, "nim": {"enabled": True}, "ollama": {"enabled": False}}, env={})
    assert router.backend == "nim"
    assert router.active() is router.fallback()
