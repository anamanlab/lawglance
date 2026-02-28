# Court/Tribunal Document Compilation Rules Baseline (Canada Immigration)

Date: 2026-02-27  
Owner: IMMCAD platform maintainers

## Purpose

Document the enforceable, source-backed filing compilation requirements that should drive IMMCAD's rule-aware document package engine for:
- Federal Court judicial review (immigration)
- IRB divisions: RPD, RAD, ID, IAD

This document is a requirements baseline for implementation and testing. It is not legal advice.

## Primary Legal Sources

1. Federal Courts Citizenship, Immigration and Refugee Protection Rules (SOR/93-22)
- https://laws-lois.justice.gc.ca/eng/regulations/SOR-93-22/

2. Federal Courts Rules (SOR/98-106)
- https://laws-lois.justice.gc.ca/eng/regulations/SOR-98-106/

3. Refugee Protection Division Rules (SOR/2012-256)
- https://laws-lois.justice.gc.ca/eng/regulations/SOR-2012-256/

4. Refugee Appeal Division Rules (SOR/2012-257)
- https://laws-lois.justice.gc.ca/eng/regulations/SOR-2012-257/

5. Immigration Division Rules (SOR/2002-229)
- https://laws-lois.justice.gc.ca/eng/regulations/SOR-2002-229/

6. Immigration Appeal Division Rules, 2022 (SOR/2022-277)
- https://laws-lois.justice.gc.ca/eng/regulations/SOR-2022-277/

## Operational Filing Sources (Non-regulation guidance)

1. Federal Court E-Filing guidance
- https://www-u.fct-cf.gc.ca/en/pages/online-access/e-filing

2. IRB My Case / electronic submission guidance
- https://irb.gc.ca/en/legal-policy/procedures/Pages/my-case-portal-registration-submission-documents.aspx
- https://irb.gc.ca/en/filing-refugee-appeal/responding-minister-appeal-refugee-decision/pages/index.aspx
- https://irb.gc.ca/en/legal-policy/procedures/Pages/id-communicating-electronic-mail.aspx

## Rule Matrix (Enforceable Requirements)

### Federal Court JR (Immigration leave stage)

Source: SOR/93-22 rule 10(2), rule 11

Core requirements:
- Applicant must perfect leave with a record on consecutively numbered pages.
- Applicant record has mandatory order (application, decision/order, written reasons or notice, anonymity request if any, supporting affidavit(s), memorandum, language statement).
- Respondent opposing leave must provide memorandum and may provide affidavit(s) within the prescribed timeline.

Machine-check implications:
- Validate required sections present and ordered.
- Validate consecutive package page numbering.
- Validate leave-stage profile content before package generation.

### Federal Court JR (hearing stage)

Source: SOR/98-106 rule 309(2), rule 310

Core requirements:
- Applicant record must be on consecutively numbered pages.
- Applicant record must include TOC and ordered contents defined in rule 309(2).
- Respondent record timelines and structure apply per rule 310.

Machine-check implications:
- Distinct profile from leave stage (`federal_court_jr_hearing`).
- Ordered record and TOC validation.
- Respondent package profile support.

### RPD

Source: SOR/2012-256 rules 31, 32, 34, 35, 36

Core requirements:
- If multiple documents are filed, provide list identifying each document.
- Consecutive page numbering across all provided documents as one set.
- Non-English/French documents require translation + translator declaration.
- Disclosure timing rules apply for evidence documents.

Machine-check implications:
- Enforce `translation -> translator_declaration` conditional rule.
- Require multi-document index/list artifact.
- Apply disclosure deadline validations where dates are available.
- Flag late/undisclosed evidence as blocking or warning by profile.

### RAD

Source: SOR/2012-257 rules 3, 9, 27, 28

Core requirements:
- Appellant records (person and Minister pathways) include ordered documents and consecutive numbering.
- If multiple documents are filed, provide list identifying each document.
- Consecutive page numbering across all provided documents.
- Non-English/French documents require translation + translator declaration.
- Memorandum length limits apply for at least the person-appellant pathway under rule 3(4).

Machine-check implications:
- Add pathway-specific RAD profiles where needed (`rad_person`, `rad_minister`).
- Validate memorandum page-length constraints.
- Enforce list + numbering + translation declaration rules.

### ID

Source: SOR/2002-229 rules 24, 25, 26

Core requirements:
- Documents prepared for proceedings must be paginated and formatted as required.
- Each document must be consecutively numbered; where multiple documents are provided, include a list of documents and their numbers.
- Non-English/French documents require translation + translator declaration.
- Disclosure deadlines apply based on proceeding type.

Machine-check implications:
- Validate numbering and multi-document list behavior.
- Enforce translation declaration condition.
- Validate hearing-relative disclosure deadlines when data exists.

### IAD (current framework)

Source: SOR/2022-277 rules 20, 21, 22, 24, 26, 31, 32, 33

Core requirements:
- Appeal record contents vary by appeal type (sponsorship, admissibility hearing, examination, residency obligation) and include TOC.
- Appeal record delivery deadlines are explicit by appeal type.
- Evidence disclosure timelines apply (including response evidence timeline).
- Documents prepared by parties must satisfy formatting constraints.
- If multiple documents are filed, pages must be consecutively numbered as one set and accompanied by a document list.
- Non-English/French documents require translation + translator written statement.

Machine-check implications:
- Introduce subtype-aware IAD profiles (`iad_sponsorship`, `iad_admissibility`, etc.).
- Enforce typed record-content requirements and timelines.
- Validate multi-document list + pagination + translation statements.

## Operational Constraints For Compilation Engine

These are implementation constraints from filing channels and operational guidance, separate from statutory rules:

- Federal Court e-filing expects PDF-only, searchable typed text, and no password protection; document package size/page constraints and bookmark expectations are specified in portal guidance.
- IRB electronic channels (My Case/email) impose file-size/attachment constraints and PDF requirements; these should be validated pre-upload and pre-export.

Engine implications:
- Add profile-level output constraints (max pages, max bytes, split-strategy).
- Add a preflight validator that returns deterministic remediation errors.

## Current System Gap Snapshot (as of 2026-02-27)

Observed in current runtime:
- Rule-aware readiness exists, but only as high-level required-doc checks for five forums.
- TOC exists only as ordered filename/type list; no page map or compiled pagination model.
- No compiled binder PDF assembly exists.
- No formal source-cited rule catalog with versioning.
- No deadline-aware rule validation (where date inputs exist).

## Required Implementation Artifacts

1. Versioned rule catalog with source provenance and effective dates.
2. Rule validator returning typed violations (`blocking`/`warning`) with source references.
3. Compilation planner with TOC page ranges and package pagination metadata.
4. Forum/subtype builders for FC leave/hearing and IAD appeal subtypes.
5. Preflight output validator for filing-channel constraints.

## Linked Execution Plan

Execution plan:
- [Rule-Aware Court/Tribunal Document Compilation Implementation Plan](../plans/2026-02-27-rule-aware-document-compilation-implementation-plan.md)
