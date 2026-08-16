# Phase 10 — Substrate Modes and Domain-Admissibility Geometry

Substrate Modes extend QSOL-SUBSTRATE with a public, vendor-neutral policy layer for specialist knowledge domains while preserving the canonical public substrate as the sole source of canonical truth.

## Implemented in Phase 10 bootstrap

- [x] Define Substrate Modes as bounded domain/epistemic contexts rather than personas, permissions, or authority levels.
- [x] Add 19 top-level domain modes covering formal knowledge, natural science, life science, medicine, engineering, computing, security, law, governance, economics, business, social science, history, philosophy, humanities, education, arts/media, environment, and everyday practical knowledge.
- [x] Add 10 cross-cutting activity modes: research, diagnostic, design, decision, educational, forensic, historical, predictive, normative, and creative.
- [x] Define the request composition contract: `DOMAIN_MODE + ACTIVITY_MODE + EPISTEMIC_PROFILE_24D + DECLARED_BRIDGES`.
- [x] Add explicit mode resolution states: `MODE_OK`, `MODE_AMBIGUOUS`, `MODE_CROSSOVER`, `MODE_VIOLATION`, and `MODE_UNRESOLVED`.
- [x] Add a source-admissibility model separating provenance class, publication state, epistemic status, authority class, and claim scope.
- [x] Enforce `CLAIM_STRENGTH <= EVIDENCE_ENTITLEMENT` as the central mode invariant.
- [x] Add claim maturity labels: established, consensus, supported, contested, preliminary, theoretical, proposed, speculative, unknown, hypothetical, counterfactual, fictional, and satirical.
- [x] Preserve preprint status and prevent silent promotion to peer reviewed or established.
- [x] Define repository/DOI semantics so archival identity and persistence cannot be mistaken for peer review, consensus, authority, or truth.
- [x] Permit repository-hosted/DOI material, including Zenodo-style archival records, in theoretical/proposed/speculative/unknown contexts while requiring separate stronger evidence for stronger claim states.
- [x] Add hard Legal mode policy: binding legal claims require resolved primary legal authority; commentary may explain but cannot become final binding authority.
- [x] Add Medical research/clinical separation: preprints and repository material may be used in labelled research contexts but are non-normative for clinical guidance by default.
- [x] Add field-sensitive terminology namespaces for ambiguous terms including evidence, proof, significance, causation, diagnosis, theory, model, test, risk, normal, liability, and validity.
- [x] Add an interpretable 24-dimensional mode-validation geometry.
- [x] Define geometry as structural validation machinery rather than a truth score, embedding oracle, or evidence source.
- [x] Add sparse hard geometry constraints for binding legal claims, clinical guidance, high-safety/low-evidence claims, and material cross-domain dependence.
- [x] Add explicit cross-domain bridges with non-equivalence rules for the highest-value domain crossings.
- [x] Require material cross-domain inference to declare a bridge rather than silently inheriting terminology or authority.
- [x] Add JSON Schema validation for the domain mode registry.
- [x] Add fail-closed `tools/validate_modes.py` validation.
- [x] Add regression tests for mode coverage, 24D geometry, bridge endpoints, high-stakes source guards, and the central evidence-entitlement invariant.
- [x] Run mode validation in the main GitHub Actions validation workflow.
- [x] Load the lightweight mode contract from `ai/bootstrap.json` while leaving detailed mode resources selective/on-demand.
- [x] Extend the canonical epistemic contract with claim maturity states and DOI/preprint/peer-review promotion guards.

## Deferred — requires additional evidence, domain maintenance, or empirical evaluation

- [ ] **DEFERRED:** Calibrate 24D thresholds empirically against frozen cross-model evaluation runs. The current thresholds are conservative structural guards, not empirically fitted performance claims.
- [ ] **DEFERRED:** Build a deterministic `MODE-CONFUSION/1` probe corpus measuring accidental cross-mode terminology transfer, bridge omission, authority escalation, and claim-strength inflation.
- [ ] **DEFERRED:** Measure mode-boundary performance across MICRO, STANDARD, FULL, vector-selected, latent-prefix, hybrid, and tool-enabled delivery conditions.
- [ ] **DEFERRED:** Propagate mode policy into every generated tool-less capsule and adapter only after deterministic size/compatibility rules are specified and regression-tested.
- [ ] **DEFERRED:** Define jurisdiction-specific Legal subprofiles and primary-authority resolvers for individual jurisdictions. Do not ship generic pseudo-jurisdictional rules as if they were binding law.
- [ ] **DEFERRED:** Define specialty-specific Medical clinical profiles and current guideline/regulator bindings. These require continuous freshness handling and must not be frozen as timeless clinical truth.
- [ ] **DEFERRED:** Define formal update/freshness policies for standards-heavy Engineering, Security, Computing, Governance, and Environment submodes.
- [ ] **DEFERRED:** Expand the bridge registry only where a concrete category-error contract is justified; do not auto-generate all pairwise mode combinations.
- [ ] **DEFERRED:** Add comprehensive field-level terminology ontologies for each submode after collision and maintenance policy is defined.
- [ ] **DEFERRED:** Add authoritative source resolvers for legislation, case law, regulators, clinical guidelines, standards bodies, official statistical agencies, and primary datasets.
- [ ] **DEFERRED:** Add conflict-resolution contracts for cases where multiple primary/official authorities disagree or where jurisdiction/version/date changes the answer.
- [ ] **DEFERRED:** Explore machine-checkable/formal proofs of selected mode-separation invariants. A future Lean 4 formalization may prove internal policy properties but must retain `FORMALIZATION != PHYSICAL_OR_LEGAL_OR_CLINICAL_TRUTH`.
- [ ] **DEFERRED:** Evaluate whether sparse 24D constraints outperform simpler rule-only policies before adding any learned or continuous classifier.
- [ ] **DEFERRED:** Add mode-policy fingerprints and compatibility identity to release manifests after the policy stabilizes enough to become a versioned derived artifact surface.

## Exit principle

A mode implementation is acceptable only if it increases specialist usefulness without allowing a weaker evidence regime in one field to leak into another.

```text
DOMAIN_BOUNDARY != SILO
BRIDGE != EVIDENCE
DOI != VALIDATION
MODE != AUTHORITY
GEOMETRY != TRUTH
CLAIM_STRENGTH <= EVIDENCE_ENTITLEMENT
```
