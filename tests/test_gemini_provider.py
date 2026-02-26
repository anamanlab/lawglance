from __future__ import annotations

from types import ModuleType, SimpleNamespace
import sys

from immcad_api.providers.gemini_provider import GeminiProvider
from immcad_api.providers.prompt_builder import build_combined_runtime_prompt


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeModels:
    def __init__(self, answer_text: str, captured: dict[str, object]) -> None:
        self.answer_text = answer_text
        self.captured = captured

    def generate_content(self, *, model: str, contents: str, config) -> _FakeResponse:  # noqa: ANN001
        self.captured["model"] = model
        self.captured["contents"] = contents
        self.captured["temperature"] = getattr(config, "temperature", None)
        return _FakeResponse(self.answer_text)


def _install_fake_google_sdk(monkeypatch, captured: dict[str, object], answer_text: str = "OK") -> None:  # noqa: ANN001
    class _FakeHttpOptions:
        def __init__(self, *, timeout: int) -> None:
            captured["timeout"] = timeout
            self.timeout = timeout

    class _FakeGenerateContentConfig:
        def __init__(self, *, temperature: float) -> None:
            self.temperature = temperature

    class _FakeClient:
        def __init__(self, *, api_key: str, http_options: _FakeHttpOptions) -> None:
            captured["api_key"] = api_key
            captured["http_options_timeout"] = http_options.timeout
            self.models = _FakeModels(answer_text, captured)

    google_module = ModuleType("google")
    genai_module = ModuleType("google.genai")
    genai_module.Client = _FakeClient
    genai_module.types = SimpleNamespace(
        HttpOptions=_FakeHttpOptions,
        GenerateContentConfig=_FakeGenerateContentConfig,
    )
    google_module.genai = genai_module

    monkeypatch.setitem(sys.modules, "google", google_module)
    monkeypatch.setitem(sys.modules, "google.genai", genai_module)


def test_gemini_provider_uses_millisecond_timeout(monkeypatch) -> None:  # noqa: ANN001
    captured: dict[str, object] = {}
    _install_fake_google_sdk(monkeypatch, captured)
    provider = GeminiProvider(
        "gemini-key",
        model="gemini-3-flash-preview",
        fallback_models=("gemini-2.5-flash",),
        timeout_seconds=15.0,
        max_retries=0,
    )

    response = provider.generate(message="hello", citations=[], locale="en-CA")

    assert captured["timeout"] == 15_000
    assert response.answer == "OK"
    assert response.provider == "gemini"
    assert response.citations == []


def test_gemini_provider_clamps_timeout_to_one_second(monkeypatch) -> None:  # noqa: ANN001
    captured: dict[str, object] = {}
    _install_fake_google_sdk(monkeypatch, captured)
    provider = GeminiProvider(
        "gemini-key",
        model="gemini-3-flash-preview",
        timeout_seconds=0.2,
        max_retries=0,
    )

    provider.generate(message="hello", citations=[], locale="en-CA")

    assert captured["timeout"] == 1_000


def test_gemini_provider_prompt_includes_scope_and_grounding(monkeypatch) -> None:  # noqa: ANN001
    captured: dict[str, object] = {}
    _install_fake_google_sdk(monkeypatch, captured)
    provider = GeminiProvider(
        "gemini-key",
        model="gemini-2.5-flash-lite",
        timeout_seconds=15.0,
        max_retries=0,
    )

    provider.generate(
        message="How does Express Entry work?",
        citations=[],
        locale="en-CA",
    )

    prompt = str(captured["contents"])
    expected_prompt = build_combined_runtime_prompt(
        message="How does Express Entry work?",
        citations=[],
        locale="en-CA",
    )
    assert prompt == expected_prompt
    assert "Do not claim model/vendor identity" in prompt
    assert "No grounded citations were provided." in prompt
    assert captured["temperature"] == 0.2
