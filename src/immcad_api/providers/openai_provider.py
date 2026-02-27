from __future__ import annotations

import importlib
import json
import time

import httpx

from immcad_api.providers.base import ProviderError, ProviderResult
from immcad_api.providers.error_mapping import map_provider_exception
from immcad_api.providers.prompt_builder import build_runtime_prompts
from immcad_api.schemas import Citation

OpenAI = None


class OpenAIProvider:
    name = "openai"
    _OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"
    _NON_TRANSIENT_PROVIDER_ERROR_MESSAGES = (
        "no choices",
        "no message content",
    )

    def __init__(
        self,
        api_key: str | None,
        *,
        model: str,
        timeout_seconds: float,
        max_retries: int,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max(0, max_retries)

    def generate(
        self, *, message: str, citations: list[Citation], locale: str
    ) -> ProviderResult:
        if not self.api_key:
            raise ProviderError(
                self.name, "provider_error", "OPENAI_API_KEY not configured"
            )

        system_prompt, prompt = build_runtime_prompts(
            message=message,
            citations=citations,
            locale=locale,
        )

        sdk_client_ctor = self._resolve_openai_client_constructor()
        if sdk_client_ctor is not None:
            answer = self._generate_with_sdk(
                sdk_client_ctor=sdk_client_ctor,
                system_prompt=system_prompt,
                prompt=prompt,
            )
        else:
            answer = self._generate_with_httpx(
                system_prompt=system_prompt,
                prompt=prompt,
            )

        if not answer:
            raise ProviderError(self.name, "provider_error", "Empty OpenAI response")

        return ProviderResult(
            provider=self.name,
            answer=answer,
            # The provider currently returns plain text only; do not imply model-emitted citations.
            citations=[],
            confidence="medium",
        )

    @staticmethod
    def _resolve_openai_client_constructor():
        if OpenAI is not None:  # pragma: no cover - test monkeypatch path.
            return OpenAI
        try:
            openai_module = importlib.import_module("openai")
            client_ctor = getattr(openai_module, "OpenAI", None)
            return client_ctor if callable(client_ctor) else None
        except Exception:
            return None

    def _generate_with_sdk(
        self, *, sdk_client_ctor, system_prompt: str, prompt: str
    ) -> str:  # noqa: ANN001
        client = sdk_client_ctor(api_key=self.api_key, timeout=self.timeout_seconds)
        answer = ""
        last_error: ProviderError | None = None
        for attempt in range(self.max_retries + 1):
            try:
                completion = client.chat.completions.create(
                    model=self.model,
                    temperature=0.2,
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt,
                        },
                        {"role": "user", "content": prompt},
                    ],
                )
                if not completion.choices:
                    raise ProviderError(
                        self.name,
                        "provider_error",
                        "OpenAI response contained no choices",
                    )
                first_choice = completion.choices[0]
                message_obj = getattr(first_choice, "message", None)
                content = getattr(message_obj, "content", None) if message_obj else None
                if content is None:
                    raise ProviderError(
                        self.name,
                        "provider_error",
                        "OpenAI response contained no message content",
                    )
                answer = content
                break
            except ProviderError as exc:
                lowered = exc.message.lower()
                is_non_transient = exc.code == "provider_error" and any(
                    marker in lowered
                    for marker in self._NON_TRANSIENT_PROVIDER_ERROR_MESSAGES
                )
                if is_non_transient:
                    raise
                last_error = exc
            except Exception as exc:  # pragma: no cover
                last_error = map_provider_exception(self.name, exc)

            if attempt < self.max_retries:
                time.sleep(0.4 * (attempt + 1))
                continue
            if last_error:
                raise last_error

        if not answer:
            raise ProviderError(self.name, "provider_error", "Empty OpenAI response")
        return answer

    def _generate_with_httpx(self, *, system_prompt: str, prompt: str) -> str:
        headers = {
            "authorization": f"Bearer {self.api_key}",
            "content-type": "application/json",
        }
        payload = {
            "model": self.model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
        }

        answer = ""
        last_error: ProviderError | None = None
        for attempt in range(self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    response = client.post(
                        self._OPENAI_CHAT_COMPLETIONS_URL,
                        headers=headers,
                        content=json.dumps(payload),
                    )
                if response.status_code == 429:
                    raise ProviderError(self.name, "rate_limit", response.text)
                if response.status_code >= 400:
                    raise ProviderError(
                        self.name,
                        "provider_error",
                        f"OpenAI API returned HTTP {response.status_code}: {response.text}",
                    )
                data = response.json()
                choices = data.get("choices")
                if not isinstance(choices, list) or not choices:
                    raise ProviderError(
                        self.name,
                        "provider_error",
                        "OpenAI response contained no choices",
                    )
                first_choice = choices[0]
                message_payload = (
                    first_choice.get("message")
                    if isinstance(first_choice, dict)
                    else None
                )
                content = (
                    message_payload.get("content")
                    if isinstance(message_payload, dict)
                    else None
                )
                if isinstance(content, str):
                    answer = content
                elif isinstance(content, list):
                    # The responses API may emit structured text segments.
                    answer = "".join(
                        str(item.get("text", ""))
                        for item in content
                        if isinstance(item, dict)
                    ).strip()
                else:
                    answer = ""
                if not answer:
                    raise ProviderError(
                        self.name,
                        "provider_error",
                        "OpenAI response contained no message content",
                    )
                break
            except httpx.TimeoutException as exc:
                last_error = ProviderError(self.name, "timeout", str(exc))
            except httpx.HTTPError as exc:
                last_error = map_provider_exception(self.name, exc)
            except ProviderError as exc:
                lowered = exc.message.lower()
                is_non_transient = exc.code == "provider_error" and any(
                    marker in lowered
                    for marker in self._NON_TRANSIENT_PROVIDER_ERROR_MESSAGES
                )
                if is_non_transient:
                    raise
                last_error = exc
            except Exception as exc:  # pragma: no cover
                last_error = map_provider_exception(self.name, exc)

            if attempt < self.max_retries:
                time.sleep(0.4 * (attempt + 1))
                continue
            if last_error:
                raise last_error

        if not answer:
            raise ProviderError(self.name, "provider_error", "Empty OpenAI response")
        return answer
