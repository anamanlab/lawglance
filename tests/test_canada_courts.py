from __future__ import annotations

import json

from immcad_api.sources.canada_courts import (
    parse_decisia_rss_feed,
    parse_scc_json_feed,
    validate_court_source_payload,
)


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
    rss = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Doe v Canada, 2024 FC 10</title>
      <link>https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/item/987/index.do</link>
      <pubDate>Mon, 19 Feb 2024 09:00:00 GMT</pubDate>
      <description>Sample case description</description>
    </item>
  </channel>
</rss>
"""
    records = parse_decisia_rss_feed(
        rss.encode("utf-8"),
        source_id="FC_DECISIONS",
        court_code="FC",
    )

    assert len(records) == 1
    record = records[0]
    assert record.source_id == "FC_DECISIONS"
    assert record.court_code == "FC"
    assert record.case_id == "987"
    assert record.citation == "2024 FC 10"
    assert record.pdf_url == "https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/987/1/document.do"


def test_parse_scc_json_feed_coerces_numeric_case_id_to_string() -> None:
    payload = {
        "rss": {
            "channel": {
                "item": [
                    {
                        "id": 456,
                        "title": "Example v Canada, 2024 SCC 4",
                        "link": "https://decisions.scc-csc.ca/scc-csc/scc-csc/en/item/456/index.do",
                        "pubDate": "Tue, 20 Feb 2024 10:00:00 GMT",
                    }
                ]
            }
        }
    }

    records = parse_scc_json_feed(json.dumps(payload).encode("utf-8"))
    assert len(records) == 1
    assert records[0].case_id == "456"


def test_validate_court_source_payload_accepts_fca_caf_citation() -> None:
    rss = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Example v Minister, 2024 CAF 11</title>
      <link>https://decisions.fca-caf.gc.ca/fca-caf/decisions/en/item/333/index.do</link>
      <pubDate>Wed, 21 Feb 2024 12:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""
    summary = validate_court_source_payload("FCA_DECISIONS", rss.encode("utf-8"))

    assert summary is not None
    assert summary.records_total == 1
    assert summary.records_valid == 1
    assert summary.records_invalid == 0


def test_validate_court_source_payload_flags_invalid_fc_citation() -> None:
    rss = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Example without expected citation format</title>
      <link>https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/item/111/index.do</link>
      <pubDate>Thu, 22 Feb 2024 12:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""
    summary = validate_court_source_payload("FC_DECISIONS", rss.encode("utf-8"))

    assert summary is not None
    assert summary.records_total == 1
    assert summary.records_valid == 0
    assert summary.records_invalid == 1
    assert "missing_citation" in summary.errors[0]


def test_validate_court_source_payload_handles_malformed_scc_json_without_raising() -> None:
    summary = validate_court_source_payload("SCC_DECISIONS", b"{not-json")

    assert summary is not None
    assert summary.records_invalid == 1
    assert summary.records_valid == 0
    assert summary.errors
    assert "payload_parse_error" in summary.errors[0]


def test_validate_court_source_payload_handles_malformed_fc_xml_without_raising() -> None:
    summary = validate_court_source_payload("FC_DECISIONS", b"<rss><channel><item>")

    assert summary is not None
    assert summary.records_invalid == 1
    assert summary.records_valid == 0
    assert summary.errors
    assert "payload_parse_error" in summary.errors[0]
