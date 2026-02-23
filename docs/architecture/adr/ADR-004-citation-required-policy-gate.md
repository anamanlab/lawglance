# ADR-004: Enforce Citation-Required Policy Gate

## Table of Contents

- [Table of Contents](#table-of-contents)
- [Context](#context)
- [Options Considered](#options-considered)
- [Decision](#decision)
- [Rationale](#rationale)
- [Trade-offs](#trade-offs)
- [Consequences](#consequences)
- [Revisit Trigger](#revisit-trigger)

- [Context](#context)
- [Options Considered](#options-considered)
- [Decision](#decision)
- [Rationale](#rationale)
- [Trade-offs](#trade-offs)
- [Consequences](#consequences)
- [Revisit Trigger](#revisit-trigger)

- Status: Accepted
- Date: 2026-02-23
- Deciders: IMMCAD maintainers
- Tags: compliance, policy, legal-domain

## Context

Legal-domain assistant must reduce hallucination risk and provide transparent grounding.

## Options Considered

1. **Best-effort citations**
   - Description: return answers even when citations are missing, adding citations only when retrieval succeeds.
   - Pros: higher answer rate; lower immediate implementation effort; fewer user-visible refusals.
   - Cons: weak legal defensibility; inconsistent trust signal; higher hallucination exposure on low-context queries.
   - Decision: rejected because legal-domain safety requires deterministic grounding behavior, not optional enrichment.
2. **Mandatory citation gate with refusal fallback**
   - Description: allow legal factual answers only when at least one valid citation is present; otherwise return controlled refusal guidance.
   - Pros: strong safety posture; consistent and auditable response contract; easier policy/compliance review.
   - Cons: more refusals in sparse-context sessions; requires stricter retrieval and validator logic; can reduce perceived answer coverage.
   - Decision: accepted because it best balances legal risk control with transparent user behavior.
3. **No citations in MVP**
   - Description: defer citations entirely to post-MVP and focus on conversational fluency first.
   - Pros: fastest initial delivery; simplest orchestration path; minimal retrieval validation work.
   - Cons: unacceptable legal/compliance risk; poor explainability; harder future migration because clients depend on non-cited outputs.
   - Decision: rejected due to high risk and direct conflict with product safety requirements.

## Decision

Require at least one valid citation for legal factual answers; otherwise return controlled refusal with guidance.

## Rationale

This aligns with legal safety requirements and improves user trust.

## Trade-offs

- Gains: stronger factual grounding and auditability.
- Costs: more refusals on low-context queries.
- Risks: stricter gate may reduce answer rate.

## Consequences

- Positive: safer and more defensible outputs.
- Negative: possible user friction when context is insufficient.
- Mitigation: clear refusal messaging and query refinement prompts.

## Revisit Trigger

Revisit when retrieval quality improves enough to safely tune strictness thresholds.
