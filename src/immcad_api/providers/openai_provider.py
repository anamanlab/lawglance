from __future__ import annotations

import time

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI, RateLimitError

from immcad_api.providers.base import ProviderError, ProviderResult
from immcad_api.providers.error_mapping import map_provider_exception
from immcad_api.providers.prompt_builder import build_runtime_prompts
from immcad_api.schemas import Citation


class OpenAIProvider:
    name = "openai"
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

    def generate(self, *, message: str, citations: list[Citation], locale: str) -> ProviderResult:
        if not self.api_key:
            raise ProviderError(self.name, "provider_error", "OPENAI_API_KEY not configured")

        client = OpenAI(api_key=self.api_key, timeout=self.timeout_seconds)
        system_prompt, prompt = build_runtime_prompts(
            message=message,
            citations=citations,
            locale=locale,
        )

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
                    marker in lowered for marker in self._NON_TRANSIENT_PROVIDER_ERROR_MESSAGES
                )
                if is_non_transient:
                    raise
                last_error = exc
            except RateLimitError as exc:
                last_error = ProviderError(self.name, "rate_limit", str(exc))
            except APITimeoutError as exc:
                last_error = ProviderError(self.name, "timeout", str(exc))
            except (APIConnectionError, APIStatusError) as exc:
                last_error = map_provider_exception(self.name, exc)
            except Exception as exc:  # pragma: no cover
                last_error = map_provider_exception(self.name, exc)

            if attempt < self.max_retries:
                time.sleep(0.4 * (attempt + 1))
                continue
            if last_error:
                raise last_error

        if not answer:
            raise ProviderError(self.name, "provider_error", "Empty OpenAI response")

        return ProviderResult(
            provider=self.name,
            answer=answer,
            citations=citations,
            confidence="medium",
        )
