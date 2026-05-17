import asyncio

import httpx

from saturnix_harness.brains.ollama_provider import (
    OLLAMA_GENERATE_PATH,
    OLLAMA_TAGS_PATH,
    SaturnixOllamaProvider,
)
from saturnix_harness.config import Settings


def test_ollama_resolves_supported_model_aliases(tmp_path):
    provider = _provider(tmp_path)

    assert provider.resolve_model("gemma") == "gemma3"
    assert provider.resolve_model("minimax") == "minimax"
    assert provider.resolve_model("qwen coder") == "qwen2.5-coder"
    assert provider.resolve_model("deepseek coder") == "deepseek-coder-v2"


def test_ollama_health_check_reports_not_running(tmp_path, monkeypatch):
    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return None

        async def get(self, url):
            raise httpx.ConnectError("connection refused")

    monkeypatch.setattr("saturnix_harness.brains.ollama_provider.httpx.AsyncClient", FakeClient)

    health = asyncio.run(_provider(tmp_path).health_check())

    assert health.enabled is True
    assert health.running is False
    assert health.base_url == "http://localhost:11434"
    assert "not reachable" in health.detail


def test_ollama_health_check_lists_missing_supported_models(tmp_path, monkeypatch):
    captured = {}

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"models": [{"name": "gemma3:latest"}, {"name": "deepseek-coder-v2:latest"}]}

    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return None

        async def get(self, url):
            captured["url"] = url
            return FakeResponse()

    monkeypatch.setattr("saturnix_harness.brains.ollama_provider.httpx.AsyncClient", FakeClient)

    health = asyncio.run(_provider(tmp_path).health_check())

    assert captured["url"] == "http://localhost:11434" + OLLAMA_TAGS_PATH
    assert health.running is True
    assert health.available_models == ["gemma3:latest", "deepseek-coder-v2:latest"]
    assert "qwen coder" in health.missing_supported_models


def test_ollama_generate_uses_generate_endpoint(tmp_path, monkeypatch):
    captured = {}

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"response": "local answer", "done": True}

    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return None

        async def post(self, url, json):
            captured["url"] = url
            captured["json"] = json
            return FakeResponse()

    monkeypatch.setattr("saturnix_harness.brains.ollama_provider.httpx.AsyncClient", FakeClient)

    result = asyncio.run(
        _provider(tmp_path).generate(
            "Explain SATURNIX",
            model="gemma",
            system="Be concise.",
            max_tokens=128,
        )
    )

    assert captured["url"] == "http://localhost:11434" + OLLAMA_GENERATE_PATH
    assert captured["json"]["model"] == "gemma3"
    assert captured["json"]["system"] == "Be concise."
    assert captured["json"]["options"]["num_predict"] == 128
    assert result.ok is True
    assert result.output == "local answer"


def test_ollama_generate_returns_fallback_when_unavailable(tmp_path, monkeypatch):
    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return None

        async def post(self, url, json):
            raise httpx.ConnectError("connection refused")

    monkeypatch.setattr("saturnix_harness.brains.ollama_provider.httpx.AsyncClient", FakeClient)

    result = asyncio.run(
        _provider(tmp_path).generate(
            "Summarize locally",
            model="gemma",
            fallback_text="Ollama unavailable; use routed cloud fallback.",
        )
    )

    assert result.ok is False
    assert result.fallback_used is True
    assert result.output == "Ollama unavailable; use routed cloud fallback."
    assert "not reachable" in result.error


def test_ollama_code_generate_and_summarize_choose_local_models(tmp_path, monkeypatch):
    calls = []

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"response": "generated", "done": True}

    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return None

        async def post(self, url, json):
            calls.append(json)
            return FakeResponse()

    monkeypatch.setattr("saturnix_harness.brains.ollama_provider.httpx.AsyncClient", FakeClient)
    provider = _provider(tmp_path)

    code = asyncio.run(provider.code_generate("Write parser", model="qwen coder", language="Python"))
    summary = asyncio.run(provider.summarize("A long note about SATURNIX memory."))

    assert code.ok is True
    assert calls[0]["model"] == "qwen2.5-coder"
    assert "Target language: Python." in calls[0]["prompt"]
    assert summary.ok is True
    assert calls[1]["model"] == "gemma3"


def test_ollama_classify_task_selects_coding_model(tmp_path):
    classification = _provider(tmp_path).classify_task(
        "Fast private code generation for a Python API helper"
    )

    assert classification.task_type == "coding"
    assert classification.privacy_level == "local"
    assert classification.speed_priority == "high"
    assert classification.output_format == "code"
    assert classification.local_model == "deepseek-coder-v2"


def _provider(tmp_path):
    settings = Settings(
        saturnix_env="test",
        saturnix_sqlite_path=tmp_path / "memory.sqlite3",
        saturnix_enable_chroma=False,
        saturnix_enable_ollama=True,
        ollama_base_url="http://localhost:11434",
        ollama_gemma_model="gemma3",
        ollama_minimax_model="minimax",
        ollama_qwen_coder_model="qwen2.5-coder",
        ollama_deepseek_coder_model="deepseek-coder-v2",
        ollama_coding_model="deepseek-coder-v2",
    )
    return SaturnixOllamaProvider(settings)

