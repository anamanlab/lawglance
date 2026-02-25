from __future__ import annotations

from typing import Any

import httpx
import pytest

from immcad_api.errors import SourceUnavailableError
from immcad_api.schemas import CaseSearchRequest
from immcad_api.sources.official_case_law_client import OfficialCaseLawClient
from immcad_api.sources.source_registry import SourceRegistry


def _registry() -> SourceRegistry:
    return SourceRegistry.model_validate(
        {
            "version": "2026-02-25",
            "jurisdiction": "ca",
            "sources": [
                {
                    "source_id": "SCC_DECISIONS",
                    "source_type": "case_law",
                    "instrument": "SCC feed",
                    "url": "https://decisions.scc-csc.ca/scc-csc/scc-csc/en/json/rss.do",
                    "update_cadence": "scheduled_incremental",
                },
                {
                    "source_id": "FC_DECISIONS",
                    "source_type": "case_law",
                    "instrument": "FC feed",
                    "url": "https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/rss.do",
                    "update_cadence": "scheduled_incremental",
                },
                {
                    "source_id": "FCA_DECISIONS",
                    "source_type": "case_law",
                    "instrument": "FCA feed",
                    "url": "https://decisions.fca-caf.gc.ca/fca-caf/en/nav.do?iframe=true",
                    "update_cadence": "scheduled_incremental",
                },
            ],
        }
    )


class _FakeResponse:
    def __init__(self, payload: bytes, status_ok: bool = True) -> None:
        self._payload = payload
        self._status_ok = status_ok

    @property
    def content(self) -> bytes:
        return self._payload

    def raise_for_status(self) -> None:
        if not self._status_ok:
            raise httpx.HTTPStatusError(
                "error",
                request=httpx.Request("GET", "https://example.test"),
                response=httpx.Response(500),
            )


class _FakeClient:
    def __init__(self, responses: dict[str, bytes]) -> None:
        self.responses = responses

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get(self, url: str, *args: Any, **kwargs: Any) -> _FakeResponse:
        del args, kwargs
        payload = self.responses.get(url)
        if payload is None:
            raise httpx.ConnectError(f"No mock payload for {url}")
        return _FakeResponse(payload)


def test_official_case_law_client_returns_ranked_fc_results(monkeypatch: pytest.MonkeyPatch) -> None:
    fc_feed = b"""<?xml version='1.0' encoding='utf-8'?>
<rss version='2.0'>
  <channel>
    <item>
      <title>Example v Canada (Citizenship and Immigration)</title>
      <link>https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/item/123456/index.do</link>
      <description>Neutral citation 2026 FC 101</description>
      <pubDate>Mon, 01 Jan 2026 00:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""
    responses = {
        "https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/rss.do": fc_feed,
    }

    monkeypatch.setattr(
        "immcad_api.sources.official_case_law_client.httpx.Client",
        lambda *args, **kwargs: _FakeClient(responses),
    )

    client = OfficialCaseLawClient(source_registry=_registry())
    request = CaseSearchRequest(
        query="citizenship immigration",
        jurisdiction="ca",
        court="fc",
        limit=5,
    )
    response = client.search_cases(request)

    assert len(response.results) == 1
    assert response.results[0].citation == "2026 FC 101"
    assert response.results[0].case_id == "123456"


def test_official_case_law_client_raises_when_all_sources_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _BrokenClient:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, *args: Any, **kwargs: Any):
            del args, kwargs
            raise httpx.ConnectError("network unavailable")

    monkeypatch.setattr(
        "immcad_api.sources.official_case_law_client.httpx.Client",
        lambda *args, **kwargs: _BrokenClient(),
    )

    client = OfficialCaseLawClient(source_registry=_registry())
    request = CaseSearchRequest(
        query="express entry",
        jurisdiction="ca",
        court=None,
        limit=3,
    )

    with pytest.raises(SourceUnavailableError, match="Official court case-law sources"):
        client.search_cases(request)
