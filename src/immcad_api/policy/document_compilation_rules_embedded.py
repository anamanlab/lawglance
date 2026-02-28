"""Embedded fallback for document compilation rules catalog.

Auto-generated from data/policy/document_compilation_rules.ca.json.
"""

CATALOG_PAYLOAD_JSON = r'''
{
  "version": "2026-02-27",
  "jurisdiction": "ca",
  "profiles": [
    {
      "profile_id": "federal_court_jr_leave",
      "forum": "federal_court_jr",
      "title": "Federal Court JR Leave Record",
      "required_documents": [
        {
          "rule_id": "fc_jr_leave_required_notice_of_application",
          "document_type": "notice_of_application",
          "severity": "blocking",
          "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-93-22/",
          "remediation": "Include the notice of application in the leave package."
        },
        {
          "rule_id": "fc_jr_leave_required_decision_under_review",
          "document_type": "decision_under_review",
          "severity": "blocking",
          "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-93-22/",
          "remediation": "Include the decision under review in the leave package."
        },
        {
          "rule_id": "fc_jr_leave_required_affidavit",
          "document_type": "affidavit",
          "severity": "blocking",
          "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-93-22/",
          "remediation": "Include supporting affidavit evidence in the leave package."
        },
        {
          "rule_id": "fc_jr_leave_required_memorandum",
          "document_type": "memorandum",
          "severity": "blocking",
          "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-93-22/",
          "remediation": "Include a memorandum in the leave package."
        }
      ],
      "conditional_rules": [
        {
          "rule_id": "fc_jr_leave_translation_requires_translator_declaration",
          "when_document_type": "translation",
          "requires_document_type": "translator_declaration",
          "severity": "blocking",
          "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-93-22/",
          "remediation": "Add a translator declaration when translations are filed."
        }
      ],
      "order_requirements": {
        "rule_id": "fc_jr_leave_ordering",
        "document_types": [
          "notice_of_application",
          "decision_under_review",
          "affidavit",
          "memorandum",
          "translation",
          "translator_declaration"
        ],
        "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-93-22/",
        "remediation": "Reorder the leave package to match the required sequence."
      },
      "pagination_requirements": {
        "rule_id": "fc_jr_leave_pagination",
        "require_continuous_package_pagination": true,
        "require_index_document": false,
        "index_document_type": "index",
        "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-93-22/",
        "remediation": "Ensure package pagination is continuous."
      }
    },
    {
      "profile_id": "federal_court_jr_hearing",
      "forum": "federal_court_jr",
      "title": "Federal Court JR Hearing Record",
      "required_documents": [
        {
          "rule_id": "fc_jr_hearing_required_notice_of_application",
          "document_type": "notice_of_application",
          "severity": "blocking",
          "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-98-106/",
          "remediation": "Include the originating application document in the hearing package."
        },
        {
          "rule_id": "fc_jr_hearing_required_affidavit",
          "document_type": "affidavit",
          "severity": "blocking",
          "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-98-106/",
          "remediation": "Include affidavit evidence in the hearing package."
        },
        {
          "rule_id": "fc_jr_hearing_required_memorandum",
          "document_type": "memorandum",
          "severity": "blocking",
          "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-98-106/",
          "remediation": "Include a memorandum in the hearing package."
        }
      ],
      "conditional_rules": [
        {
          "rule_id": "fc_jr_hearing_translation_requires_translator_declaration",
          "when_document_type": "translation",
          "requires_document_type": "translator_declaration",
          "severity": "blocking",
          "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-98-106/",
          "remediation": "Add a translator declaration when translations are filed."
        }
      ],
      "order_requirements": {
        "rule_id": "fc_jr_hearing_ordering",
        "document_types": [
          "notice_of_application",
          "affidavit",
          "memorandum",
          "translation",
          "translator_declaration"
        ],
        "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-98-106/",
        "remediation": "Reorder the hearing package to match the required sequence."
      },
      "pagination_requirements": {
        "rule_id": "fc_jr_hearing_pagination",
        "require_continuous_package_pagination": true,
        "require_index_document": false,
        "index_document_type": "index",
        "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-98-106/",
        "remediation": "Ensure package pagination is continuous."
      }
    },
    {
      "profile_id": "rpd",
      "forum": "rpd",
      "title": "Refugee Protection Division Record",
      "required_documents": [
        {
          "rule_id": "rpd_required_disclosure_package",
          "document_type": "disclosure_package",
          "severity": "blocking",
          "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2012-256/",
          "remediation": "Include a disclosure package for RPD filing."
        }
      ],
      "conditional_rules": [
        {
          "rule_id": "rpd_translation_requires_translator_declaration",
          "when_document_type": "translation",
          "requires_document_type": "translator_declaration",
          "severity": "blocking",
          "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2012-256/",
          "remediation": "Add a translator declaration when translations are filed."
        }
      ],
      "order_requirements": {
        "rule_id": "rpd_ordering",
        "document_types": [
          "disclosure_package",
          "translation",
          "translator_declaration"
        ],
        "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2012-256/",
        "remediation": "Reorder the RPD package to match filing expectations."
      },
      "pagination_requirements": {
        "rule_id": "rpd_pagination",
        "require_continuous_package_pagination": true,
        "require_index_document": false,
        "index_document_type": "index",
        "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2012-256/",
        "remediation": "Ensure package pagination is continuous."
      }
    },
    {
      "profile_id": "rad",
      "forum": "rad",
      "title": "Refugee Appeal Division Record",
      "required_documents": [
        {
          "rule_id": "rad_required_appeal_record",
          "document_type": "appeal_record",
          "severity": "blocking",
          "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2012-257/",
          "remediation": "Include an appeal record for RAD filing."
        },
        {
          "rule_id": "rad_required_decision_under_review",
          "document_type": "decision_under_review",
          "severity": "blocking",
          "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2012-257/",
          "remediation": "Include the decision under review in the RAD package."
        },
        {
          "rule_id": "rad_required_memorandum",
          "document_type": "memorandum",
          "severity": "blocking",
          "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2012-257/",
          "remediation": "Include a memorandum in the RAD package."
        }
      ],
      "conditional_rules": [
        {
          "rule_id": "rad_translation_requires_translator_declaration",
          "when_document_type": "translation",
          "requires_document_type": "translator_declaration",
          "severity": "blocking",
          "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2012-257/",
          "remediation": "Add a translator declaration when translations are filed."
        }
      ],
      "order_requirements": {
        "rule_id": "rad_ordering",
        "document_types": [
          "appeal_record",
          "decision_under_review",
          "memorandum",
          "translation",
          "translator_declaration"
        ],
        "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2012-257/",
        "remediation": "Reorder the RAD package to match filing expectations."
      },
      "pagination_requirements": {
        "rule_id": "rad_pagination",
        "require_continuous_package_pagination": true,
        "require_index_document": false,
        "index_document_type": "index",
        "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2012-257/",
        "remediation": "Ensure package pagination is continuous."
      }
    },
    {
      "profile_id": "id",
      "forum": "id",
      "title": "Immigration Division Record",
      "required_documents": [
        {
          "rule_id": "id_required_disclosure_package",
          "document_type": "disclosure_package",
          "severity": "blocking",
          "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2002-229/",
          "remediation": "Include a disclosure package for ID filing."
        },
        {
          "rule_id": "id_required_witness_list",
          "document_type": "witness_list",
          "severity": "blocking",
          "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2002-229/",
          "remediation": "Include a witness list for ID filing."
        }
      ],
      "conditional_rules": [
        {
          "rule_id": "id_translation_requires_translator_declaration",
          "when_document_type": "translation",
          "requires_document_type": "translator_declaration",
          "severity": "blocking",
          "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2002-229/",
          "remediation": "Add a translator declaration when translations are filed."
        }
      ],
      "order_requirements": {
        "rule_id": "id_ordering",
        "document_types": [
          "disclosure_package",
          "witness_list",
          "translation",
          "translator_declaration"
        ],
        "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2002-229/",
        "remediation": "Reorder the ID package to match filing expectations."
      },
      "pagination_requirements": {
        "rule_id": "id_pagination",
        "require_continuous_package_pagination": true,
        "require_index_document": false,
        "index_document_type": "index",
        "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2002-229/",
        "remediation": "Ensure package pagination is continuous."
      }
    },
    {
      "profile_id": "iad",
      "forum": "iad",
      "title": "Immigration Appeal Division Record",
      "required_documents": [
        {
          "rule_id": "iad_required_appeal_record",
          "document_type": "appeal_record",
          "severity": "blocking",
          "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2022-277/",
          "remediation": "Include an appeal record for IAD filing."
        },
        {
          "rule_id": "iad_required_decision_under_review",
          "document_type": "decision_under_review",
          "severity": "blocking",
          "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2022-277/",
          "remediation": "Include the decision under review in the IAD package."
        },
        {
          "rule_id": "iad_required_disclosure_package",
          "document_type": "disclosure_package",
          "severity": "blocking",
          "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2022-277/",
          "remediation": "Include disclosure materials in the IAD package."
        }
      ],
      "conditional_rules": [
        {
          "rule_id": "iad_translation_requires_translator_declaration",
          "when_document_type": "translation",
          "requires_document_type": "translator_declaration",
          "severity": "blocking",
          "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2022-277/",
          "remediation": "Add a translator declaration when translations are filed."
        }
      ],
      "order_requirements": {
        "rule_id": "iad_ordering",
        "document_types": [
          "appeal_record",
          "decision_under_review",
          "disclosure_package",
          "translation",
          "translator_declaration"
        ],
        "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2022-277/",
        "remediation": "Reorder the IAD package to match filing expectations."
      },
      "pagination_requirements": {
        "rule_id": "iad_pagination",
        "require_continuous_package_pagination": true,
        "require_index_document": false,
        "index_document_type": "index",
        "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2022-277/",
        "remediation": "Ensure package pagination is continuous."
      }
    },
    {
      "profile_id": "iad_sponsorship",
      "forum": "iad",
      "title": "Immigration Appeal Division Sponsorship Appeal Record",
      "required_documents": [
        {
          "rule_id": "iad_sponsorship_required_appeal_record",
          "document_type": "appeal_record",
          "severity": "blocking",
          "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2022-277/",
          "remediation": "Include an appeal record for IAD sponsorship appeal filing."
        },
        {
          "rule_id": "iad_sponsorship_required_decision_under_review",
          "document_type": "decision_under_review",
          "severity": "blocking",
          "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2022-277/",
          "remediation": "Include the decision under review in the IAD sponsorship appeal package."
        },
        {
          "rule_id": "iad_sponsorship_required_disclosure_package",
          "document_type": "disclosure_package",
          "severity": "blocking",
          "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2022-277/",
          "remediation": "Include disclosure materials in the IAD sponsorship appeal package."
        }
      ],
      "conditional_rules": [
        {
          "rule_id": "iad_sponsorship_translation_requires_translator_declaration",
          "when_document_type": "translation",
          "requires_document_type": "translator_declaration",
          "severity": "blocking",
          "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2022-277/",
          "remediation": "Add a translator declaration when translations are filed."
        }
      ],
      "order_requirements": {
        "rule_id": "iad_sponsorship_ordering",
        "document_types": [
          "appeal_record",
          "decision_under_review",
          "disclosure_package",
          "translation",
          "translator_declaration"
        ],
        "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2022-277/",
        "remediation": "Reorder the IAD sponsorship appeal package to match filing expectations."
      },
      "pagination_requirements": {
        "rule_id": "iad_sponsorship_pagination",
        "require_continuous_package_pagination": true,
        "require_index_document": false,
        "index_document_type": "index",
        "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2022-277/",
        "remediation": "Ensure package pagination is continuous."
      }
    },
    {
      "profile_id": "iad_residency",
      "forum": "iad",
      "title": "Immigration Appeal Division Residency Obligation Appeal Record",
      "required_documents": [
        {
          "rule_id": "iad_residency_required_appeal_record",
          "document_type": "appeal_record",
          "severity": "blocking",
          "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2022-277/",
          "remediation": "Include an appeal record for IAD residency obligation appeal filing."
        },
        {
          "rule_id": "iad_residency_required_decision_under_review",
          "document_type": "decision_under_review",
          "severity": "blocking",
          "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2022-277/",
          "remediation": "Include the decision under review in the IAD residency obligation appeal package."
        },
        {
          "rule_id": "iad_residency_required_disclosure_package",
          "document_type": "disclosure_package",
          "severity": "blocking",
          "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2022-277/",
          "remediation": "Include disclosure materials in the IAD residency obligation appeal package."
        }
      ],
      "conditional_rules": [
        {
          "rule_id": "iad_residency_translation_requires_translator_declaration",
          "when_document_type": "translation",
          "requires_document_type": "translator_declaration",
          "severity": "blocking",
          "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2022-277/",
          "remediation": "Add a translator declaration when translations are filed."
        }
      ],
      "order_requirements": {
        "rule_id": "iad_residency_ordering",
        "document_types": [
          "appeal_record",
          "decision_under_review",
          "disclosure_package",
          "translation",
          "translator_declaration"
        ],
        "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2022-277/",
        "remediation": "Reorder the IAD residency obligation appeal package to match filing expectations."
      },
      "pagination_requirements": {
        "rule_id": "iad_residency_pagination",
        "require_continuous_package_pagination": true,
        "require_index_document": false,
        "index_document_type": "index",
        "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2022-277/",
        "remediation": "Ensure package pagination is continuous."
      }
    },
    {
      "profile_id": "iad_admissibility",
      "forum": "iad",
      "title": "Immigration Appeal Division Admissibility Appeal Record",
      "required_documents": [
        {
          "rule_id": "iad_admissibility_required_appeal_record",
          "document_type": "appeal_record",
          "severity": "blocking",
          "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2022-277/",
          "remediation": "Include an appeal record for IAD admissibility appeal filing."
        },
        {
          "rule_id": "iad_admissibility_required_decision_under_review",
          "document_type": "decision_under_review",
          "severity": "blocking",
          "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2022-277/",
          "remediation": "Include the decision under review in the IAD admissibility appeal package."
        },
        {
          "rule_id": "iad_admissibility_required_disclosure_package",
          "document_type": "disclosure_package",
          "severity": "blocking",
          "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2022-277/",
          "remediation": "Include disclosure materials in the IAD admissibility appeal package."
        }
      ],
      "conditional_rules": [
        {
          "rule_id": "iad_admissibility_translation_requires_translator_declaration",
          "when_document_type": "translation",
          "requires_document_type": "translator_declaration",
          "severity": "blocking",
          "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2022-277/",
          "remediation": "Add a translator declaration when translations are filed."
        }
      ],
      "order_requirements": {
        "rule_id": "iad_admissibility_ordering",
        "document_types": [
          "appeal_record",
          "decision_under_review",
          "disclosure_package",
          "translation",
          "translator_declaration"
        ],
        "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2022-277/",
        "remediation": "Reorder the IAD admissibility appeal package to match filing expectations."
      },
      "pagination_requirements": {
        "rule_id": "iad_admissibility_pagination",
        "require_continuous_package_pagination": true,
        "require_index_document": false,
        "index_document_type": "index",
        "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2022-277/",
        "remediation": "Ensure package pagination is continuous."
      }
    },
    {
      "profile_id": "ircc_pr_card_renewal",
      "forum": "ircc_application",
      "title": "IRCC Permanent Resident Card Renewal Application Package",
      "required_documents": [
        {
          "rule_id": "ircc_pr_card_renewal_required_disclosure_package",
          "document_type": "disclosure_package",
          "severity": "blocking",
          "source_url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/application/application-forms-guides/application-renew-replace-permanent-resident-card.html",
          "remediation": "Include the core PR card renewal application package materials."
        },
        {
          "rule_id": "ircc_pr_card_renewal_required_supporting_evidence",
          "document_type": "supporting_evidence",
          "severity": "blocking",
          "source_url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/application/application-forms-guides/application-renew-replace-permanent-resident-card.html",
          "remediation": "Include supporting evidence for physical presence and identity requirements."
        }
      ],
      "conditional_rules": [
        {
          "rule_id": "ircc_pr_card_renewal_translation_requires_translator_declaration",
          "when_document_type": "translation",
          "requires_document_type": "translator_declaration",
          "severity": "blocking",
          "source_url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/application/application-forms-guides/application-renew-replace-permanent-resident-card.html",
          "remediation": "Add a translator declaration when translated evidence is filed."
        }
      ],
      "order_requirements": {
        "rule_id": "ircc_pr_card_renewal_ordering",
        "document_types": [
          "disclosure_package",
          "supporting_evidence",
          "translation",
          "translator_declaration"
        ],
        "source_url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/application/application-forms-guides/application-renew-replace-permanent-resident-card.html",
        "remediation": "Reorder the IRCC PR card renewal package to match application guidance."
      },
      "pagination_requirements": {
        "rule_id": "ircc_pr_card_renewal_pagination",
        "require_continuous_package_pagination": true,
        "require_index_document": false,
        "index_document_type": "index",
        "source_url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/application/application-forms-guides/application-renew-replace-permanent-resident-card.html",
        "remediation": "Ensure package pagination is continuous."
      }
    }
  ]
}
'''
