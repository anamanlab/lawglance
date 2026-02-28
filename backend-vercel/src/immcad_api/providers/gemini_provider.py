from __future__ import annotations

import importlib
import json
import time

import httpx

from immcad_api.providers.base import ProviderError, ProviderResult
from immcad_api.providers.error_mapping import map_provider_exception
from immcad_api.providers.prompt_builder import build_combined_runtime_prompt
from immcad_api.schemas import Citation


class GeminiProvider:
    name = "gemini"
    _GEMINI_API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def __init__(
        self,
        api_key: str | None,
        *,
        model: str,
        fallback_models: tuple[str, ...] = (),
        timeout_seconds: float,
        max_retries: int,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.fallback_models = fallback_models
        self.timeout_seconds = timeout_seconds
        self.max_retries = max(0, max_retries)

    def generate(
        self, *, message: str, citations: list[Citation], locale: str
    ) -> ProviderResult:
        if not self.api_key:
            raise ProviderError(
                self.name, "provider_error", "GEMINI_API_KEY not configured"
            )

        # google-genai SDK is optional; Cloudflare native runtime uses HTTP fallback.
        genai_module, genai_types = self._load_google_genai_sdk()

        prompt = build_combined_runtime_prompt(
            message=message,
            locale=locale,
            citations=citations,
        )

        if genai_module is not None and genai_types is not None:
            answer = self._generate_with_sdk(
                prompt=prompt,
                genai=genai_module,
                types=genai_types,
            )
        else:
            answer = self._generate_with_httpx(prompt=prompt)

        if not answer:
            raise ProviderError(self.name, "provider_error", "Empty Gemini response")

        return ProviderResult(
            provider=self.name,
            answer=answer,
            # The provider currently returns plain text only; do not imply model-emitted citations.
            citations=[],
            confidence="medium",
        )

    @staticmethod
    def _load_google_genai_sdk():
        try:
            genai = importlib.import_module("google.genai")
            types = getattr(genai, "types", None)
            if types is None:
                return None, None
            return genai, types
        except Exception:  # pragma: no cover
            return None, None

    def _generate_with_sdk(self, *, prompt: str, genai, types) -> str:  # noqa: ANN001
        # google-genai HttpOptions.timeout is interpreted in milliseconds.
        timeout_millis = max(1000, int(self.timeout_seconds * 1000))
        client = genai.Client(
            api_key=self.api_key,
            http_options=types.HttpOptions(timeout=timeout_millis),
        )

        answer = ""
        last_error: ProviderError | None = None
        models_to_try = [self.model, *self.fallback_models]
        for model_name in models_to_try:
            for attempt in range(self.max_retries + 1):
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.2,
                        ),
                    )
                    answer = response.text or ""
                    if answer:
                        break
                    last_error = ProviderError(
                        self.name,
                        "provider_error",
                        f"Empty Gemini response from model '{model_name}'",
                    )
                except Exception as exc:  # pragma: no cover
                    last_error = map_provider_exception(self.name, exc)

                if attempt < self.max_retries:
                    time.sleep(0.4 * (attempt + 1))
                    continue
            if answer:
                break

        if not answer:
            if last_error:
                raise ProviderError(
                    self.name,
                    last_error.code,
                    f"{last_error.message} (models tried: {', '.join(models_to_try)})",
                ) from last_error
            raise ProviderError(self.name, "provider_error", "Empty Gemini response")
        return answer

    def _generate_with_httpx(self, *, prompt: str) -> str:
        timeout_millis = max(1000, int(self.timeout_seconds * 1000))
        models_to_try = [self.model, *self.fallback_models]
        answer = ""
        last_error: ProviderError | None = None
        for model_name in models_to_try:
            endpoint = self._GEMINI_API_ENDPOINT.format(model=model_name)
            params = {"key": self.api_key}
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2},
            }
            for attempt in range(self.max_retries + 1):
                try:
                    with httpx.Client(timeout=timeout_millis / 1000.0) as client:
                        response = client.post(
                            endpoint,
                            params=params,
                            headers={"content-type": "application/json"},
                            content=json.dumps(payload),
                        )
                    if response.status_code == 429:
                        raise ProviderError(self.name, "rate_limit", response.text)
                    if response.status_code >= 400:
                        raise ProviderError(
                            self.name,
                            "provider_error",
                            f"Gemini API returned HTTP {response.status_code}: {response.text}",
                        )
                    data = response.json()
                    candidates = data.get("candidates")
                    if isinstance(candidates, list) and candidates:
                        first_candidate = candidates[0]
                        content = (
                            first_candidate.get("content")
                            if isinstance(first_candidate, dict)
                            else None
                        )
                        parts = (
                            content.get("parts") if isinstance(content, dict) else None
                        )
                        if isinstance(parts, list):
                            answer = "".join(
                                str(part.get("text", ""))
                                for part in parts
                                if isinstance(part, dict)
                            ).strip()
                    if not answer:
                        raise ProviderError(
                            self.name,
                            "provider_error",
                            f"Empty Gemini response from model '{model_name}'",
                        )
                    break
                except httpx.TimeoutException as exc:
                    last_error = ProviderError(self.name, "timeout", str(exc))
                except httpx.HTTPError as exc:
                    last_error = map_provider_exception(self.name, exc)
                except Exception as exc:  # pragma: no cover
                    last_error = map_provider_exception(self.name, exc)

                if attempt < self.max_retries:
                    time.sleep(0.4 * (attempt + 1))
                    continue
            if answer:
                break

        if not answer:
            if last_error:
                raise ProviderError(
                    self.name,
                    last_error.code,
                    f"{last_error.message} (models tried: {', '.join(models_to_try)})",
                ) from last_error
            raise ProviderError(self.name, "provider_error", "Empty Gemini response")
        return answer
