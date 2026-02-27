"""Embedded fallback for source policy.

Auto-generated from config/source_policy.yaml.
"""

SOURCE_POLICY_PAYLOAD_JSON = r'''
{
  "version": "2026-02-24",
  "jurisdiction": "ca",
  "sources": [
    {
      "source_id": "IRPA",
      "source_class": "official",
      "internal_ingest_allowed": true,
      "production_ingest_allowed": true,
      "answer_citation_allowed": true,
      "export_fulltext_allowed": true,
      "license_notes": "Justice Laws public statute text.",
      "review_owner": "legal-compliance",
      "review_date": "2026-02-24"
    },
    {
      "source_id": "IRPR",
      "source_class": "official",
      "internal_ingest_allowed": true,
      "production_ingest_allowed": true,
      "answer_citation_allowed": true,
      "export_fulltext_allowed": true,
      "license_notes": "Justice Laws public regulation text.",
      "review_owner": "legal-compliance",
      "review_date": "2026-02-24"
    },
    {
      "source_id": "CIT_ACT",
      "source_class": "official",
      "internal_ingest_allowed": true,
      "production_ingest_allowed": true,
      "answer_citation_allowed": true,
      "export_fulltext_allowed": true,
      "license_notes": "Justice Laws public statute text.",
      "review_owner": "legal-compliance",
      "review_date": "2026-02-24"
    },
    {
      "source_id": "CIT_REG",
      "source_class": "official",
      "internal_ingest_allowed": true,
      "production_ingest_allowed": true,
      "answer_citation_allowed": true,
      "export_fulltext_allowed": true,
      "license_notes": "Justice Laws public regulation text.",
      "review_owner": "legal-compliance",
      "review_date": "2026-02-24"
    },
    {
      "source_id": "CIT_REG_NO2",
      "source_class": "official",
      "internal_ingest_allowed": true,
      "production_ingest_allowed": true,
      "answer_citation_allowed": true,
      "export_fulltext_allowed": true,
      "license_notes": "Justice Laws public regulation text.",
      "review_owner": "legal-compliance",
      "review_date": "2026-02-24"
    },
    {
      "source_id": "IRB_ID_RULES",
      "source_class": "official",
      "internal_ingest_allowed": true,
      "production_ingest_allowed": true,
      "answer_citation_allowed": true,
      "export_fulltext_allowed": true,
      "license_notes": "Justice Laws public regulation text.",
      "review_owner": "legal-compliance",
      "review_date": "2026-02-24"
    },
    {
      "source_id": "IRB_IAD_RULES",
      "source_class": "official",
      "internal_ingest_allowed": true,
      "production_ingest_allowed": true,
      "answer_citation_allowed": true,
      "export_fulltext_allowed": true,
      "license_notes": "Justice Laws public regulation text.",
      "review_owner": "legal-compliance",
      "review_date": "2026-02-24"
    },
    {
      "source_id": "IRB_RPD_RULES",
      "source_class": "official",
      "internal_ingest_allowed": true,
      "production_ingest_allowed": true,
      "answer_citation_allowed": true,
      "export_fulltext_allowed": true,
      "license_notes": "Justice Laws public regulation text.",
      "review_owner": "legal-compliance",
      "review_date": "2026-02-24"
    },
    {
      "source_id": "IRB_RAD_RULES",
      "source_class": "official",
      "internal_ingest_allowed": true,
      "production_ingest_allowed": true,
      "answer_citation_allowed": true,
      "export_fulltext_allowed": true,
      "license_notes": "Justice Laws public regulation text.",
      "review_owner": "legal-compliance",
      "review_date": "2026-02-24"
    },
    {
      "source_id": "PIPEDA",
      "source_class": "official",
      "internal_ingest_allowed": true,
      "production_ingest_allowed": true,
      "answer_citation_allowed": true,
      "export_fulltext_allowed": true,
      "license_notes": "Justice Laws public statute text.",
      "review_owner": "legal-compliance",
      "review_date": "2026-02-24"
    },
    {
      "source_id": "CASL",
      "source_class": "official",
      "internal_ingest_allowed": true,
      "production_ingest_allowed": true,
      "answer_citation_allowed": true,
      "export_fulltext_allowed": true,
      "license_notes": "Justice Laws public statute text.",
      "review_owner": "legal-compliance",
      "review_date": "2026-02-24"
    },
    {
      "source_id": "IRCC_PDI",
      "source_class": "official",
      "internal_ingest_allowed": true,
      "production_ingest_allowed": true,
      "answer_citation_allowed": true,
      "export_fulltext_allowed": false,
      "license_notes": "Program delivery instructions; cite source URLs.",
      "review_owner": "legal-compliance",
      "review_date": "2026-02-24"
    },
    {
      "source_id": "EE_MI_CURRENT",
      "source_class": "official",
      "internal_ingest_allowed": true,
      "production_ingest_allowed": true,
      "answer_citation_allowed": true,
      "export_fulltext_allowed": false,
      "license_notes": "Ministerial instruction page; cite source URLs.",
      "review_owner": "legal-compliance",
      "review_date": "2026-02-24"
    },
    {
      "source_id": "EE_MI_INVITES",
      "source_class": "official",
      "internal_ingest_allowed": true,
      "production_ingest_allowed": true,
      "answer_citation_allowed": true,
      "export_fulltext_allowed": false,
      "license_notes": "Ministerial instruction page; cite source URLs.",
      "review_owner": "legal-compliance",
      "review_date": "2026-02-24"
    },
    {
      "source_id": "FEDERAL_LAWS_BULK_XML",
      "source_class": "official",
      "internal_ingest_allowed": true,
      "production_ingest_allowed": true,
      "answer_citation_allowed": true,
      "export_fulltext_allowed": true,
      "license_notes": "Justice Laws Website bulk XML index under Open Government Licence.",
      "review_owner": "legal-compliance",
      "review_date": "2026-02-27"
    },
    {
      "source_id": "CANLII_CASE_BROWSE",
      "source_class": "unofficial",
      "internal_ingest_allowed": true,
      "production_ingest_allowed": true,
      "answer_citation_allowed": true,
      "export_fulltext_allowed": false,
      "license_notes": "Metadata-only API usage under CanLII constraints.",
      "review_owner": "legal-compliance",
      "review_date": "2026-02-24"
    },
    {
      "source_id": "CANLII_CASE_CITATOR",
      "source_class": "unofficial",
      "internal_ingest_allowed": true,
      "production_ingest_allowed": true,
      "answer_citation_allowed": true,
      "export_fulltext_allowed": false,
      "license_notes": "Metadata-only API usage under CanLII constraints.",
      "review_owner": "legal-compliance",
      "review_date": "2026-02-24"
    },
    {
      "source_id": "CANLII_TERMS",
      "source_class": "unofficial",
      "internal_ingest_allowed": true,
      "production_ingest_allowed": true,
      "answer_citation_allowed": false,
      "export_fulltext_allowed": false,
      "license_notes": "Reference source for terms compliance; no full-text export.",
      "review_owner": "legal-compliance",
      "review_date": "2026-02-24"
    },
    {
      "source_id": "SCC_DECISIONS",
      "source_class": "official",
      "internal_ingest_allowed": true,
      "production_ingest_allowed": true,
      "answer_citation_allowed": true,
      "export_fulltext_allowed": true,
      "license_notes": "Official SCC decisions endpoint.",
      "review_owner": "legal-compliance",
      "review_date": "2026-02-24"
    },
    {
      "source_id": "FC_DECISIONS",
      "source_class": "official",
      "internal_ingest_allowed": true,
      "production_ingest_allowed": true,
      "answer_citation_allowed": true,
      "export_fulltext_allowed": true,
      "license_notes": "Official Federal Court decisions endpoint.",
      "review_owner": "legal-compliance",
      "review_date": "2026-02-24"
    },
    {
      "source_id": "FCA_DECISIONS",
      "source_class": "official",
      "internal_ingest_allowed": true,
      "production_ingest_allowed": true,
      "answer_citation_allowed": true,
      "export_fulltext_allowed": true,
      "license_notes": "Official Federal Court of Appeal decisions endpoint.",
      "review_owner": "legal-compliance",
      "review_date": "2026-02-24"
    },
    {
      "source_id": "A2AJ",
      "source_class": "unofficial",
      "internal_ingest_allowed": true,
      "production_ingest_allowed": false,
      "answer_citation_allowed": false,
      "export_fulltext_allowed": false,
      "license_notes": "Internal-only until explicit legal sign-off for production use.",
      "review_owner": "legal-compliance",
      "review_date": "2026-02-24"
    },
    {
      "source_id": "REFUGEE_LAW_LAB",
      "source_class": "unofficial",
      "internal_ingest_allowed": true,
      "production_ingest_allowed": false,
      "answer_citation_allowed": false,
      "export_fulltext_allowed": false,
      "license_notes": "Internal-only until CC BY-NC and upstream terms are approved for production.",
      "review_owner": "legal-compliance",
      "review_date": "2026-02-24"
    }
  ]
}
'''
