from __future__ import annotations

from types import SimpleNamespace

from immcad_api.providers.openai_provider import OpenAIProvider
from immcad_api.providers.prompt_builder import build_runtime_prompts
from immcad_api.schemas import Citation


class _FakeCompletions:
    def __init__(self, captured: dict[str, object], answer_text: str) -> None:
        self.captured = captured
        self.answer_text = answer_text

    def create(self, *, model: str, temperature: float, messages):  # noqa: ANN001
        self.captured["model"] = model
        self.captured["temperature"] = temperature
        self.captured["messages"] = messages
        choice = SimpleNamespace(message=SimpleNamespace(content=self.answer_text))
        return SimpleNamespace(choices=[choice])


class _FakeChat:
    def __init__(self, captured: dict[str, object], answer_text: str) -> None:
        self.completions = _FakeCompletions(captured, answer_text)


class _FakeOpenAIClient:
    def __init__(
        self,
        *,
        api_key: str,
        timeout: float,
        captured: dict[str, object],
        answer_text: str,
    ) -> None:
        captured["api_key"] = api_key
        captured["timeout"] = timeout
        self.chat = _FakeChat(captured, answer_text)


def test_openai_provider_prompt_includes_scope_and_grounding(monkeypatch) -> None:  # noqa: ANN001
    captured: dict[str, object] = {}

    def _fake_client(*, api_key: str, timeout: float):  # noqa: ANN001
        return _FakeOpenAIClient(
            api_key=api_key,
            timeout=timeout,
            captured=captured,
            answer_text="Informational answer",
        )

    monkeypatch.setattr("immcad_api.providers.openai_provider.OpenAI", _fake_client)

    provider = OpenAIProvider(
        "openai-key",
        model="gpt-4o-mini",
        timeout_seconds=12.0,
        max_retries=0,
    )
    citations = [
        Citation(
            source_id="IRPA",
            title="Immigration and Refugee Protection Act",
            url="https://laws-lois.justice.gc.ca/eng/acts/i-2.5/",
            pin="s. 11",
            snippet="A foreign national must apply before entering Canada.",
        )
    ]

    response = provider.generate(
        message="How does Express Entry work?",
        citations=citations,
        locale="en-CA",
    )

    assert response.answer == "Informational answer"
    assert response.provider == "openai"
    assert response.citations == citations
    assert captured["api_key"] == "openai-key"
    assert captured["timeout"] == 12.0
    assert captured["temperature"] == 0.2

    messages = captured["messages"]
    assert isinstance(messages, list)
    assert len(messages) == 2
    system_message = messages[0]["content"]
    user_message = messages[1]["content"]
    expected_system_prompt, expected_user_prompt = build_runtime_prompts(
        message="How does Express Entry work?",
        citations=citations,
        locale="en-CA",
    )
    assert system_message == expected_system_prompt
    assert user_message == expected_user_prompt
    assert "Do not claim model/vendor identity" in system_message
    assert "Immigration and Refugee Protection Act" in user_message
