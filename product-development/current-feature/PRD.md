# Product Requirements Document (PRD)

## Feature
Chat API Scaffold

## Document Purpose
Define product requirements for introducing an API-first chat scaffold that decouples UI from backend orchestration, enforces safety/grounding policies, and enables reliable integration for the IMMCAD experience.

## Product Context
- Product reference: `docs/IMMCAD_System_Overview.md`
- Feature reference: `docs/features/chat-api-scaffold.md`
- Risk context: `docs/features/chat-api-scaffold-risk-review.md`
- JTBD reference: derived for this PRD from product mission and feature goals (no standalone `JTBD.md` found in repo)

## Problem Statement
The current prototype experience is tightly coupled and not optimized for stable API-driven integration. This creates friction for frontend evolution, makes policy consistency harder to enforce, and limits reliability when provider failures occur.

Users need a dependable chat backend that consistently applies jurisdiction and citation policies, handles fallback behavior transparently, and provides stable contracts for product integration.

## User Needs
- Users need consistent and trustworthy responses with clear policy behavior.
- Users need factual legal information responses to include supporting citations.
- Users need safe handling for requests that cross legal-advice boundaries.
- Integrators need stable API contracts to build and evolve UI features with confidence.
- Operators need traceability to diagnose failures and fallback behavior quickly.

## Jobs To Be Done (JTBD)
1. When I ask a legal-information question, I want a grounded response with citations, so I can verify what I read.
2. When my request is unsafe or out of policy, I want a clear refusal, so I am not misled.
3. As a product/frontend builder, I want predictable API responses, so I can ship UI features without backend guesswork.
4. As an operator, I want request traceability and fallback visibility, so I can resolve issues faster.

## Goals
- Establish an API-first chat foundation for IMMCAD.
- Enforce policy blocks and citation-required behavior consistently.
- Provide deterministic integration behavior for case-search wiring.
- Improve reliability through provider routing with ordered fallback.
- Support operational debugging through response trace identifiers.

## Non-Goals
- Full production-grade authentication/authorization redesign.
- Final end-to-end retrieval quality optimization.
- Complete external provider integration hardening beyond scaffold intent.
- Broad UI redesign.

## Target Users and Stakeholders
- Primary users: people seeking Canadian immigration legal information.
- Secondary users: frontend/product developers integrating chat and case search.
- Stakeholders: product, engineering, legal/compliance, and operations.

## Feature Scope
### In Scope
- API endpoints for chat and case-search scaffolding.
- Policy-block handling for legal-advice and unsafe prompts.
- Citation-required behavior for non-refusal responses.
- Ordered provider routing (primary then fallback).
- Trace ID exposure in response headers.

### Out of Scope
- Full production authN/authZ rollout.
- Complete CanLII production integration maturity.
- Final retrieval/index corpus integration completeness.
- Advanced quota and monetization controls.

## Functional Requirements
1. The product must expose a chat API contract that frontend clients can call reliably.
2. The product must expose a case-search API contract for legal research workflow wiring.
3. The system must block/refuse requests that violate legal-advice safety policy.
4. The system must enforce citation-required output for factual legal responses when not refusing.
5. The routing behavior must attempt the primary provider first, then fallback in defined order.
6. Every API response must include a trace identifier for observability and support.
7. Error responses must follow a consistent product-facing envelope.

## User Experience Requirements
- Chat responses should feel consistent even during provider fallback scenarios.
- Refusal messages should be explicit, understandable, and safe.
- Citation behavior should be predictable in factual responses.
- Case-search results should provide stable structure for UI rendering.
- Failure states should preserve user trust through clear messaging.

## Success Metrics
- API contract conformance: 100% for defined chat and case-search schemas.
- Policy enforcement pass rate: 100% for defined block/refusal test scenarios.
- Citation-required compliance: 100% for in-scope non-refusal factual responses.
- Traceability coverage: 100% of API responses include trace ID.
- Fallback resilience: successful response continuity maintained for primary provider failure scenarios in test coverage.

## Acceptance Criteria
1. Chat and case-search endpoints return schema-aligned payloads.
2. Policy-block scenarios return clear refusals with policy reason.
3. Citation-required rule is enforced for non-refusal factual responses.
4. Ordered provider fallback behavior is demonstrated in validation tests.
5. Response headers include trace ID consistently.
6. Error responses are standardized and usable by consuming clients.

## Dependencies
- Provider availability and credentials for primary/fallback routes.
- Policy definitions for refusal and citation behavior.
- Legal/compliance alignment on safety boundary messaging.
- Downstream integration of retrieval and source systems.

## Risks and Mitigations
- Risk: Contract drift between backend behavior and client expectations.
  - Mitigation: enforce schema contract tests and standardized error envelopes.
- Risk: Security exposure from under-protected API surface.
  - Mitigation: apply environment-aware token policy and secret management.
- Risk: Fallback ambiguity reduces incident diagnosability.
  - Mitigation: preserve fallback reason and trace identifiers in response paths.
- Risk: External case-source integration instability.
  - Mitigation: maintain graceful degradation and deterministic fallback behavior.

## High-Level Technical Considerations
- API-first boundary should remain decoupled from UI implementation.
- Policy enforcement must be centralized for consistent behavior.
- Provider abstraction should support explicit routing order and fallback reason reporting.
- Observability should include trace-first diagnostics for support and compliance review.

## Open Questions
- What minimum security posture is required before external exposure beyond internal environments?
- How should user-facing messaging differ across refusal, degraded fallback, and generic error states?
- What readiness threshold should be required before enabling broader case-search reliance?

## Release Readiness Statement
This feature is ready for broader integration once policy and citation acceptance criteria pass, API contracts are stable for consumers, and operational traceability is consistently validated.
