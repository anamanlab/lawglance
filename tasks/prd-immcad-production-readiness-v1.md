# PRD: IMMCAD Production-Ready V1 (Canada Immigration AI Assistant)

## 1. Introduction/Overview

IMMCAD needs to move from scaffold readiness to production-ready operation for Canada-only immigration and citizenship informational guidance. This feature package hardens legal-source reliability, policy safety, case-law integration, security/compliance controls, observability, and release governance, while shipping a minimal chat-first web experience.

The problem this solves: current behavior can appear compliant in tests but still permit non-authoritative fallbacks or incomplete legal corpus governance in production.

## 2. Goals

- Ship a production-ready V1 that is Canada-jurisdiction-only and source-grounded.
- Enforce authoritative-source governance across statute, regulation, policy, and case law.
- Prevent personalized legal-advice/representation behavior through policy gates.
- Provide reliable provider routing with deterministic failure behavior.
- Establish release gates with legal/compliance sign-off and operational readiness evidence.
- Deliver a minimal chat UI with visible disclaimer and citations.

## 3. User Stories

### US-001: Complete Canada legal source registry
**Description:** As a legal/compliance owner, I want all mandatory Canadian immigration sources tracked so that answers are grounded in the full required corpus.

**Acceptance Criteria:**
- [ ] Source registry includes IRPA, IRPR, Citizenship Act, Citizenship Regulations, Citizenship Regulations No. 2.
- [ ] Source registry includes IRB procedural rules: ID, IAD, RPD, RAD.
- [ ] Source registry includes policy sources: IRCC PDI, Express Entry MI current, Express Entry invitation rounds.
- [ ] Source registry includes product compliance references: PIPEDA, CASL, CanLII Terms.
- [ ] Typecheck/lint passes.

### US-002: Enforce strict source-registry validation
**Description:** As an engineer, I want CI checks to fail on missing or untrusted legal sources so that production cannot ship with incomplete governance.

**Acceptance Criteria:**
- [ ] Validation script enforces required source IDs and trusted domains.
- [ ] Unit tests fail when any required source is missing.
- [ ] Quality workflow runs registry validation on PR and main branch.
- [ ] Typecheck/lint passes.

### US-003: Make CanLII case search authoritative-only in production
**Description:** As a user, I want case-law results to be real or explicitly unavailable so that fabricated cases are never presented as authoritative.

**Acceptance Criteria:**
- [ ] In production mode, CanLII client does not return synthetic scaffold cases.
- [ ] On API/key/network failure, API returns a structured unavailability/refusal response.
- [ ] Response includes trace ID and actionable retry/escalation guidance.
- [ ] Typecheck/lint passes.

### US-004: Harden legal policy refusal behavior
**Description:** As a compliance owner, I want robust refusal handling for representation/advice requests so that the system remains informational only.

**Acceptance Criteria:**
- [ ] Policy block covers representation, personalized legal strategy, filing on behalf, and guarantee requests.
- [ ] Allowed informational questions remain answerable.
- [ ] Policy-block test suite includes positive and negative examples.
- [ ] Typecheck/lint passes.

### US-005: Enforce citation provenance contract
**Description:** As an end user, I want each legal response to include verifiable citations so that I can inspect sources and trust the answer boundaries.

**Acceptance Criteria:**
- [ ] Non-refusal legal responses require at least one citation.
- [ ] Citation schema includes source ID, title, URL, pin, and snippet.
- [ ] In production mode, synthetic citations are disabled.
- [ ] Typecheck/lint passes.

### US-006: Lock provider routing policy for production
**Description:** As a platform engineer, I want explicit provider order and fallback rules so that reliability and behavior are predictable.

**Acceptance Criteria:**
- [ ] Primary provider is OpenAI (attempted first).
- [ ] Fallback provider is Gemini (second); Grok remains optional behind feature flag.
- [ ] Retry/circuit-breaker behavior is tested for transient provider failures.
- [ ] Typecheck/lint passes.

### US-007: Enforce security baseline on `/api/*`
**Description:** As a security owner, I want API access controls and abuse protection so that endpoints are protected by default.

**Acceptance Criteria:**
- [ ] Bearer token is required in production and CI for `/api/*`.
- [ ] Constant-time auth header comparison is used.
- [ ] Rate limiting is enforced with deterministic client ID resolution.
- [ ] Security-relevant events include trace ID in structured logs.
- [ ] Typecheck/lint passes.

### US-008: Implement PII-minimizing audit logging
**Description:** As a privacy owner, I want audit logs that support investigations without storing raw personal content.

**Acceptance Criteria:**
- [ ] Logs avoid raw user message storage by default.
- [ ] Audit events capture trace ID, event type, route, provider, and decision reason.
- [ ] Retention policy and redaction rules are documented.
- [ ] Typecheck/lint passes.

### US-009: Add legal release gate with mandatory sign-off
**Description:** As a release manager, I want legal checklist completion to block release so that compliance review is enforced before deployment.

**Acceptance Criteria:**
- [ ] Release workflow runs strict checklist validation (`--require-checked`).
- [ ] Missing reviewer/date/sign-off fails release gate.
- [ ] Jurisdiction evaluation and suite artifacts are required release artifacts.
- [ ] Typecheck/lint passes.

### US-010: Ship minimalist chat web UI (Next.js + Tailwind)
**Description:** As a user, I want a clean chat-first interface with minimal controls so that legal informational interactions are simple and focused.

**Acceptance Criteria:**
- [ ] UI provides chat input, response stream area, citation chips, and disclaimer banner.
- [ ] Error/refusal states are clearly rendered with trace ID reference.
- [ ] UI is responsive for desktop and mobile.
- [ ] Typecheck/lint passes.
- [ ] Verify in browser using dev-browser skill.

### US-011: Add observability dashboards and alerts
**Description:** As an operator, I want visibility into quality and reliability so that incidents are detected and triaged quickly.

**Acceptance Criteria:**
- [ ] Metrics include request rate, error rate, refusal rate, fallback rate, and latency percentiles.
- [ ] Alert thresholds are defined for sustained error/fallback spikes.
- [ ] Trace IDs are usable for request-level root-cause analysis.
- [ ] Typecheck/lint passes.

### US-012: Create backup/recovery runbook and drill process
**Description:** As ops, I want explicit backup and recovery procedures so that data/platform failures can be restored within target windows.

**Acceptance Criteria:**
- [ ] Backup schedule and retention policy are documented.
- [ ] RTO and RPO targets are defined.
- [ ] Restore verification checklist and failover order are documented.
- [ ] Quarterly drill cadence is documented with ownership.
- [ ] Typecheck/lint passes.

## 4. Functional Requirements

1. FR-1: The system must maintain a machine-validated Canada legal source registry covering required statutes, regulations, tribunal rules, policy, and case law endpoints.
2. FR-2: The system must reject release if required source IDs are missing.
3. FR-3: The system must enforce Canada-only legal scope in prompts, policy checks, and evaluation suites.
4. FR-4: The chat API must refuse representation/personalized legal-advice requests.
5. FR-5: Non-refusal legal responses must include at least one valid citation.
6. FR-6: Synthetic citations must be disabled in production.
7. FR-7: CanLII integration must return real results or explicit source-unavailable responses in production.
8. FR-8: Provider order must be OpenAI first, Gemini second, Grok optional by flag.
9. FR-9: `/api/*` routes must enforce bearer token in production and CI.
10. FR-10: Auth checks must use constant-time comparison.
11. FR-11: API rate limiting must be applied per trusted client identifier.
12. FR-12: All API responses must include trace ID in headers.
13. FR-13: Security/compliance events must be audit logged with redaction controls.
14. FR-14: Release workflow must require legal checklist strict validation before deploy.
15. FR-15: Jurisdiction evaluation and jurisdictional test suite must pass release thresholds.
16. FR-16: Web UI must render disclaimer and citations for each response.
17. FR-17: UI must render policy refusal and provider/source errors clearly.
18. FR-18: Observability must expose latency, errors, fallback, and refusal metrics.
19. FR-19: Backup/recovery policy must define schedule, retention, RTO, and RPO.
20. FR-20: Operations documentation must assign responsible roles for incident and recovery workflows.

## 5. Non-Goals (Out of Scope)

- Providing legal representation or personalized legal strategy.
- Automating government filing submission on behalf of users.
- Supporting non-Canadian jurisdictions in V1.
- Building a full legal case-management system.
- Replacing legal counsel or RCIC review for high-stakes outcomes.

## 6. Design Considerations

- Minimalist chat-first layout inspired by modern conversational tools (not pixel-cloned).
- Persistent, visible disclaimer near response surface.
- Citations shown as compact chips with click-through URLs and pin references.
- Minimal controls: input box, send action, compact settings drawer (if needed).

## 7. Technical Considerations

- Backend remains API-first service with strict schema contracts.
- Source governance should be data-driven via registry + validation scripts.
- Provider abstraction must preserve consistent error envelope and traceability.
- Production environment must disable scaffold fallbacks that can create synthetic legal content.
- CI/release gates should publish jurisdiction/legal artifacts for auditability.

## 8. Success Metrics (Combined Scorecard)

- Legal Reliability:
  - Authoritative-source coverage: 100% of required IDs present.
  - Citation coverage for grounded-info responses: >= 98%.
  - India-domain leakage rate: 0%.
- Safety/Compliance:
  - Policy-refusal accuracy on suite: 100%.
  - Production releases with completed legal checklist: 100%.
  - PII redaction compliance in sampled logs: >= 99%.
- Runtime Reliability:
  - API p95 latency: <= 2.5s for chat requests under normal load.
  - 5xx error rate: < 1%.
  - Fallback success rate (when primary fails): >= 95%.

## 9. Open Questions

- Should French (`fr-CA`) be mandatory in V1 or scheduled for V1.1?
- What is the required legal-review SLA for checklist sign-off before release cut?
- Should CanLII outage behavior be soft-fail (answer without case law) or hard refusal for case-law-specific queries?
- Do we require immutable external audit-log storage in V1 or V1.1?
- Which monitoring platform is canonical for metrics/traces/dashboards in production?
