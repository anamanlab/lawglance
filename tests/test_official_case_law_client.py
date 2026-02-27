from __future__ import annotations

from datetime import date
import time
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


def test_official_case_law_client_follows_redirects_for_runtime_fetch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redirecting_url = "https://redirect.example.test/fc-feed"
    fc_feed = b"""<?xml version='1.0' encoding='utf-8'?>
<rss version='2.0'>
  <channel>
    <item>
      <title>Redirected FC decision</title>
      <link>https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/item/100003/index.do</link>
      <description>Neutral citation 2026 FC 303</description>
      <pubDate>Mon, 01 Jan 2026 00:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""

    class _RedirectAwareClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            del args
            self.follow_redirects = bool(kwargs.get("follow_redirects"))

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, url: str, *args: Any, **kwargs: Any) -> _FakeResponse:
            del args
            if url == redirecting_url and (
                self.follow_redirects or kwargs.get("follow_redirects")
            ):
                return _FakeResponse(fc_feed)
            raise httpx.HTTPStatusError(
                "redirect not followed",
                request=httpx.Request("GET", url),
                response=httpx.Response(302),
            )

    registry = SourceRegistry.model_validate(
        {
            "version": "2026-02-25",
            "jurisdiction": "ca",
            "sources": [
                {
                    "source_id": "FC_DECISIONS",
                    "source_type": "case_law",
                    "instrument": "FC feed",
                    "url": redirecting_url,
                    "update_cadence": "scheduled_incremental",
                }
            ],
        }
    )

    monkeypatch.setattr(
        "immcad_api.sources.official_case_law_client.httpx.Client",
        _RedirectAwareClient,
    )

    client = OfficialCaseLawClient(source_registry=registry)
    response = client.search_cases(
        CaseSearchRequest(
            query="redirected decision",
            jurisdiction="ca",
            court="fc",
            limit=5,
        )
    )

    assert response.results
    assert response.results[0].citation == "2026 FC 303"


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
    assert response.results[0].source_id == "FC_DECISIONS"
    assert (
        response.results[0].document_url
        == "https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/123456/1/document.do"
    )


def test_official_case_law_client_prefers_fc_query_search_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fc_search_html = b"""<!DOCTYPE html>
<html lang="en">
  <body>
    <ul>
      <li class="odd list-item-expanded">
        <div class="metadata">
          <h3>
            <span class="title">
              <a target="_parent" href="/fc-cf/decisions/en/item/521478/index.do?q=immigration">
                Balakumar v. Canada (Immigration, Refugees and Citizenship)
              </a>
            </span>
            - <span class="citation">2022 FC 703</span>
            - <span class="publicationDate">2022-05-12</span>
          </h3>
        </div>
      </li>
    </ul>
  </body>
</html>
"""
    fc_feed = b"""<?xml version='1.0' encoding='utf-8'?>
<rss version='2.0'><channel></channel></rss>
"""
    responses = {
        "https://decisions.fct-cf.gc.ca/fc-cf/en/d/s/index.do": fc_search_html,
        "https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/rss.do": fc_feed,
    }
    fetch_count: dict[str, int] = {}

    class _CountingClient(_FakeClient):
        def get(self, url: str, *args: Any, **kwargs: Any) -> _FakeResponse:
            fetch_count[url] = fetch_count.get(url, 0) + 1
            return super().get(url, *args, **kwargs)

    monkeypatch.setattr(
        "immcad_api.sources.official_case_law_client.httpx.Client",
        lambda *args, **kwargs: _CountingClient(responses),
    )

    client = OfficialCaseLawClient(source_registry=_registry())
    response = client.search_cases(
        CaseSearchRequest(
            query="immigration",
            jurisdiction="ca",
            court="fc",
            limit=5,
        )
    )

    assert response.results
    assert response.results[0].citation == "2022 FC 703"
    assert fetch_count["https://decisions.fct-cf.gc.ca/fc-cf/en/d/s/index.do"] == 1
    assert fetch_count.get("https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/rss.do", 0) == 0


def test_official_case_law_client_falls_back_to_fc_feed_when_query_search_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fc_feed = b"""<?xml version='1.0' encoding='utf-8'?>
<rss version='2.0'>
  <channel>
    <item>
      <title>Fallback FC decision</title>
      <link>https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/item/100777/index.do</link>
      <description>Neutral citation 2026 FC 707</description>
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
    response = client.search_cases(
        CaseSearchRequest(
            query="fallback fc decision",
            jurisdiction="ca",
            court="fc",
            limit=5,
        )
    )

    assert response.results
    assert response.results[0].citation == "2026 FC 707"


def test_official_case_law_client_prefers_fca_query_search_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fca_search_html = b"""<!DOCTYPE html>
<html lang="en">
  <body>
    <ul>
      <li class="odd list-item-expanded">
        <div class="metadata">
              <h3>
                <span class="title">
                  <a target="_parent" href="/fca-caf/decisions/en/item/521795/index.do?q=immigration">
                Canadian Society of Immigration Consultants v. Canada (Citizenship and Immigration)
                  </a>
                </span>
            - <span class="citation">2026 FCA 43</span>
            - <span class="publicationDate">2026-02-26</span>
          </h3>
        </div>
      </li>
    </ul>
  </body>
</html>
"""

    class _FcaParamCheckingClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            del args, kwargs

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, url: str, *args: Any, **kwargs: Any) -> _FakeResponse:
            del args
            assert url == "https://decisions.fca-caf.gc.ca/fca-caf/en/d/s/index.do"
            params = kwargs.get("params", {})
            assert isinstance(params, dict)
            assert params.get("cont") == "immigration"
            assert params.get("col") == "53"
            assert params.get("iframe") == "true"
            return _FakeResponse(fca_search_html)

    monkeypatch.setattr(
        "immcad_api.sources.official_case_law_client.httpx.Client",
        _FcaParamCheckingClient,
    )

    client = OfficialCaseLawClient(source_registry=_registry())
    response = client.search_cases(
        CaseSearchRequest(
            query="immigration",
            jurisdiction="ca",
            court="fca",
            limit=5,
        )
    )

    assert response.results
    assert response.results[0].citation == "2026 FCA 43"
    assert response.results[0].source_id == "FCA_DECISIONS"


def test_official_case_law_client_uses_content_param_for_generic_query_search(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fc_search_html = b"""<!DOCTYPE html>
<html lang="en">
  <body>
    <ul>
      <li class="odd list-item-expanded">
        <div class="metadata">
          <h3>
            <span class="title">
              <a target="_parent" href="/fc-cf/decisions/en/item/521478/index.do?q=immigration">
                Balakumar v. Canada (Immigration, Refugees and Citizenship)
              </a>
            </span>
            - <span class="citation">2022 FC 703</span>
            - <span class="publicationDate">2022-05-12</span>
          </h3>
        </div>
      </li>
    </ul>
  </body>
</html>
"""

    class _ParamCheckingClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            del args, kwargs

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, url: str, *args: Any, **kwargs: Any) -> _FakeResponse:
            del args
            assert url == "https://decisions.fct-cf.gc.ca/fc-cf/en/d/s/index.do"
            params = kwargs.get("params", {})
            assert isinstance(params, dict)
            assert params.get("cont") == "immigration judicial review"
            assert "ref" not in params
            return _FakeResponse(fc_search_html)

    monkeypatch.setattr(
        "immcad_api.sources.official_case_law_client.httpx.Client",
        _ParamCheckingClient,
    )

    client = OfficialCaseLawClient(source_registry=_registry())
    response = client.search_cases(
        CaseSearchRequest(
            query="immigration judicial review",
            jurisdiction="ca",
            court="fc",
            limit=5,
        )
    )

    assert response.results
    assert response.results[0].citation == "2022 FC 703"


def test_official_case_law_client_rejects_non_positive_cache_ttl() -> None:
    with pytest.raises(ValueError, match="cache_ttl_seconds must be > 0"):
        OfficialCaseLawClient(
            source_registry=_registry(),
            cache_ttl_seconds=0,
            stale_cache_ttl_seconds=1,
        )


def test_official_case_law_client_rejects_stale_ttl_shorter_than_fresh_ttl() -> None:
    with pytest.raises(
        ValueError,
        match="stale_cache_ttl_seconds must be >= cache_ttl_seconds",
    ):
        OfficialCaseLawClient(
            source_registry=_registry(),
            cache_ttl_seconds=60,
            stale_cache_ttl_seconds=30,
        )


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


def test_official_case_law_client_raises_when_requested_source_not_in_registry() -> None:
    registry = SourceRegistry.model_validate(
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
                }
            ],
        }
    )
    client = OfficialCaseLawClient(source_registry=registry)
    request = CaseSearchRequest(
        query="inadmissibility",
        jurisdiction="ca",
        court="fc",
        limit=3,
    )

    with pytest.raises(SourceUnavailableError, match="Official court case-law sources"):
        client.search_cases(request)


def test_official_case_law_client_prioritizes_immigration_records_without_court_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fc_feed = b"""<?xml version='1.0' encoding='utf-8'?>
<rss version='2.0'>
  <channel>
    <item>
      <title>Cadogan v Canada (Citizenship and Immigration), 2025 FC 1125</title>
      <link>https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/item/654321/index.do</link>
      <description>Immigration judicial review record</description>
      <pubDate>Mon, 23 Jun 2025 00:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""
    scc_feed = b"""{
  "rss": {
    "channel": {
      "item": [
        {
          "title": "Nova Chemicals Corp. v. Dow Chemical Co. - 2022 SCC 43",
          "link": "https://decisions.scc-csc.ca/scc-csc/scc-csc/en/item/19631/index.do",
          "pubDate": "Fri, 18 Nov 2022 00:00:00 GMT"
        }
      ]
    }
  }
}
"""
    fca_feed = b"""<?xml version='1.0' encoding='utf-8'?><rss version='2.0'><channel></channel></rss>"""
    responses = {
        "https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/rss.do": fc_feed,
        "https://decisions.scc-csc.ca/scc-csc/scc-csc/en/json/rss.do": scc_feed,
        "https://decisions.fca-caf.gc.ca/fca-caf/en/nav.do?iframe=true": fca_feed,
    }

    monkeypatch.setattr(
        "immcad_api.sources.official_case_law_client.httpx.Client",
        lambda *args, **kwargs: _FakeClient(responses),
    )

    client = OfficialCaseLawClient(source_registry=_registry())
    request = CaseSearchRequest(
        query="my pr card expired outside canada how do i renew",
        jurisdiction="ca",
        court=None,
        limit=5,
    )
    response = client.search_cases(request)

    assert response.results
    assert response.results[0].citation == "2025 FC 1125"
    assert all("SCC 43" not in result.citation for result in response.results)


def test_official_case_law_client_keeps_matching_scc_records_for_asylum_queries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scc_feed = b"""{
  "rss": {
    "channel": {
      "item": [
        {
          "title": "Refugee rights and asylum claimant protections",
          "link": "https://decisions.scc-csc.ca/scc-csc/scc-csc/en/item/22222/index.do",
          "pubDate": "Fri, 18 Nov 2022 00:00:00 GMT",
          "_neutral_citation": "2022 SCC 22"
        }
      ]
    }
  }
}
"""
    responses = {
        "https://decisions.scc-csc.ca/scc-csc/scc-csc/en/json/rss.do": scc_feed,
    }

    monkeypatch.setattr(
        "immcad_api.sources.official_case_law_client.httpx.Client",
        lambda *args, **kwargs: _FakeClient(responses),
    )

    client = OfficialCaseLawClient(source_registry=_registry())
    response = client.search_cases(
        CaseSearchRequest(
            query="asylum claimant rights",
            jurisdiction="ca",
            court="scc",
            limit=5,
        )
    )

    assert response.results
    assert response.results[0].citation == "2022 SCC 22"


def test_official_case_law_client_maps_court_metadata_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scc_feed = b"""{
  "rss": {
    "channel": {
      "item": [
        {
          "title": "Refugee rights decision update",
          "link": "https://decisions.scc-csc.ca/scc-csc/scc-csc/en/item/41215/index.do",
          "pubDate": "Fri, 18 Nov 2022 00:00:00 GMT",
          "_neutral_citation": "2022 SCC 22",
          "_docket_numbers": ["41215", "41216"],
          "_status": "updated"
        }
      ]
    }
  }
}
"""
    responses = {
        "https://decisions.scc-csc.ca/scc-csc/scc-csc/en/json/rss.do": scc_feed,
    }
    monkeypatch.setattr(
        "immcad_api.sources.official_case_law_client.httpx.Client",
        lambda *args, **kwargs: _FakeClient(responses),
    )

    client = OfficialCaseLawClient(source_registry=_registry())
    response = client.search_cases(
        CaseSearchRequest(
            query="refugee rights",
            jurisdiction="ca",
            court="scc",
            limit=5,
        )
    )

    assert response.results
    assert response.results[0].docket_numbers == ["41215", "41216"]
    assert response.results[0].source_event_type == "updated"


def test_official_case_law_client_uses_citation_year_when_decision_date_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fc_feed = b"""<?xml version='1.0' encoding='utf-8'?>
<rss version='2.0'>
  <channel>
    <item>
      <title>Cadogan v Canada (Citizenship and Immigration), 2025 FC 1125</title>
      <link>https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/item/654321/index.do</link>
      <description>Immigration judicial review record</description>
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

    assert response.results
    assert response.results[0].decision_date.isoformat() == "2025-01-01"


def test_official_case_law_client_filters_results_by_decision_date_range(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fc_feed = b"""<?xml version='1.0' encoding='utf-8'?>
<rss version='2.0'>
  <channel>
    <item>
      <title>Older FC decision</title>
      <link>https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/item/100001/index.do</link>
      <description>Neutral citation 2023 FC 11</description>
      <pubDate>Mon, 01 Jan 2023 00:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Recent FC decision</title>
      <link>https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/item/100002/index.do</link>
      <description>Neutral citation 2025 FC 22</description>
      <pubDate>Mon, 01 Apr 2025 00:00:00 GMT</pubDate>
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
        query="decision",
        jurisdiction="ca",
        court="fc",
        limit=5,
        decision_date_from=date(2024, 1, 1),
    )
    response = client.search_cases(request)

    assert len(response.results) == 1
    assert response.results[0].citation == "2025 FC 22"


def test_official_case_law_client_handles_missing_decision_date_in_range_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fc_feed = b"""<?xml version='1.0' encoding='utf-8'?>
<rss version='2.0'>
  <channel>
    <item>
      <title>Missing date decision</title>
      <link>https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/item/200001/index.do</link>
      <description>Neutral citation 2025 FC 55</description>
    </item>
    <item>
      <title>Dated decision</title>
      <link>https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/item/200002/index.do</link>
      <description>Neutral citation 2024 FC 44</description>
      <pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate>
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
    response = client.search_cases(
        CaseSearchRequest(
            query="decision",
            jurisdiction="ca",
            court="fc",
            limit=5,
            decision_date_from=date(2024, 1, 1),
            decision_date_to=date(2024, 12, 31),
        )
    )

    assert len(response.results) == 1
    assert response.results[0].citation == "2024 FC 44"


def test_official_case_law_client_avoids_substring_token_false_positives(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fc_feed = b"""<?xml version='1.0' encoding='utf-8'?>
<rss version='2.0'>
  <channel>
    <item>
      <title>Cadogan v Canada (Citizenship and Immigration), 2025 FC 1125</title>
      <link>https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/item/654321/index.do</link>
      <description>Immigration judicial review record</description>
      <pubDate>Mon, 23 Jun 2025 00:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Canada (National Revenue) v Carflex Distribution Inc., 2025 FC 96</title>
      <link>https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/item/111111/index.do</link>
      <description>Commercial tax appeal</description>
      <pubDate>Fri, 10 Jan 2025 00:00:00 GMT</pubDate>
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
    response = client.search_cases(
        CaseSearchRequest(
            query="my pr card expired outside canada",
            jurisdiction="ca",
            court="fc",
            limit=5,
        )
    )

    assert response.results
    assert response.results[0].citation == "2025 FC 1125"
    assert all("FC 96" not in result.citation for result in response.results)


def test_official_case_law_client_filters_noise_query_without_token_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fc_feed = b"""<?xml version='1.0' encoding='utf-8'?>
<rss version='2.0'>
  <channel>
    <item>
      <title>Cadogan v Canada (Citizenship and Immigration), 2025 FC 1125</title>
      <link>https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/item/654321/index.do</link>
      <description>Immigration judicial review record</description>
      <pubDate>Mon, 23 Jun 2025 00:00:00 GMT</pubDate>
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
    response = client.search_cases(
        CaseSearchRequest(
            query="oi",
            jurisdiction="ca",
            court="fc",
            limit=5,
        )
    )

    assert response.results == []


def test_official_case_law_client_uses_fresh_cache_without_refetch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    fetch_count: dict[str, int] = {}

    class _CountingClient(_FakeClient):
        def get(self, url: str, *args: Any, **kwargs: Any) -> _FakeResponse:
            fetch_count[url] = fetch_count.get(url, 0) + 1
            return super().get(url, *args, **kwargs)

    monkeypatch.setattr(
        "immcad_api.sources.official_case_law_client.httpx.Client",
        lambda *args, **kwargs: _CountingClient(responses),
    )

    client = OfficialCaseLawClient(
        source_registry=_registry(),
        cache_ttl_seconds=60.0,
        stale_cache_ttl_seconds=120.0,
    )
    request = CaseSearchRequest(
        query="citizenship immigration",
        jurisdiction="ca",
        court="fc",
        limit=5,
    )

    first_response = client.search_cases(request)
    second_response = client.search_cases(request)

    assert first_response.results
    assert second_response.results
    assert fetch_count["https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/rss.do"] == 1


def test_official_case_law_client_returns_stale_cache_and_schedules_refresh(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    fetch_count: dict[str, int] = {}

    class _CountingClient(_FakeClient):
        def get(self, url: str, *args: Any, **kwargs: Any) -> _FakeResponse:
            fetch_count[url] = fetch_count.get(url, 0) + 1
            return super().get(url, *args, **kwargs)

    monkeypatch.setattr(
        "immcad_api.sources.official_case_law_client.httpx.Client",
        lambda *args, **kwargs: _CountingClient(responses),
    )

    client = OfficialCaseLawClient(
        source_registry=_registry(),
        cache_ttl_seconds=2.0,
        stale_cache_ttl_seconds=60.0,
    )
    request = CaseSearchRequest(
        query="citizenship immigration",
        jurisdiction="ca",
        court="fc",
        limit=5,
    )
    client.search_cases(request)
    client._cache_refreshed_at_monotonic_by_source["FC_DECISIONS"] = (
        time.monotonic() - 10.0
    )

    scheduled_refreshes: list[tuple[str, ...]] = []

    def _record_refresh(resolved_sources: list[tuple[str, str]]) -> None:
        scheduled_refreshes.append(
            tuple(source_id for source_id, _source_url in resolved_sources)
        )

    monkeypatch.setattr(client, "_schedule_background_refresh", _record_refresh)

    second_response = client.search_cases(request)

    assert second_response.results
    assert fetch_count["https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/rss.do"] == 1
    assert scheduled_refreshes == [("FC_DECISIONS",)]


def test_official_case_law_client_cache_freshness_is_tracked_per_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fc_feed = b"""<?xml version='1.0' encoding='utf-8'?>
<rss version='2.0'>
  <channel>
    <item>
      <title>Cadogan v Canada (Citizenship and Immigration), 2025 FC 1125</title>
      <link>https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/item/654321/index.do</link>
      <description>Immigration judicial review record</description>
      <pubDate>Mon, 23 Jun 2025 00:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""
    scc_feed = b"""{
  "rss": {
    "channel": {
      "item": [
        {
          "title": "Refugee rights and asylum claimant protections",
          "link": "https://decisions.scc-csc.ca/scc-csc/scc-csc/en/item/22222/index.do",
          "pubDate": "Fri, 18 Nov 2022 00:00:00 GMT",
          "_neutral_citation": "2022 SCC 22"
        }
      ]
    }
  }
}
"""
    fca_feed = b"""<?xml version='1.0' encoding='utf-8'?><rss version='2.0'><channel></channel></rss>"""
    responses = {
        "https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/rss.do": fc_feed,
        "https://decisions.scc-csc.ca/scc-csc/scc-csc/en/json/rss.do": scc_feed,
        "https://decisions.fca-caf.gc.ca/fca-caf/en/nav.do?iframe=true": fca_feed,
    }
    fetch_count: dict[str, int] = {}

    class _CountingClient(_FakeClient):
        def get(self, url: str, *args: Any, **kwargs: Any) -> _FakeResponse:
            fetch_count[url] = fetch_count.get(url, 0) + 1
            return super().get(url, *args, **kwargs)

    monkeypatch.setattr(
        "immcad_api.sources.official_case_law_client.httpx.Client",
        lambda *args, **kwargs: _CountingClient(responses),
    )

    client = OfficialCaseLawClient(
        source_registry=_registry(),
        cache_ttl_seconds=30.0,
        stale_cache_ttl_seconds=300.0,
    )
    request = CaseSearchRequest(
        query="immigration asylum rights",
        jurisdiction="ca",
        court=None,
        limit=5,
    )
    client.search_cases(request)

    stale_timestamp = time.monotonic() - 120.0
    for source_id in ("SCC_DECISIONS", "FC_DECISIONS", "FCA_DECISIONS"):
        client._cache_refreshed_at_monotonic_by_source[source_id] = stale_timestamp

    client._update_cache(
        {
            "FC_DECISIONS": list(client._cached_records_by_source["FC_DECISIONS"]),
        }
    )
    scheduled_refreshes: list[tuple[str, ...]] = []

    def _record_refresh(resolved_sources: list[tuple[str, str]]) -> None:
        scheduled_refreshes.append(
            tuple(source_id for source_id, _source_url in resolved_sources)
        )

    monkeypatch.setattr(client, "_schedule_background_refresh", _record_refresh)

    response = client.search_cases(request)

    assert response.results
    assert fetch_count["https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/rss.do"] == 1
    assert fetch_count["https://decisions.scc-csc.ca/scc-csc/scc-csc/en/json/rss.do"] == 1
    assert (
        fetch_count["https://decisions.fca-caf.gc.ca/fca-caf/en/nav.do?iframe=true"] == 1
    )
    assert scheduled_refreshes == [("FC_DECISIONS", "FCA_DECISIONS", "SCC_DECISIONS")]
