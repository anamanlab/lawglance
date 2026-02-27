from __future__ import annotations

from datetime import date

from immcad_api.sources.federal_laws_bulk_xml import (
    infer_official_number_from_registry_url,
    parse_federal_law_section_chunks,
    parse_federal_laws_index,
    select_index_entry,
    target_federal_law_source_ids,
)
from immcad_api.sources.source_registry import SourceRegistry


def test_parse_federal_laws_index_extracts_entries() -> None:
    payload = b"""<?xml version="1.0" encoding="UTF-8"?>
<ActsRegsList>
  <Acts>
    <Act>
      <UniqueId>I-2.5</UniqueId>
      <OfficialNumber>I-2.5</OfficialNumber>
      <Language>eng</Language>
      <LinkToXML>http://laws-lois.justice.gc.ca/eng/XML/I-2.5.xml</LinkToXML>
      <LinkToHTMLToC>http://laws-lois.justice.gc.ca/eng/acts/I-2.5/index.html</LinkToHTMLToC>
      <Title>Immigration and Refugee Protection Act</Title>
      <CurrentToDate>2026-02-18</CurrentToDate>
    </Act>
  </Acts>
</ActsRegsList>
"""
    entries = parse_federal_laws_index(payload)

    assert len(entries) == 1
    entry = entries[0]
    assert entry.official_number == "I-2.5"
    assert entry.language == "eng"
    assert entry.link_to_xml == "https://laws-lois.justice.gc.ca/eng/XML/I-2.5.xml"
    assert entry.link_to_html_toc == "https://laws-lois.justice.gc.ca/eng/acts/I-2.5/index.html"
    assert entry.title == "Immigration and Refugee Protection Act"
    assert entry.current_to_date == date(2026, 2, 18)


def test_parse_federal_laws_index_uses_unique_id_when_official_number_missing() -> None:
    payload = b"""<?xml version="1.0" encoding="UTF-8"?>
<ActsRegsList>
  <Regulations>
    <Regulation>
      <UniqueId>SOR-2002-227</UniqueId>
      <Language>eng</Language>
      <LinkToXML>http://laws-lois.justice.gc.ca/eng/XML/SOR-2002-227.xml</LinkToXML>
      <LinkToHTMLToC>http://laws-lois.justice.gc.ca/eng/regulations/SOR-2002-227/index.html</LinkToHTMLToC>
      <Title>Immigration and Refugee Protection Regulations</Title>
      <CurrentToDate>2026-02-18</CurrentToDate>
    </Regulation>
  </Regulations>
</ActsRegsList>
"""
    entries = parse_federal_laws_index(payload)

    assert len(entries) == 1
    assert entries[0].unique_id == "SOR-2002-227"
    assert entries[0].official_number == "SOR-2002-227"


def test_infer_official_number_from_registry_url_extracts_segment() -> None:
    official_number = infer_official_number_from_registry_url(
        "https://laws-lois.justice.gc.ca/eng/acts/I-2.5/FullText.html"
    )
    assert official_number == "I-2.5"


def test_target_federal_law_source_ids_maps_registry_sources() -> None:
    registry = SourceRegistry.model_validate(
        {
            "version": "2026-02-27",
            "jurisdiction": "ca",
            "sources": [
                {
                    "source_id": "FEDERAL_LAWS_BULK_XML",
                    "source_type": "statute",
                    "instrument": "Justice Laws bulk XML",
                    "url": "https://laws-lois.justice.gc.ca/eng/XML/Legis.xml",
                    "update_cadence": "daily",
                },
                {
                    "source_id": "IRPA",
                    "source_type": "statute",
                    "instrument": "IRPA",
                    "url": "https://laws-lois.justice.gc.ca/eng/acts/I-2.5/FullText.html",
                    "update_cadence": "weekly",
                },
                {
                    "source_id": "IRCC_PDI",
                    "source_type": "policy",
                    "instrument": "PDI",
                    "url": "https://www.canada.ca/en/immigration-refugees-citizenship/corporate/publications-manuals/operational-bulletins-manuals.html",
                    "update_cadence": "daily",
                },
            ],
        }
    )

    targets = target_federal_law_source_ids(registry)

    assert targets == {"IRPA": "I-2.5"}


def test_select_index_entry_prefers_requested_language() -> None:
    payload = b"""<?xml version="1.0" encoding="UTF-8"?>
<ActsRegsList>
  <Acts>
    <Act>
      <UniqueId>I-2.5</UniqueId>
      <OfficialNumber>I-2.5</OfficialNumber>
      <Language>fra</Language>
      <LinkToXML>http://laws-lois.justice.gc.ca/fra/XML/I-2.5.xml</LinkToXML>
      <LinkToHTMLToC>http://laws-lois.justice.gc.ca/fra/lois/I-2.5/index.html</LinkToHTMLToC>
      <Title>Loi sur l'immigration et la protection des refugies</Title>
      <CurrentToDate>2026-02-18</CurrentToDate>
    </Act>
    <Act>
      <UniqueId>I-2.5</UniqueId>
      <OfficialNumber>I-2.5</OfficialNumber>
      <Language>eng</Language>
      <LinkToXML>http://laws-lois.justice.gc.ca/eng/XML/I-2.5.xml</LinkToXML>
      <LinkToHTMLToC>http://laws-lois.justice.gc.ca/eng/acts/I-2.5/index.html</LinkToHTMLToC>
      <Title>Immigration and Refugee Protection Act</Title>
      <CurrentToDate>2026-02-18</CurrentToDate>
    </Act>
  </Acts>
</ActsRegsList>
"""
    entries = parse_federal_laws_index(payload)
    selected = select_index_entry(entries, identifier="I-2.5", language="eng")

    assert selected is not None
    assert selected.language == "eng"


def test_parse_federal_law_section_chunks_extracts_heading_and_text() -> None:
    index_payload = b"""<?xml version="1.0" encoding="UTF-8"?>
<ActsRegsList>
  <Acts>
    <Act>
      <UniqueId>I-2.5</UniqueId>
      <OfficialNumber>I-2.5</OfficialNumber>
      <Language>eng</Language>
      <LinkToXML>http://laws-lois.justice.gc.ca/eng/XML/I-2.5.xml</LinkToXML>
      <LinkToHTMLToC>http://laws-lois.justice.gc.ca/eng/acts/I-2.5/index.html</LinkToHTMLToC>
      <Title>Immigration and Refugee Protection Act</Title>
      <CurrentToDate>2026-02-18</CurrentToDate>
    </Act>
  </Acts>
</ActsRegsList>
"""
    entry = parse_federal_laws_index(index_payload)[0]
    act_payload = b"""<?xml version="1.0" encoding="UTF-8"?>
<Statute>
  <Body>
    <Heading>
      <Label>PART 1</Label>
      <TitleText>Immigration to Canada</TitleText>
    </Heading>
    <Section>
      <Label>3</Label>
      <MarginalNote>Objectives</MarginalNote>
      <Subsection>
        <Label>(1)</Label>
        <Text>This Act has the following objectives:</Text>
      </Subsection>
      <Paragraph>
        <Label>(a)</Label>
        <Text>to permit Canada to pursue the maximum social, cultural and economic benefits of immigration;</Text>
      </Paragraph>
    </Section>
  </Body>
</Statute>
"""
    chunks = parse_federal_law_section_chunks(
        act_payload,
        source_id="IRPA",
        index_entry=entry,
    )

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.source_id == "IRPA"
    assert chunk.official_number == "I-2.5"
    assert chunk.heading_label == "PART 1"
    assert chunk.heading_title == "Immigration to Canada"
    assert chunk.section_label == "3"
    assert chunk.section_title == "Objectives"
    assert "This Act has the following objectives:" in chunk.text
    assert chunk.section_url == "https://laws-lois.justice.gc.ca/eng/acts/I-2.5/section-3.html"
    assert chunk.content_hash_sha256
