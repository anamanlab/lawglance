from __future__ import annotations

import json

from immcad_api.sources.canada_courts import (
    CourtPayloadValidationConfig,
    parse_decisia_rss_feed,
    parse_scc_json_feed,
    validate_court_source_payload,
)


def _decisia_rss(*, title: str, link: str, pub_date: str, description: str = "") -> bytes:
    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>{title}</title>
      <link>{link}</link>
      <pubDate>{pub_date}</pubDate>
      <description>{description}</description>
    </item>
  </channel>
</rss>
"""
    return rss.encode("utf-8")


def test_parse_scc_json_feed_extracts_record() -> None:
    payload = {
        "rss": {
            "channel": {
                "item": [
                    {
                        "title": "Example v Canada, 2024 SCC 3",
                        "link": "https://decisions.scc-csc.ca/scc-csc/scc-csc/en/item/123/index.do",
                        "pubDate": "Tue, 20 Feb 2024 10:00:00 GMT",
                    }
                ]
            }
        }
    }
    records = parse_scc_json_feed(json.dumps(payload).encode("utf-8"))

    assert len(records) == 1
    record = records[0]
    assert record.source_id == "SCC_DECISIONS"
    assert record.court_code == "SCC"
    assert record.case_id == "123"
    assert record.citation == "2024 SCC 3"
    assert record.pdf_url == "https://decisions.scc-csc.ca/scc-csc/scc-csc/en/123/1/document.do"


def test_parse_decisia_rss_feed_extracts_fc_record() -> None:
    records = parse_decisia_rss_feed(
        _decisia_rss(
            title="Doe v Canada, 2024 FC 10",
            link="https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/item/987/index.do",
            pub_date="Mon, 19 Feb 2024 09:00:00 GMT",
            description="Sample case description",
        ),
        source_id="FC_DECISIONS",
        court_code="FC",
    )

    assert len(records) == 1
    record = records[0]
    assert record.source_id == "FC_DECISIONS"
    assert record.case_id == "987"
    assert record.citation == "2024 FC 10"
    assert record.pdf_url == "https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/987/1/document.do"


def test_validate_court_source_payload_accepts_fca_caf_citation() -> None:
    summary = validate_court_source_payload(
        "FCA_DECISIONS",
        _decisia_rss(
            title="Example v Minister, 2024 CAF 11",
            link="https://decisions.fca-caf.gc.ca/fca-caf/decisions/en/item/333/index.do",
            pub_date="Wed, 21 Feb 2024 12:00:00 GMT",
        ),
    )

    assert summary is not None
    assert summary.records_total == 1
    assert summary.records_valid == 1
    assert summary.records_invalid == 0


def test_validate_court_source_payload_flags_invalid_fc_citation() -> None:
    summary = validate_court_source_payload(
        "FC_DECISIONS",
        _decisia_rss(
            title="Example without expected citation format",
            link="https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/item/111/index.do",
            pub_date="Thu, 22 Feb 2024 12:00:00 GMT",
        ),
    )

    assert summary is not None
    assert summary.records_total == 1
    assert summary.records_valid == 0
    assert summary.records_invalid == 1
    assert "missing_citation" in summary.errors[0]


def test_validate_court_source_payload_accepts_record_within_year_window() -> None:
    summary = validate_court_source_payload(
        "FC_DECISIONS",
        _decisia_rss(
            title="Example v Canada, 2025 FC 12",
            link="https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/item/222/index.do",
            pub_date="Tue, 20 Feb 2025 10:00:00 GMT",
        ),
        validation_config=CourtPayloadValidationConfig(expected_year=2024, year_window=1),
    )

    assert summary is not None
    assert summary.records_total == 1
    assert summary.records_valid == 1
    assert summary.records_invalid == 0


def test_validate_court_source_payload_flags_record_outside_year_window() -> None:
    summary = validate_court_source_payload(
        "FC_DECISIONS",
        _decisia_rss(
            title="Example v Canada, 2022 FC 7",
            link="https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/item/444/index.do",
            pub_date="Tue, 20 Feb 2022 10:00:00 GMT",
        ),
        validation_config=CourtPayloadValidationConfig(expected_year=2024, year_window=1),
    )

    assert summary is not None
    assert summary.records_total == 1
    assert summary.records_valid == 0
    assert summary.records_invalid == 1
    assert "decision_year_out_of_window" in summary.errors[0]

